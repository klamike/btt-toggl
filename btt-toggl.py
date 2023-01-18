import os, sys, json

import requests, subprocess

from datetime import datetime, timezone
from pathlib import Path
from argparse import ArgumentParser
from functools import partial

from typing import Optional
from traceback import format_exc
from logging import debug, info, basicConfig

from config import PATH_TO_ACTIVE_IMG, PATH_TO_INACTIVE_IMG, PATH_TO_CACHE_FILE, WID_PID_DICT, TAG_ALL_ENTRIES, VALIDATION
from custom_types import CACHE_TYPE, WID_PID_TYPE, State

USAGE = """
    btt-toggl.py status                             # prints general BTT style string (active if logging any project)
    btt-toggl.py stop                               # stops current entry

    btt-toggl.py status -w <wid> -p <pid>           # prints BTT style string for <wid> <pid> (active only if logging <wid> <pid>)
    btt-toggl.py status -t <tag>                    # prints BTT style string for <tag> (active only if current entry tags contains <tag>)
    btt-toggl.py toggle -w <wid> -p <pid> -t <tag>  # if <wid> <pid> is currently running, stop entry. otherwise, stop current and start new entry (tag optional)
    btt-toggl.py start -w <wid> -p <pid> -t <tag>   # starts new entry (tag optional)

    btt-toggl.py add_tag -t <tag>                   # adds tag to current entry
    btt-toggl.py remove_tag -t <tag>                # removes tag from current entry
    btt-toggl.py toggle_tag -t <tag>                # if tag is in current entry, remove it. otherwise, add it.

    btt-toggl.py get_project_dict                   # gets workspaces and projects from Toggl and prints them in a format that can be copied into config.py for WID_PID_DICT
    btt-toggl.py -h                                 # shows help message

    Options:
        --debug                                     # prints debug messages
        --info                                      # prints info messages
        --no-validation                             # skips validation of command line arguments, paths, etc.
        --curl                                      # uses curl backend
        --requests                                  # uses requests backend (default if available)
"""

TIME_ENTRY = "https://api.track.toggl.com/api/v9/workspaces/{}/time_entries/{}"
CURRENT = "https://api.track.toggl.com/api/v9/me/time_entries/current"
START = "https://api.track.toggl.com/api/v9/workspaces/{}/time_entries"
STOP = "https://api.track.toggl.com/api/v9/workspaces/{}/time_entries/{}/stop"
PROJECTS = "https://api.track.toggl.com/api/v9/me/projects"

send_to_btt = partial(print, flush=True, file=sys.stdout)

logging_kwargs = None
if "--debug" in sys.argv or str(os.environ.get("BTTT_DEBUG")).lower() in ['true', '1']:
    logging_kwargs = dict(level="DEBUG", format="%(message)s", datefmt="[%X]")
elif "--info" in sys.argv or "get_project_dict" in sys.argv:
    logging_kwargs = dict(level="INFO", format="%(message)s", datefmt="[%X]")
if logging_kwargs:
    try:
        from rich.logging import RichHandler
        logging_kwargs["handlers"] = [RichHandler(omit_repeated_times=False)]
    except ImportError:
        pass
    finally:
        basicConfig(**logging_kwargs)
        debug("Debug logs enabled")
        info("Info logs enabled")

if "--curl" in sys.argv:
    from backends.curl import get, post, put, patch
    debug("Using curl backend (forced)")
elif "--requests" in sys.argv:
    from backends.requests import get, post, put, patch
    debug("Using requests backend (forced)")
else:
    try:
        from backends.requests import get, post, put, patch
        debug("Found requests installation; using requests backend")
    except ImportError:
        from backends.curl import get, post, put, patch
        debug("No requests installation found; using curl backend")

if "--no-validation" in sys.argv:
    debug("Validation disabled")
    VALIDATION = False

debug("Imports/Setup done")


def write_cache(state: State=None):
    """Write the current state of each project to the cache file."""
    debug("Making cache")
    state = get_current(state)
    d: CACHE_TYPE = dict()
    for wid, pids in WID_PID_DICT.items():
        d[wid] = {}
        for pid in pids.keys():
            d[wid][pid] = make_status(state, False, wid, pid, v=False)

    if state is not None:
        debug("Adding active tags to cache")
        d["tags"] = state.get("tags", list())
        debug("Tags: %s", str(d['tags']))

    debug("Writing to cache")
    with open(PATH_TO_CACHE_FILE, "w") as f: json.dump(d, f)
    debug("Done writing to cache")

    return state


