import os, sys, json

from typing import Optional
from logging import debug, info
from datetime import datetime, timezone

from btt_cache import write_cache
from config import TAG_ALL_ENTRIES
from utils import State, WID_PID_TYPE, wid_pid_tag_match

TIME_ENTRY = "https://api.track.toggl.com/api/v9/workspaces/{}/time_entries/{}"
CURRENT = "https://api.track.toggl.com/api/v9/me/time_entries/current"
START = "https://api.track.toggl.com/api/v9/workspaces/{}/time_entries"
STOP = "https://api.track.toggl.com/api/v9/workspaces/{}/time_entries/{}/stop"
PROJECTS = "https://api.track.toggl.com/api/v9/me/projects"

if "--curl" in sys.argv:
    from backends.curl import get, post, put, patch, NoInternetExceptions
    debug("Using curl backend (forced)")
elif "--requests" in sys.argv:
    from backends.requests import get, post, put, patch, NoInternetExceptions
    debug("Using requests backend (forced)")
elif "--urllib" in sys.argv:
    from backends.urllib import get, post, put, patch, NoInternetExceptions
    debug("Using urllib backend (forced)")
elif "--urllib3" in sys.argv:
    from backends.urllib3 import get, post, put, patch, NoInternetExceptions
    debug("Using urllib3 backend (forced)")
elif "--pycurl" in sys.argv:
    from backends.pycurl import get, post, put, patch, NoInternetExceptions
    debug("Using pycurl backend (forced)")
else:
    from backends.curl import get, post, put, patch, NoInternetExceptions
    debug("No backend specified, using curl through subprocess")


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

    state = put(TIME_ENTRY.format(state['workspace_id'], state['id']), json_dict)

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

    state = put(TIME_ENTRY.format(state['workspace_id'], state['id']), json_dict)

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
    info("Copy the above code into your config file, replacing the placeholder WID_PID_DICT definition (on line 18). Feel free to change the descriptions associated with each project.")
    return d
