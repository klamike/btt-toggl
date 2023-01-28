import sys, json

from functools import partial
from typing import Optional, Union

from config import WID_PID_DICT, PATH_TO_ACTIVE_IMG, PATH_TO_INACTIVE_IMG

WID_PID_TYPE = dict[str, dict[str, str]] # JSON {wid -> {pid -> display name, ...}}
CACHE_TYPE = dict[str, Union[dict[str, str], list[str]]] # JSON {wid -> {pid -> style string, ...}, ..., tags}
STR_KEY_JSON = dict[str, Union[dict, list, str, bool, type(None)]] # JSON with string keys
State = Optional[STR_KEY_JSON] # JSON if currently logging, None otherwise

USAGE = """
    btt-toggl.py status                             # prints general BTT style string (active if logging any project)
    btt-toggl.py status -w <wid> -p <pid>           # prints BTT style string for <wid> <pid> (active only if logging <wid> <pid>)
    btt-toggl.py status -t <tag>                    # prints BTT style string for <tag> (active only if current entry tags contains <tag>)

    btt-toggl.py toggle -w <wid> -p <pid> -t <tag>  # if <wid> <pid> is currently running, stop entry. otherwise, stop current and start new entry (tag optional)
    btt-toggl.py start -w <wid> -p <pid> -t <tag>   # starts new entry (tag optional)
    btt-toggl.py stop                               # stops current entry

    btt-toggl.py toggle_tag -t <tag>                # if tag is in current entry, remove it. otherwise, add it.
    btt-toggl.py add_tag -t <tag>                   # adds tag to current entry
    btt-toggl.py remove_tag -t <tag>                # removes tag from current entry

    btt-toggl.py get_project_dict                   # gets workspaces and projects from Toggl and prints them in a format that can be copied into config.py for WID_PID_DICT
    btt-toggl.py -h                                 # shows help message

    Options:
        --debug                                     # prints debug messages
        --info                                      # prints info messages
        --no-validation                             # skips validation of command line arguments, paths, etc.
        --curl                                      # uses curl backend
        --requests                                  # uses requests backend (default if available)
        --urllib                                    # uses urllib backend
        --urllib3                                   # uses urllib3 backend
        --pycurl                                    # uses pycurl backend
"""

send_to_btt = partial(print, flush=True, file=sys.stdout)

logging_kwargs = None
if "--debug" in sys.argv:
    logging_kwargs = dict(level="DEBUG", format="%(message)s", datefmt="[%X]")
elif "--info" in sys.argv or "get_project_dict" in sys.argv:
    logging_kwargs = dict(level="INFO", format="%(message)s", datefmt="[%X]")
if logging_kwargs:
    from logging import debug, info, basicConfig
    try:
        from rich.logging import RichHandler
        logging_kwargs["handlers"] = [RichHandler(omit_repeated_times=False)]
    except ImportError:
        pass
    finally:
        basicConfig(**logging_kwargs)
else:
    def debug(*args, **kwargs): pass
    def info(*args, **kwargs): pass

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

def make_status(data: Optional[dict]=None, general: bool=False, wid: Optional[str]=None, pid: Optional[str]=None, tag: Optional[str]=None):
    """Print status as in `data`, in the BTT format."""
    if general and tag is None:
        active = bool(data)
    elif wid_pid_tag_match(data, wid, pid, tag):
        active = True
    else:
        active = False

    debug("Making %s style string %s", "active" if active else "inactive", "" if general else ("for " + str((wid, pid))))

    icon_path = PATH_TO_ACTIVE_IMG if active else PATH_TO_INACTIVE_IMG
    if not general:
        text = WID_PID_DICT[wid][pid]
        if tag: text += f": {tag}"
    else:
        text = tag or " "

    status_string = json.dumps({"text": text, "icon_path": icon_path})
    debug("Status string: %s", status_string)

    return status_string
