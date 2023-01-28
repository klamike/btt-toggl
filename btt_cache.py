import json

from logging import debug

from utils import make_status, State, CACHE_TYPE
from config import WID_PID_DICT, PATH_TO_CACHE_FILE


def write_cache(state: State):
    """Write the current state of each project to the cache file."""
    debug("Making cache")
    d: CACHE_TYPE = dict()
    for wid, pids in WID_PID_DICT.items():
        d[wid] = {}
        for pid in pids.keys():
            d[wid][pid] = make_status(state, False, wid, pid)

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