def read_cache(wid: str, pid: str):
    """Read the current style string of a project from the cache file."""
    debug("Reading from cache (%s, %s)", wid, pid)
    with open(PATH_TO_CACHE_FILE, "r") as f:
        out_dict: CACHE_TYPE = json.load(f)
        return out_dict[wid][pid]


def read_cache_tag(tag: str):
    """Checking if a tag is in the cache file."""
    debug("Looking for %s in cache", tag)

    with open(PATH_TO_CACHE_FILE, "r") as f:
        out_dict: CACHE_TYPE = json.load(f)
        match = tag in out_dict["tags"]
        debug("Found %s in cache" if match else "No %s in cache", tag)
        return match


def get_current(state: Optional[State]=None, force: bool=False) -> State:
    """If `state` is None, retrieve the current time entry from Toggl."""
    if state is None or force:
        debug("Getting current from Toggl")
        state = get(CURRENT)
        debug("Current: %s", str(state))
    else:
        debug("Using cached current")

    return state


def start(wid: str, pid: str, tag: Optional[str]=None, cache: bool=False):
    """Start a new entry."""
    debug("Starting new entry (%s, %s, %s)", wid, pid, tag)
    tags: list[str] = []
    if tag:               tags.append(tag)
    if TAG_ALL_ENTRIES: tags.append("btt-toggl")

    now = datetime.now(tz=timezone.utc)
    json_dict =  {"tags": tags, "start": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "duration": -1 * int(now.timestamp()),
                  "workspace_id": int(wid), "project_id": int(pid), "created_with": "btt-toggl"}

    state = post(START.format(wid), json_dict)

    return write_cache(state) if cache else state


def stop(state: Optional[dict] = None, cache: bool=False):
    """Stop the current entry, if it exists."""
    debug("Stopping current entry")
    state = get_current(state)
    if state is None: return None

    state = patch(STOP.format(state['workspace_id'], state['id']))

    return write_cache(state) if cache else state


def toggle(wid: str, pid: str, tag: Optional[str]=None, cache: bool=True):
    """Convenience function to toggle the current entry"""
    debug("Toggling (%s, %s, %s)", wid, pid, tag)
    state = get_current()
    if state is not None:
        stopped = stop(state, cache=False)

        if wid_pid_tag_match(stopped, wid, pid, tag):
            return write_cache(stopped)

    # if there is no current trial, or if the current trial does not match wid/pid, start a new one.
    out = start(wid, pid, tag, cache=False)

    return write_cache(out) if cache else out


def add_tag(new_tag: str, state: Optional[dict]=None, cache: bool=True):
    """Add a tag to the current entry"""
    debug("Adding tag %s to current entry", new_tag)
    state = get_current(state)
    if state is None: return None

    tags: list[str] = state.get("tags", list())
    tags.append(new_tag)

    json_dict = dict(tags=tags)

    state = put(TIME_ENTRY.format(state['wid'], state['id']), json_dict)

    return write_cache(state) if cache else state


def remove_tag(old_tag: str, state: Optional[dict]=None, cache: bool=True):
    """Remove a tag from the current entry"""
    debug("Removing tag %s from current entry", old_tag)
    state = get_current(state)
    if state is None: return None

    tags: list[str] = state.get("tags", list())
    if old_tag in tags:
        tags = [t for t in tags if t != old_tag]

    json_dict = dict(tags=tags)

    state = put(TIME_ENTRY.format(state['wid'], state['id']), json_dict)

    return write_cache(state) if cache else state


def toggle_tag(tag: str, state: Optional[dict]=None, cache: bool=True):
    """Convenience function to toggle a tag"""
    debug("Toggling tag %s on current entry", tag)

    state = get_current(state)
    if state is None: return None

    tags: list[str] = state.get("tags", list())
    if tag in tags:
        state = remove_tag(tag, state, cache=False)
    else:
        state = add_tag(tag, state, cache=False)

    return write_cache(state) if cache else state


