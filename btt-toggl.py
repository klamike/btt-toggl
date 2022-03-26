#!/usr/bin/env pypy3
import sys, pathlib, argparse, subprocess, json
from typing import Optional as O, Union as U

from misc import vprint, get_data, assertf
from config import API_TOKEN, PATH_TO_IMG_DIR, PATH_TO_CACHE_FILE, WID_PID_DICT, TAG_ALL_ENTRIES, VALIDATION

## Usage:
# btt-toggl.py status                             # prints general BTT style string (active if logging any project)
# btt-toggl.py status -w <wid> -p <pid>           # prints BTT style string for <wid> <pid> (active only if logging <wid> <pid>)
# btt-toggl.py toggle -w <wid> -p <pid> -t <tag>  # if <wid> <pid> is currently running, stop entry. otherwise, stop current and start new entry (tag optional)
# btt-toggl.py add_tag -t <tag>                   # adds tag to current entry
# btt-toggl.py start -w <wid> -p <pid> -t <tag>   # starts new entry (tag optional)
# btt-toggl.py stop                               # stops current entry
# btt-toggl.py -h                                 # shows help message

CURL   = "curl -s "
AUTH   = f"-u {API_TOKEN}:api_token "
HEADER = '-H "Content-Type: application/json" '
DATA   = " -d '{}' "
GET, POST, PUT = "-X GET ", "-X POST ", "-X PUT "
TIME_ENTRIES   = "https://api.track.toggl.com/api/v8/time_entries"
CURRENT, START, STOP = "/current", "/start", "/stop"

def write_cache(current:O[dict]=None) -> O[dict]:
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

def get_current() -> O[dict]:
    ## return data for the current entry or None if not currently logging
    return get_data(CURL + AUTH + GET + TIME_ENTRIES + CURRENT)

def start(wid:O[U[str,int]], pid:O[U[str,int]], tag:O[str]=None) -> O[dict]:
    ## start a new entry
    d = json.dumps({"time_entry":
                         {"tags": ([tag, "btt-toggl"] if tag else ["btt-toggl"]) \
                                         if TAG_ALL_ENTRIES else \
                                  ([tag] if tag else []),
                           "wid": wid,
                           "pid": pid,
                  "created_with": "curl"}})
    return get_data(CURL + AUTH + HEADER + DATA.format(d) + POST + TIME_ENTRIES + START)

def stop(current:O[dict]=None) -> O[dict]:
    ## stop the current entry
    if current is None: current = get_current()
    if current is None: return None
    return get_data(CURL + AUTH + HEADER + DATA.format("") + PUT + TIME_ENTRIES + f"/{current['id']}" + STOP)

def toggle(wid:str, pid:str, tag:O[str]=None) -> O[dict]:
    ## stop the current entry if needed
    current = get_current()
    if current is not None:
        stopped = stop(current)
        if (int(wid) == stopped['wid']) and (int(pid) == stopped['pid']):
            return write_cache(stopped)
    ## start a new entry if needed
    out = start(wid, pid, tag)
    return write_cache(out)

def add_tag(new_tag:str, current:O[dict]=None) -> O[dict]:
    ## add a tag to the current entry
    if current is None: current = get_current()
    if current is None: return None # no entry to add a tag to
    d = json.dumps({"time_entry":
                         {"tags": current["tags"] + [new_tag],
                           "wid": str(current['wid']),
                           "pid": str(current['pid'])}})
    return get_data(CURL + AUTH + HEADER + DATA.format(d) + PUT + TIME_ENTRIES + f"/{current['id']}")

def is_wid_pid_match(data:O[dict], wid:O[U[str,int]], pid:O[U[str,int]]) -> bool:
    ## True if wid and pid match, False otherwise
    return (data) and ('pid' in data) and ('wid' in data) and (str(data['pid']) == str(pid)) and (str(data['wid']) == str(wid))

def print_out(data:O[dict], general:bool=False, wid:O[U[str,int]]=None, pid:O[U[str,int]]=None, v:bool=True) -> O[str]:
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

def main(general:bool, mode:str, wid:O[str], pid:O[str], tag:O[str]) -> None:
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

    if VALIDATION:
        ## validate args
        if args.tag is not None:
            assertf(args.mode in ['add_tag', 'start', 'toggle'], # stop or status
                        f"Tag cannot be set in {args.mode} mode\n")
        if args.mode == 'start':
            assertf(args.wid is not None and args.pid is not None,
                        f"Workspace ID and Project ID must be set in {args.mode} mode\n")
        if general:
            assertf(args.mode in ['status', 'stop', 'add_tag'],
                        f"Workspace ID and Project ID must be set in {args.mode} mode\n")
        else:
            assertf(int(args.wid) in WID_PID_DICT.keys(),
                        f"Workspace ID {args.wid} not found. Make sure WID_PID_DICT is correct in config.py\n")
            assertf(int(args.pid) in WID_PID_DICT[int(args.wid)].keys(),
                        f"Project ID {args.pid} not found. Make sure WID_PID_DICT is correct in config.py\n")

        ## validate cache path
        try: pathlib.Path(PATH_TO_CACHE_FILE).touch() # make sure we can write to cache file
        except (PermissionError, FileNotFoundError) as e: print(f"Is your cache file writeable?\n", file=sys.stderr); exit(1)

        ## validate image paths
        assertf(pathlib.Path(PATH_TO_IMG_DIR + '/active.png').is_file() \
            and pathlib.Path(PATH_TO_IMG_DIR + '/inactive.png').is_file(),
                        f"Your image files seem to be missing.\n")

    ## run script
    try:
        main(general, args.mode, args.wid, args.pid, args.tag)
        exit(0)
    except subprocess.CalledProcessError as e:
        print(f"cURL failed ({e.returncode})", file=sys.stderr)
        if args.mode == 'status':  # if curl fails, (mostly) silently assume we're inactive. this also doesn't update the cache
            w, p = (int(args.wid), int(args.pid)) if not general else (None, None)
            if general: print(json.dumps({"text":" ",                "icon_path":PATH_TO_IMG_DIR + "inactive.png"}))
            else:       print(json.dumps({"text":WID_PID_DICT[w][p], "icon_path":PATH_TO_IMG_DIR + "inactive.png"}))

    except json.JSONDecodeError as e: # for other exceptions, we shouldn't be silent
        print(f"\nDid you change your API key? Make sure it's correct in config.py\n", file=sys.stderr)
        from traceback import print_exc; print_exc()
        print(f"\nDid you change your API key? Make sure it's correct in config.py\n", file=sys.stderr)
    except (PermissionError, FileNotFoundError) as e:
        print(f"Is your cache file in writeable?\n", file=sys.stderr)
    except Exception as e:
        from traceback import format_exc
        print(f"Encountered uncaught exception:\n\n {format_exc()}\n Please report to https://github.com/klamike/btt-toggl/issues\n", file=sys.stderr)
    finally: # we exit(0) after main if successful, so this block only runs after an exception
        exit(1)