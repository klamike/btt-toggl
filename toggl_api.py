import os, sys, json

from typing import Optional

from btt_cache import write_cache
from config import TAG_ALL_ENTRIES
from utils import State, WID_PID_TYPE, wid_pid_tag_match, debug, info

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
elif __name__ != "__main__":
    from backends.curl import get, post, put, patch, NoInternetExceptions
    debug("No backend specified, using curl through subprocess")
else:
    debug("Running toggl_api.py as script; not importing any backends")


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
    if tag:             tags.append(tag)
    if TAG_ALL_ENTRIES: tags.append("btt-toggl")

    import time
    from datetime import datetime
    now = time.time()
    start_rfc3339 = datetime.utcfromtimestamp(now).isoformat(timespec="seconds") + "Z"

    json_dict =  {"tags": tags, "start": start_rfc3339, "duration": -1 * int(now),
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


def backend_test(verbose: bool=False):
    info("Testing backends by sending one GET request to CURRENT.") # TODO: add post/patch/put

    profiler_kwargs = dict(interval=0.0001)
    output_kwargs = dict(unicode=True, color=True)
    round_to = 5

    try:
        import pyinstrument
    except ImportError:
        info("pyinstrument not installed, cannot test backends. Install with `pip install pyinstrument`")
        return

    def test_backend(backend):
        info("Testing %s", backend.__name__)
        for _ in range(1): # btt-toggl will rarely need to send more than one request at a time, so it doesn't make sense to test multiple requests
            for url in [CURRENT]: backend.get(url)

    results = dict()

    profiler = pyinstrument.Profiler(**profiler_kwargs)
    profiler.start()
    import backends.urllib
    test_backend(backends.urllib)
    profiler.stop()
    if verbose: print("urllib", profiler.output_text(**output_kwargs))
    results["urllib"] = round(profiler.last_session.duration, round_to)

    profiler = pyinstrument.Profiler(**profiler_kwargs)
    profiler.start()
    import backends.urllib3
    test_backend(backends.urllib3)
    profiler.stop()
    if verbose: print("urllib3", profiler.output_text(**output_kwargs))
    results["urllib3"] = round(profiler.last_session.duration, round_to)

    profiler = pyinstrument.Profiler(**profiler_kwargs)
    profiler.start()
    import backends.curl
    test_backend(backends.curl)
    profiler.stop()
    if verbose: print("curl", profiler.output_text(**output_kwargs))
    results["curl"] = round(profiler.last_session.duration, round_to)

    profiler = pyinstrument.Profiler(**profiler_kwargs)
    profiler.start()
    import backends.pycurl
    test_backend(backends.pycurl)
    profiler.stop()
    if verbose: print("pycurl", profiler.output_text(**output_kwargs))
    results["pycurl"] = round(profiler.last_session.duration, round_to)

    profiler = pyinstrument.Profiler(**profiler_kwargs)
    profiler.start()
    import backends.requests
    test_backend(backends.requests)
    profiler.stop()
    if verbose: print("requests", profiler.output_text(**output_kwargs))
    results["requests"] = round(profiler.last_session.duration, round_to)

    fastest_backend = min(results, key=results.get)

    print("Fastest backend: %s took %s seconds\n" % (fastest_backend, results[fastest_backend]))
    for backend, duration in sorted(results.items(), key=lambda x: x[1]):
        if backend != fastest_backend:
            print("%s took %s -- %s times slower than %s" % (backend, duration, round(duration/results[fastest_backend],5), fastest_backend))

    return results

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true", help="show pyinstrument output")
    parser.add_argument("--debug", action="store_true", help="show debug messages")
    parser.add_argument("--info", action="store_true", help="show info messages")
    args = parser.parse_args()
    verbose = args.verbose or args.debug or args.info

    backend_test(verbose)