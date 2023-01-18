import os, sys, json

from pathlib import Path
from argparse import ArgumentParser
from functools import partial

from typing import Optional, Union
from traceback import format_exc
from logging import debug, info, basicConfig

from config import API_TOKEN, PATH_TO_ACTIVE_IMG, PATH_TO_INACTIVE_IMG, PATH_TO_CACHE_FILE, WID_PID_DICT, TAG_ALL_ENTRIES, VALIDATION, TIMEOUT

try:
    import requests
except ImportError as e:
    print(f"btt-toggl v1 requires `requests` to communicate with the Toggl API.\n Install with: \n\t {sys.executable} -m pip install requests", flush=True)
    os._exit(1)

USAGE = """
    btt-toggl.py status                             # prints general BTT style string (active if logging any project)
    btt-toggl.py stop                               # stops current entry

    btt-toggl.py status -w <wid> -p <pid>           # prints BTT style string for <wid> <pid> (active only if logging <wid> <pid>)
    btt-toggl.py toggle -w <wid> -p <pid> -t <tag>  # if <wid> <pid> is currently running, stop entry. otherwise, stop current and start new entry (tag optional)
    btt-toggl.py start -w <wid> -p <pid> -t <tag>   # starts new entry (tag optional)

    btt-toggl.py add_tag -t <tag>                   # adds tag to current entry
    btt-toggl.py remove_tag -t <tag>                # removes tag from current entry
    btt-toggl.py toggle_tag -t <tag>                # if tag is in current entry, remove it. otherwise, add it.

    btt-toggl.py get_project_dict                   # gets workspaces and projects from Toggl and prints them in a format that can be copied into config.py for WID_PID_DICT
    btt-toggl.py -h                                 # shows help message
"""

TIME_ENTRY = "https://api.track.toggl.com/api/v8/time_entries/{}"
CURRENT = "https://api.track.toggl.com/api/v8/time_entries/current"
START = "https://api.track.toggl.com/api/v8/time_entries/start"
STOP = "https://api.track.toggl.com/api/v8/time_entries/{}/stop"
PROJECTS = "https://api.track.toggl.com/api/v9/me/projects"

JSON_TYPES = Union[dict, list, str, bool, type(None)]
WID_PID_TYPE = dict[str, dict[str, str]]
JSON_DICT = dict[str, JSON_TYPES]
State = Optional[JSON_DICT]

send_to_btt = partial(print, flush=True, file=sys.stdout)

logging_kwargs = None
if "--debug" in sys.argv or str(os.environ.get("BTTT_DEBUG")).lower() in ['true', '1']:
    logging_kwargs = dict(level="DEBUG", format="%(message)s", datefmt="[%X]")
elif "get_project_dict" in sys.argv:
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

session = requests.Session()

debug("Imports/Setup done")


def get(url: str, get_data: bool=True) -> State:
    """ Send a GET request, including authentication, then return the result as json."""
    resp: JSON_DICT = session.get(url, auth=(API_TOKEN, "api_token"), timeout=TIMEOUT).json(parse_int=str)
    return resp.get("data") if get_data else resp


def post(url: str, json: JSON_DICT, get_data: bool=True) -> State:
    """ Send a POST request with json data, including authentication, then return the result as json."""
    resp: JSON_DICT = session.post(url, auth=(API_TOKEN, "api_token"), timeout=TIMEOUT, json=json).json(parse_int=str)
    return resp.get("data") if get_data else resp


def put(url: str, get_data: bool=True) -> State:
    """ Send a PUT request, including authentication, then return the result as json."""
    resp: JSON_DICT = session.put(url, auth=(API_TOKEN, "api_token"), timeout=TIMEOUT).json(parse_int=str)
    return resp.get("data") if get_data else resp


def write_cache(current: State=None):
    """Write the current state of each project to the cache file."""
    debug("Making cache")
    current = get_current(current)
    d: WID_PID_TYPE = dict()
    for wid, pids in WID_PID_DICT.items():
        d[wid] = {}
        for pid in pids.keys():
            d[wid][pid] = make_status(current, False, wid, pid, v=False)

    debug(f"Writing to cache")
    with open(PATH_TO_CACHE_FILE, "w") as f: json.dump(d, f)
    debug(f"Done writing to cache")

    return current


def read_cache(wid: str, pid: str):
    """Read the current style string of a project from the cache file."""
    debug(f"Reading from cache ({wid}, {pid})")
    with open(PATH_TO_CACHE_FILE, "r") as f:
        out_dict: WID_PID_TYPE = json.load(f)
        return out_dict[wid][pid]


def get_current(current: Optional[State]=None, force: bool=False) -> State:
    """If `current` is None, retrieve the current time entry from Toggl."""
    if current is None or force:
        debug("Getting current from Toggl")
        current = get(CURRENT)
    else:
        debug("Using cached current")

    return current


def start(wid: str, pid: str, tag: Optional[str]=None):
    """Start a new entry."""
    debug(f"Starting new entry ({wid}, {pid}, {tag})")
    tags: list[str] = []
    if tag:               tags.append(tag)
    elif TAG_ALL_ENTRIES: tags.append("btt-toggl")

    json_dict =  {"time_entry": {"tags": tags, "wid": wid, "pid": pid, "created_with": "curl"}}

    return post(START, json_dict)


