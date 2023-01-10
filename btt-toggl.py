#!/usr/bin/env pypy3
import os, sys, json

from pathlib import Path
from argparse import ArgumentParser
from subprocess import check_output, CalledProcessError

from typing import Optional as O, Union
from traceback import format_exc

from config import API_TOKEN, PATH_TO_ACTIVE_IMG, PATH_TO_INACTIVE_IMG, PATH_TO_CACHE_FILE, WID_PID_DICT, TAG_ALL_ENTRIES, VALIDATION


USAGE = """
    btt-toggl.py status                             # prints general BTT style string (active if logging any project)
    btt-toggl.py stop                               # stops current entry

    btt-toggl.py status -w <wid> -p <pid>           # prints BTT style string for <wid> <pid> (active only if logging <wid> <pid>)
    btt-toggl.py toggle -w <wid> -p <pid> -t <tag>  # if <wid> <pid> is currently running, stop entry. otherwise, stop current and start new entry (tag optional)
    btt-toggl.py start -w <wid> -p <pid> -t <tag>   # starts new entry (tag optional)

    btt-toggl.py add_tag -t <tag>                   # adds tag to current entry
    btt-toggl.py remove_tag -t <tag>                # removes tag from current entry
    btt-toggl.py toggle_tag -t <tag>                # if tag is in current entry, remove it. otherwise, add it.

    btt-toggl.py -h                                 # shows help message
"""

CURL = "curl -s "
AUTH = f"-u {API_TOKEN}:api_token "
DATA = """ -H "Content-Type: application/json" -d '{}' """
GET, POST, PUT = "-X GET ", "-X POST ", "-X PUT "
TIME_ENTRIES = "https://api.track.toggl.com/api/v8/time_entries"
CURRENT, START, STOP = "/current", "/start", "/stop"

JSON_TYPES = Union[dict, list, str, bool, type(None)]
WID_PID_TYPE = dict[str, dict[str, str]]
STATE_DICT = dict[str, JSON_TYPES]


def get_data(curl_str: str) -> O[STATE_DICT]:
    """Executes curl_str and returns the data under the `data` key, if it exists."""
    raw_output = check_output(curl_str, shell=True).decode("utf-8")
    json_data: dict[str, JSON_TYPES] = json.loads(raw_output, parse_float=str, parse_int=str)

    if "data" in json_data:
        return json_data["data"]  # type:ignore


def write_cache(current: O[STATE_DICT]=None):
    ## gather all style strings and write them to a JSON file
    current = update_current(current)
    d: WID_PID_TYPE = dict()
    for wid, pids in WID_PID_DICT.items():
        d[wid] = {}
        for pid in pids.keys():
            d[wid][pid] = print_status(current, False, wid, pid, v=False)  # type:ignore

    with open(PATH_TO_CACHE_FILE, "w") as f:
        json.dump(d, f)

    return current


def read_cache(wid: str, pid: str):
    ## read respective style string from cache
    with open(PATH_TO_CACHE_FILE, "r") as f:
        out_dict: WID_PID_TYPE = json.load(f)
        return out_dict[wid][pid]


def get_current():
    ## return data for the current entry or None if not currently logging
    return get_data(CURL + AUTH + GET + TIME_ENTRIES + CURRENT)


def update_current(current: O[STATE_DICT]):
    if current is None:
        current = get_current()
    return current


def start(wid: str, pid: str, tag: O[str]=None):
    """Start a new entry."""

    # build tags list
    tags: list[str] = []
    if tag:
        tags.append(tag)
    elif TAG_ALL_ENTRIES:
        tags.append("btt-toggl")

    # make data dict and send request to start
    d = json.dumps(
        {"time_entry": {"tags": tags, "wid": wid, "pid": pid, "created_with": "curl"}}
    )
    return get_data(CURL + AUTH + DATA.format(d) + POST + TIME_ENTRIES + START)