def wid_pid_tag_match(data: Optional[dict]=None, wid: Optional[str]=None, pid: Optional[str]=None, tag: Optional[str]=None) -> bool:
    """Returns True if wid and pid and tag (if supplied) match the current entry."""
    if data is None: return
    debug("Checking if wid/pid/tag match (%s, %s, %s) vs data %s, %s, %s", wid, pid, tag, data.get("workspace_id"), data.get("project_id"), str(data.get("tags", list())))

    pid_match = (not pid) or ("project_id" in data and data["project_id"] == pid)
    wid_match = (not wid) or ("workspace_id" in data and data["workspace_id"] == wid)
    tag_match = (not tag) or ("tags" in data and tag in data["tags"])

    match = wid_match and pid_match and tag_match
    debug("Matched" if match else f"No match ({wid_match=}, {pid_match=}, {tag_match=})")

    return match


def make_status(data: Optional[dict]=None, general: bool=False, wid: Optional[str]=None, pid: Optional[str]=None, tag: Optional[str]=None, v: bool = True):
    """Print status as in `data`, in the BTT format."""
    if general and tag is None:
        active = bool(data)
    elif wid_pid_tag_match(data, wid, pid, tag):
        active = True
    else:
        active = False

    debug("Making %s style string %s", "active" if active else "inactive", ("for " + str((wid, pid))) if not general else "")

    icon_path = PATH_TO_ACTIVE_IMG if active else PATH_TO_INACTIVE_IMG
    if not general:
        text = WID_PID_DICT[wid][pid]
        if tag: text += f": {tag}"
    else:
        text = tag or " "

    status_string = json.dumps({"text": text, "icon_path": icon_path})
    debug("Status string: %s", status_string)

    return status_string


def main(general: bool, mode: str, wid: Optional[str]=None, pid: Optional[str]=None, tag: Optional[str]=None) -> None:
    # status is used to change BTT widget icons/text, so we print to stdout
    if mode == "status":
        if general and tag is None:
            debug("Getting general status with no tag")
            # rewrite cache on general/tag-only status
            send_to_btt(make_status(write_cache(), general, wid, pid, tag))
        else:
            debug("Getting non-general status")
            # read from cache for non-general status
            if tag is None:
                debug("Getting non-general status with no tag")
                send_to_btt(read_cache(wid, pid))
            elif general:
                debug("Getting non-general status with tag")
                icon_path = PATH_TO_ACTIVE_IMG if read_cache_tag(tag) else PATH_TO_INACTIVE_IMG
                send_to_btt(json.dumps({"text": tag, "icon_path": icon_path}))
            else:
                debug("Getting non-general status with tag and wid/pid")
                cached = json.loads(read_cache(wid, pid))
                cached['text'] += f": {tag}"
                cached['icon_path'] = PATH_TO_ACTIVE_IMG if read_cache_tag(tag) else PATH_TO_INACTIVE_IMG
                send_to_btt(json.dumps(cached))

    # commands
    elif mode == "toggle": toggle(wid, pid, tag)
    elif mode == "add_tag": add_tag(tag)
    elif mode == "remove_tag": remove_tag(tag)
    elif mode == "toggle_tag": toggle_tag(tag)
    elif mode == "start": start(wid, pid, tag)
    elif mode == "stop": stop()

def get_project_dict() -> WID_PID_TYPE:
    """ Query Toggl for all workspaces and projects """
    debug("Getting WID_PID_DICT from Toggl")
    projects = get(PROJECTS)
    d: WID_PID_TYPE = dict()
    for project in projects:
        if project["wid"] not in d:
            d[project["wid"]] = dict()
        d[project["wid"]][project["id"]] = project["name"]
    prefix = "WID_PID_DICT: dict[str, dict[str, str]] ="
    d_str = "\n".join([" "*len(prefix) + line if i else line for i, line in enumerate(json.dumps(d, indent=2).splitlines())])

    debug("Printing WID_PID_DICT definition code")
    print(f"{'~'*os.get_terminal_size().columns}\n\n{prefix} {d_str}\n\n{'~'*os.get_terminal_size().columns}", flush=True)
    info("Copy the above code into your config file, replacing the placeholder WID_PID_DICT definition on line 16. Feel free to change the descriptions associated with each project.")
    return d


