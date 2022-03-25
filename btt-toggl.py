#!/usr/bin/env pypy3
import json, pathlib, argparse
from typing import NoReturn, Optional, Union

from misc import CurlReturnCodeException, vprint, get_data
from config import API_TOKEN, PATH_TO_IMG_DIR, PATH_TO_CACHE_FILE, WID_PID_DICT

# Usage:

## Checking status:
# pypy3 btt-toggl.py status general
# pypy3 btt-toggl.py status -w <wid> -p <pid>

## Toggle projects (supports stopping, starting, and switching between projects):
# pypy3 btt-toggl.py toggle -w <wid> -p <pid>

## Stop/Start logging:
# pypy3 btt-toggl.py stop
# pypy3 btt-toggl.py start -w <wid> -p <pid>

## Add tag to current entry:
# pypy3 btt-toggl.py add_tag -t <tag>

# TODO: add support for tags to status/toggle/stop

CURL         = "curl -s "
AUTH         = f"-u {API_TOKEN}:api_token "
HEADER       = '-H "Content-Type: application/json" '
DATA         = " -d '{}' "
TIME_ENTRIES = "https://api.track.toggl.com/api/v8/time_entries"
GET, POST, PUT       = "-X GET ", "-X POST ", "-X PUT "
CURRENT, START, STOP = "/current", "/start", "/stop"

OptStrInt = Optional[Union[str, int]]

def write_cache(current:Optional[dict]=None) -> Optional[dict]:
    ## gather all style strings and write them to a JSON file
    if current is None: current = get_current()
    d = dict()
    for wid, pids in WID_PID_DICT.items():
        d[wid] = {}
        for pid in pids.keys():
            d[wid][pid] = print_out(current, False, wid, pid, v=False)

    with open(PATH_TO_CACHE_FILE, 'w') as f:
        json.dump(d, f)
    return current

def read_cache(wid:str, pid:str) -> str:
    ## read respective style string from cache
    with open(PATH_TO_CACHE_FILE, 'r') as f:
        return json.load(f)[wid][pid]

def get_current() -> Optional[dict]:
    ## return data for the current entry or None if not currently logging
    return get_data(CURL + AUTH + GET + TIME_ENTRIES + CURRENT)

def start(wid:OptStrInt, pid:OptStrInt, tag:Optional[str]=None) -> Optional[dict]:
    ## start a new entry
    d = json.dumps({"time_entry":
                         {"tags": [tag, "btt-toggl"] if tag else ["btt-toggl"],
                           "wid": wid,
                           "pid": pid,
                  "created_with": "curl"}})
    return get_data(CURL + AUTH + HEADER + DATA.format(d) + POST + TIME_ENTRIES + START)

def stop(current:Optional[dict]=None) -> Optional[dict]:
    ## stop the current entry
    if current is None: current = get_current()
    if current is None: return None
    return get_data(CURL + AUTH + HEADER + DATA.format("") + PUT + TIME_ENTRIES + f"/{current['id']}" + STOP)

def toggle(wid:str, pid:str, tag:Optional[str]=None) -> Optional[dict]:
    ## stop the current entry if needed
    current = get_current()
    if current is not None:
        stopped = stop(current)
        if (int(wid) == stopped['wid']) and (int(pid) == stopped['pid']):
            return write_cache(stopped)
    ## start a new entry if needed
    out = start(wid, pid, tag)
    return write_cache(out)

def add_tag(new_tag:str, current:Optional[dict]=None) -> Optional[dict]:
    ## add a tag to the current entry
    if current is None: current = get_current()
    if current is None: return None # no entry to add a tag to
    d = json.dumps({"time_entry":
                         {"tags": current["tags"] + [new_tag],
                           "wid": str(current['wid']),
                           "pid": str(current['pid'])}})
    return get_data(CURL + AUTH + HEADER + DATA.format(d) + PUT + TIME_ENTRIES + f"/{current['id']}")

def is_wid_pid_match(data:Optional[dict], wid:OptStrInt, pid:OptStrInt) -> bool:
    ## True if wid and pid match, False otherwise
    return (data) and ('pid' in data) and ('wid' in data) and (str(data['pid']) == str(pid)) and (str(data['wid']) == str(wid))

def print_out(data:Optional[dict], general:bool=False, wid:OptStrInt=None, pid:OptStrInt=None, v:bool=True) -> Optional[str]:
    ## determine if we are active
    if general:                            active = bool(data)
    elif (not data) or ('stop' in data):   active = False
    elif is_wid_pid_match(data, wid, pid): active = True
    else:                                  active = False

    ## print/return the appropriate style string for BTT
    w, p = (int(wid), int(pid)) if not general else (None, None)
    if general and active: return vprint(json.dumps({"text":" ",                "icon_path":PATH_TO_IMG_DIR +   "active.png"}), v)
    elif general:          return vprint(json.dumps({"text":" ",                "icon_path":PATH_TO_IMG_DIR + "inactive.png"}), v)
    elif active:           return vprint(json.dumps({"text":WID_PID_DICT[w][p], "icon_path":PATH_TO_IMG_DIR +   "active.png"}), v)
    else:                  return vprint(json.dumps({"text":WID_PID_DICT[w][p], "icon_path":PATH_TO_IMG_DIR + "inactive.png"}), v)

def main(general:bool, mode:str, wid:Optional[str], pid:Optional[str], tag:Optional[str]) -> NoReturn:
    # status is used to change BTT widget icons/text, so we print to stdout
    if mode == 'status':
        if general:         print_out(write_cache(get_current()), general, wid, pid)
        else:               print(read_cache(wid, pid))
    # toggle/add_tag are used on widget click, so we don't print
    elif mode == 'toggle':  toggle(wid, pid, tag)
    elif mode == 'add_tag': add_tag(tag, get_current())
    # manual start and stop are also provided
    elif mode == 'start':   start(wid, pid, tag)
    elif mode == 'stop':    stop()

if __name__ == '__main__':
    ## parse args
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['status', 'toggle', 'start', 'stop', 'add_tag'])
    parser.add_argument('-w', '--wid', type=str, help='workspace ID')
    parser.add_argument('-p', '--pid', type=str, help='project ID')
    parser.add_argument('-t', '--tag', type=str, help='tag to add to current/new entry')
    args = parser.parse_args()
    general = args.wid is None or args.pid is None

    ## validate args
    if args.tag is not None:
        assert args.mode in ['add_tag', 'start', 'toggle'], f"Tag cannot be set in {args.mode} mode" # stop or status
    if args.mode == 'start':
        assert args.wid is not None and args.pid is not None, f"Workspace ID and Project ID must be set in {args.mode} mode" # start
    if general:
        assert args.mode in ['status', 'stop', 'add_tag'], f"Workspace ID and Project ID must be set in {args.mode} mode" # start, toggle

    pathlib.Path(PATH_TO_CACHE_FILE).parent.mkdir(parents=True, exist_ok=True) # make sure folder for cache file exists

    ## run script
    try:
        main(general, args.mode, args.wid, args.pid, args.tag)
    except CurlReturnCodeException as e: # if curl fails, silently assume we're inactive 
        import sys                       # this also doesn't update the cache
        print(f"cURL Return code {e.returncode}", file=sys.stderr)
        if args.mode == 'status':
            w, p = (int(args.wid), int(args.pid)) if not general else (None, None)
            if general: print(json.dumps({"text":" ",                "icon_path":PATH_TO_IMG_DIR + "inactive.png"}))
            else:       print(json.dumps({"text":WID_PID_DICT[w][p], "icon_path":PATH_TO_IMG_DIR + "inactive.png"}))