def stop(current: O[dict] = None):
    """Stop the current entry, if it exists."""
    current = update_current(current)
    if current is None:
        return None  # no entry to stop

    # send request to stop
    return get_data(CURL + AUTH + DATA.format("") + PUT + TIME_ENTRIES + f"/{current['id']}" + STOP)


def toggle(wid: str, pid: str, tag: O[str]=None):
    """Convenience function to toggle the current entry"""

    # stop current entry if needed
    current = get_current()
    if current is not None:
        stopped = stop(current)

        # if wid and pid match, do not start a new trial
        # note that there is no check for tag matching
        if wid_pid_match(stopped, wid, pid):
            return write_cache(stopped)

    # if there is no current trial, or if the current trial does not match wid/pid, start a new one.
    out = start(wid, pid, tag)
    return write_cache(out)


def add_tag(new_tag: str, current: O[dict]=None):
    """Add a tag to the current entry"""
    current = update_current(current)
    if current is None:
        return None  # no entry to add tag to

    tags: list[str] = current.get("tags", list())  # type:ignore
    tags.append(new_tag)

    json_dict = dict(time_entry=dict())
    json_dict["time_entry"]["tags"] = tags
    if "wid" in current:
        json_dict["time_entry"]["wid"] = current["wid"]
    if "pid" in current:
        json_dict["time_entry"]["pid"] = current["pid"]
    d = json.dumps(json_dict)

    return get_data(CURL + AUTH + DATA.format(d) + PUT + TIME_ENTRIES + f"/{current['id']}")


def remove_tag(old_tag: str, current: O[dict]=None):
    """Remove a tag from the current entry"""
    current = update_current(current)
    if current is None:
        return None  # no entry to add tag to

    tags: list[str] = current.get("tags", list())  # type:ignore
    if old_tag in tags:
        tags = [t for t in tags if t != old_tag]

    json_dict = dict(time_entry=dict())
    json_dict["time_entry"]["tags"] = tags
    if "wid" in current:
        json_dict["time_entry"]["wid"] = current["wid"]
    if "pid" in current:
        json_dict["time_entry"]["pid"] = current["pid"]
    d = json.dumps(json_dict)

    return get_data(CURL + AUTH + DATA.format(d) + PUT + TIME_ENTRIES + f"/{current['id']}")


def toggle_tag(tag: str, current: O[dict]=None):
    """Convenience function to toggle a tag"""

    # get the current entry if needed
    current = update_current(current)
    if current is None: return None

    tags: list[str] = current.get("tags", [])
    if tag in tags:
        return remove_tag(tag, current)
    else:
        return add_tag(tag, current)


def wid_pid_match(data: O[dict]=None, wid: O[str]=None, pid: O[str]=None) -> bool:
    """Returns True if wid and pid match the current entry."""
    if data is None: return

    pid_match = (not pid) or ("pid" in data and data["pid"] == pid)
    wid_match = (not wid) or ("wid" in data and data["wid"] == wid)

    return wid_match and pid_match


def print_status(data: O[dict] = None, general: bool = False, wid: O[str] = None, pid: O[str] = None, v: bool = True):
    ## determine if we are active
    if general:
        active = bool(data)
    elif (not data) or ("stop" in data):
        active = False
    elif wid_pid_match(data, wid, pid):
        active = True
    else:
        active = False

    ## print/return the appropriate style string for BTT
    if general and active:
        status_string = json.dumps({"text": " ", "icon_path": PATH_TO_ACTIVE_IMG})
    elif general:
        status_string = json.dumps({"text": " ", "icon_path": PATH_TO_INACTIVE_IMG})
    elif active:
        status_string = json.dumps({"text": WID_PID_DICT[wid][pid], "icon_path": PATH_TO_ACTIVE_IMG})  # type:ignore
    else:
        status_string = json.dumps({"text": WID_PID_DICT[wid][pid], "icon_path": PATH_TO_INACTIVE_IMG})  # type:ignore

    if v:
        print(status_string)

    return status_string