if __name__ == "__main__":
    ## parse args/env vars

    # first check for env vars (for BTT)
    mode = os.environ.get("BTTT_MODE")
    if mode is None:
        debug("Using CLI args")
        parser = ArgumentParser(usage=USAGE)
        parser.add_argument("mode", choices=["status", "toggle", "start", "stop", "add_tag", "remove_tag", "toggle_tag", "get_project_dict"])
        parser.add_argument("-w", "--wid", type=str, help="workspace ID")
        parser.add_argument("-p", "--pid", type=str, help="project ID")
        parser.add_argument("-t", "--tag", type=str, help="tag to add to current/new entry")
        parser.add_argument("--debug", action="store_true", help="show debug messages")
        parser.add_argument("--info", action="store_true", help="show info messages")
        parser.add_argument("--curl", action="store_true", help="use curl backend")
        parser.add_argument("--requests", action="store_true", help="use requests backend")
        parser.add_argument("--no-validation", action="store_true", help="disable validation of args")
        args = parser.parse_args()
        mode = args.mode
        pid = args.pid
        wid = args.wid
        tag = args.tag
        debug_logs = args.debug
        general = (not wid) and (not pid)
    else:
        # BTTT_MODE is set, so we're in BTT
        debug("Using environment variables")
        wid = os.environ.get("BTTT_WID")
        pid = os.environ.get("BTTT_PID")
        tag = os.environ.get("BTTT_TAG")
        general = (not wid) and (not pid)

    if VALIDATION:
        def assert_false(condition: bool, message: str):
            if not condition:
                print(message, flush=True, file=sys.stderr)
                os._exit(1)

        ## validate args
        if tag is not None:
            assert_false(
                mode in ["status", "add_tag", "start", "toggle", "remove_tag", "toggle_tag"],
                f"Tag must not be set in {mode} mode\n",
            )
        if mode == "start":
            assert_false(
                (wid is not None) and (pid is not None),
                f"Workspace ID and Project ID must be set in {mode} mode\n",
            )
        elif mode in ["add_tag", "remove_tag", "toggle_tag", "get_project_dict"]:
            assert_false(
                (wid is None) and (pid is None),
                f"Workspace ID and Project ID are not used in {mode} mode\n",
            )
        if general:
            assert_false(
                mode in ["status", "stop", "add_tag", "remove_tag", "toggle_tag", "get_project_dict"],
                f"Workspace ID and Project ID must be set in {mode} mode\n",
            )
        elif not mode == "get_project_dict":
            assert_false(
                wid in WID_PID_DICT.keys(),
                f"Workspace ID {wid} not found. Make sure WID_PID_DICT is correct in config.py\n",
            )
            assert_false(
                pid in WID_PID_DICT[wid].keys(),
                f"Project ID {pid} not found under workspace {wid}. Make sure WID_PID_DICT is correct in config.py\n",
            )

        ## validate image paths
        assert_false(
            Path(PATH_TO_ACTIVE_IMG).is_file() and Path(PATH_TO_INACTIVE_IMG).is_file(),
            f"Your image files seem to be missing.\n",
        )

    ## run script
    try:
        if mode == "get_project_dict":
            get_project_dict()
        else:
            main(general, mode, wid, pid, tag)
        os._exit(0)
    except json.JSONDecodeError as e:  # for other exceptions, we shouldn't be silent
        msg = "Did you change your API key? Make sure it's correct in config.py"
        print(f"\n{msg}\n{format_exc()}\n{msg}\n", file=sys.stderr)
    # if no internet, fail (semi-)silently
    except (requests.ConnectionError, subprocess.CalledProcessError) as e:
        if mode == "status" and general:
            debug("Failing silently due to lack of internet connection")
            send_to_btt(make_status(data=None, general=True, wid=None, pid=None, v=True))
        os._exit(1)
    except (PermissionError, FileNotFoundError) as e:
        msg = "Is your cache file writeable?"
        print(f"\n{msg}\n{format_exc()}\n{msg}\n", file=sys.stderr)
    except Exception as e:
        msg = "Something unexpected went wrong. Please report this error at https://github.com/klamike/btt-toggl/issues"
        print(f"\n{msg}\n{format_exc()}\n{msg}\n", file=sys.stderr)

    os._exit(1)