def stop(current: Optional[dict] = None):
    """Stop the current entry, if it exists."""
    debug("Stopping current entry")
    current = get_current(current)
    if current is None: return None

    return put(STOP.format(current['id']))


def toggle(wid: str, pid: str, tag: Optional[str]=None):
    """Convenience function to toggle the current entry"""
    debug(f"Toggling ({wid}, {pid}, {tag})")
    current = get_current()
    if current is not None:
        stopped = stop(current)

        if wid_pid_match(stopped, wid, pid):
            return write_cache(stopped)

    # if there is no current trial, or if the current trial does not match wid/pid, start a new one.
    out = start(wid, pid, tag)
    return write_cache(out)


def add_tag(new_tag: str, current: Optional[dict]=None):
    """Add a tag to the current entry"""
    debug(f"Adding tag {new_tag} to current entry")
    current = get_current(current)
    if current is None: return None

    tags: list[str] = current.get("tags", list())
    tags.append(new_tag)

    json_dict = dict(time_entry=dict())
    json_dict["time_entry"]["tags"] = tags
    if "wid" in current: json_dict["time_entry"]["wid"] = current["wid"]
    if "pid" in current: json_dict["time_entry"]["pid"] = current["pid"]

    return put(TIME_ENTRY.format(current['id']), json_dict)


def remove_tag(old_tag: str, current: Optional[dict]=None):
    """Remove a tag from the current entry"""
    debug(f"Removing tag {old_tag} from current entry")
    current = get_current(current)
    if current is None: return None

    tags: list[str] = current.get("tags", list())
    if old_tag in tags:
        tags = [t for t in tags if t != old_tag]

    json_dict = dict(time_entry=dict())
    json_dict["time_entry"]["tags"] = tags
    if "wid" in current:
        json_dict["time_entry"]["wid"] = current["wid"]
    if "pid" in current:
        json_dict["time_entry"]["pid"] = current["pid"]

    return put(TIME_ENTRY.format(current['id']), json_dict)


def toggle_tag(tag: str, current: Optional[dict]=None):
    """Convenience function to toggle a tag"""
    debug(f"Toggling tag {tag} on current entry")

    current = get_current(current)
    if current is None: return None

    tags: list[str] = current.get("tags", [])
    if tag in tags:
        return remove_tag(tag, current)
    else:
        return add_tag(tag, current)


def wid_pid_match(data: Optional[dict]=None, wid: Optional[str]=None, pid: Optional[str]=None) -> bool:
    """Returns True if wid and pid match the current entry."""
    if data is None: return
    debug(f"Checking if wid/pid match (passed {wid}, {pid}) vs data {data.get('wid')}, {data.get('pid')}")

    pid_match = (not pid) or ("pid" in data and data["pid"] == pid)
    wid_match = (not wid) or ("wid" in data and data["wid"] == wid)

    match = wid_match and pid_match
    debug("Matched" if match else "No match")
    return match


def make_status(data: Optional[dict] = None, general: bool = False, wid: Optional[str] = None, pid: Optional[str] = None, v: bool = True):
    """Print status as in `data`, in the BTT format."""
    debug(f"Making status for ({data=}, {general=}, {wid=}, {pid=}, {v=})")
    if general or wid_pid_match(data, wid, pid):
        active = bool(data)
    else:
        active = False

    debug(f"Making {'active' if active else 'insactive'} style string {('for ' + str((wid, pid))) if not general else ''}")

    if general and active:
        status_string = json.dumps({"text": " ", "icon_path": PATH_TO_ACTIVE_IMG})
    elif general:
        status_string = json.dumps({"text": " ", "icon_path": PATH_TO_INACTIVE_IMG})
    elif active:
        status_string = json.dumps({"text": WID_PID_DICT[wid][pid], "icon_path": PATH_TO_ACTIVE_IMG})
    else:
        status_string = json.dumps({"text": WID_PID_DICT[wid][pid], "icon_path": PATH_TO_INACTIVE_IMG})

    return status_string


def main(general: bool, mode: str, wid: Optional[str]=None, pid: Optional[str]=None, tag: Optional[str]=None) -> None:
    # status is used to change BTT widget icons/text, so we print to stdout
    if mode == "status":
        if general:
            # rewrite cache on general status
            send_to_btt(make_status(write_cache(), general, wid, pid))
        else:
            # read from cache for non-general status
            send_to_btt(read_cache(wid, pid))

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
    projects = get(PROJECTS, False)
    d: WID_PID_TYPE = dict()
    for project in projects:
        if project["wid"] not in d:
            d[project["wid"]] = dict()
        d[project["wid"]][project["id"]] = project["name"]
    prefix = "WID_PID_DICT: dict[str, dict[str, str]] ="
    d_str = "\n".join([" "*len(prefix) + line if i else line for i, line in enumerate(json.dumps(d, indent=2).splitlines())])

    debug("Printing WID_PID_DICT definition code")
    print(f"{'~'*os.get_terminal_size().columns}\n\n{prefix} {d_str}\n\n{'~'*os.get_terminal_size().columns}", flush=True)
    info("Copy the above into your config file, replacing the placeholder WID_PID_DICT definition on line 16.")
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
                mode in ["add_tag", "start", "toggle", "remove_tag", "toggle_tag"],
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
    except requests.ConnectionError as e:
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