def main(general: bool, mode: str, wid: O[str]=None, pid: O[str]=None, tag: O[str]=None) -> None:
    # status is used to change BTT widget icons/text, so we print to stdout
    if mode == "status":
        if general:
            print_status(write_cache(get_current()), general, wid, pid)
        else:
            print(read_cache(wid, pid))
    elif mode == "toggle":
        toggle(wid, pid, tag)
    elif mode == "add_tag":
        add_tag(tag)
    elif mode == "remove_tag":
        remove_tag(tag)
    elif mode == "toggle_tag":
        toggle_tag(tag)
    elif mode == "start":
        start(wid, pid, tag)
    elif mode == "stop":
        stop()


if __name__ == "__main__":
    ## parse args
    parser = ArgumentParser(usage=USAGE)
    parser.add_argument("mode", choices=["status", "toggle", "start", "stop", "add_tag", "remove_tag", "toggle_tag"])
    parser.add_argument("-w", "--wid", type=str, help="workspace ID")
    parser.add_argument("-p", "--pid", type=str, help="project ID")
    parser.add_argument("-t", "--tag", type=str, help="tag to add to current/new entry")
    args = parser.parse_args()
    general = (not args.wid) and (not args.pid)

    if VALIDATION:
        def assert_false(condition: bool, message: str):
            if not condition:
                print(message)
                os._exit(1)

        ## validate args
        if args.tag is not None:
            assert_false(
                args.mode in ["add_tag", "start", "toggle", "remove_tag", "toggle_tag"],
                f"Tag must not be set in {args.mode} mode\n",
            )
        if args.mode == "start":
            assert_false(
                (args.wid is not None) and (args.pid is not None),
                f"Workspace ID and Project ID must be set in {args.mode} mode\n",
            )
        elif args.mode in ["add_tag", "remove_tag", "toggle_tag"]:
            assert_false(
                (args.wid is None) and (args.pid is None),
                f"Workspace ID and Project ID are not used in {args.mode} mode\n",
            )
        if general:
            assert_false(
                args.mode in ["status", "stop", "add_tag", "remove_tag", "toggle_tag"],
                f"Workspace ID and Project ID must be set in {args.mode} mode\n",
            )
        else:
            assert_false(
                args.wid in WID_PID_DICT.keys(),
                f"Workspace ID {args.wid} not found. Make sure WID_PID_DICT is correct in config.py\n",
            )
            assert_false(
                args.pid in WID_PID_DICT[args.wid].keys(),
                f"Project ID {args.pid} not found under workspace {args.wid}. Make sure WID_PID_DICT is correct in config.py\n",
            )

        ## validate image paths
        assert_false(
            Path(PATH_TO_ACTIVE_IMG).is_file() and Path(PATH_TO_INACTIVE_IMG).is_file(),
            f"Your image files seem to be missing.\n",
        )

    ## run script
    try:
        main(general, args.mode, args.wid, args.pid, args.tag)
        os._exit(0)

    except CalledProcessError as e:
        print(f"cURL failed ({e.returncode})", file=sys.stderr)
        if (
            args.mode == "status"
        ):  # if curl fails, (mostly) silently assume we're inactive. this also doesn't update the cache
            if general:
                print(json.dumps({"text": " ", "icon_path": PATH_TO_INACTIVE_IMG}))
            else:
                print(json.dumps({"text": WID_PID_DICT[args.wid][args.pid], "icon_path": PATH_TO_INACTIVE_IMG}))
        os._exit(0)

    except json.JSONDecodeError as e:  # for other exceptions, we shouldn't be silent
        msg = "Did you change your API key? Make sure it's correct in config.py"
        exc = format_exc()
    except (PermissionError, FileNotFoundError) as e:
        msg = "Is your cache file writeable?"
        exc = format_exc()
    except Exception as e:
        msg = "Something unexpected went wrong. Please report this error at https://github.com/klamike/btt-toggl/issues"
        exc = format_exc()
    print(f"\n{msg}\n{exc}\n{msg}\n", file=sys.stderr)
    os._exit(1)
