#!/usr/bin/env pypy3
import sys, json, pathlib
from misc import is_logging, vprint, get_output
from config import TOKEN, PATH_TO_IMG_DIR, PATH_TO_CACHE_FILE, WID_PID_DICT

# Usage:

## Checking status:
# pypy3 btt-toggl.py status general
# pypy3 btt-toggl.py status <wid> <pid>

## Toggle projects (supports stopping, starting, and switching between projects):
# pypy3 btt-toggl.py toggle <wid> <pid>

## Stop/Start logging:
# pypy3 btt-toggl.py stop
# pypy3 btt-toggl.py start <wid> <pid>

PREFIX = f'curl -s -u {TOKEN}:api_token '

def write_cache(current=None):
    # if we have current already, we don't need to get it again
    if current is None: current = get_current()
    d = {}
    for wid, pid_name in WID_PID_DICT.items():
        d[wid] = {}
        for pid in pid_name.keys():
            d[wid][pid] = print_out(current, False, wid, pid, v=False)

    pathlib.Path(PATH_TO_CACHE_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(PATH_TO_CACHE_FILE, 'w') as f:
        json.dump(d, f)
    return current

def read_status(wid, pid):
    with open(PATH_TO_CACHE_FILE, 'r') as f:
        return json.load(f)[wid][pid]

def get_current():
    get_current_curl = PREFIX + '''\
    -X GET https://api.track.toggl.com/api/v8/time_entries/current\
    '''
    return json.loads(get_output(get_current_curl)).get('data')

def start(wid, pid):
    start_curl = PREFIX + '''\
    -H "Content-Type: application/json"\
    -d '{"time_entry":{"tags":["btt-toggl"],"wid":''' + str(wid) +''', "pid":''' + str(pid) + ''',"created_with":"curl"}}'\
    -X POST https://api.track.toggl.com/api/v8/time_entries/start\
    '''
    return json.loads(get_output(start_curl)).get('data')

def stop(current=None):
    # if we have current already, we don't need to get it again
    if current is None: current = get_current()
    stop_curl = PREFIX + '''\
    -H "Content-Type: application/json"\
    -d ""\
    -X PUT https://api.track.toggl.com/api/v8/time_entries/'''+ str(current['id']) + '''/stop\
    '''
    return json.loads(get_output(stop_curl)).get('data')

def toggle(wid, pid):
    current = get_current()
    # stop current project if needed
    if is_logging(current):
        stopped = stop(current)
        if (int(wid) == stopped['wid']) and (int(pid) == stopped['pid']):
            return write_cache(stopped)
    # start new project
    out = start(wid, pid)
    return write_cache(out)

def add_tag(client, current):
    if current is None: return None
    tag_curl = PREFIX + '''\
    -H "Content-Type: application/json"\
    -d '{"time_entry":{"tags":["''' + client + '''"],"wid":''' + str(current['wid']) + ''',"pid":''' + str(current['pid']) + '''}}'\
    -X PUT https://api.track.toggl.com/api/v8/time_entries/''' + str(current['id'])

    return json.loads(get_output(tag_curl)).get('data')

def is_wid_pid_match(data, wid, pid):
    if not data: return False
    elif (('pid' in data) and ('wid' in data) and (data['pid'] == pid) and (data['wid'] == wid)) \
         or \
         (('pid' in data) and (data['pid'] == pid) and ('wid' not in data)): return True
    else: return False

def print_out(data, general=False, wid=None, pid=None, v=True):
    if general: active = is_logging(data)
    elif (not data) or ('stop' in data): active = False
    elif is_wid_pid_match(data, wid, pid): active = True
    else: active = False

    if general and active: return vprint("""{\"text\":\" \",\"icon_path":\"""" + PATH_TO_IMG_DIR + """active.png\"}""", v)
    elif general:          return vprint("""{\"text\":\" \",\"icon_path":\"""" + PATH_TO_IMG_DIR + """inactive.png\"}""", v)
    elif active:           return vprint("""{\"text\":\"""" + WID_PID_DICT[int(wid)][int(pid)] + """\",\"icon_path":\"""" + PATH_TO_IMG_DIR + """active.png\"}""", v)
    else:                  return vprint("""{\"text\":\"""" + WID_PID_DICT[int(wid)][int(pid)] + """\",\"icon_path":\"""" + PATH_TO_IMG_DIR + """inactive.png\"}""", v)

def main(general, mode, wid, pid):
    if mode == 'status':
        if general:
            current = get_current()
            print_out(current, general, wid, pid)
            write_cache(current)
        else:
            print(read_status(wid, pid))
    elif mode == 'toggle': print_out(toggle(wid, pid), general, wid, pid)
    elif mode == 'start':  start(wid, pid)
    elif mode == 'stop':   stop()
    elif mode == 'addtag': # experimental
        name = args[-2]
        current = get_current()
        print(add_tag(name.lower(), current))

if __name__ == '__main__':
    try:
        args = sys.argv
        general = args[-1] in ['general', 'stop', 'start']
        mode = args[1]
        wid, pid = (args[2], args[3]) if not general else (None, None)
    except (KeyError, IndexError):
        print("""# Usage:\npypy3 btt-toggl.py status general\npypy3 btt-toggl.py status <wid> <pid>\npypy3 btt-toggl.py toggle <wid> <pid>""")
        sys.exit(1)
    try:
        main(general, mode, wid, pid)
    except:
        # on exception (usually no internet connection) set to inactive
        # uncomment below for debugging

        from traceback import format_exc
        print(format_exc())
        if general:
            print("""{\"text\":\" \",\"icon_path":\"""" + PATH_TO_IMG_DIR + """inactive.png\"}""")
        else:
            print("""{\"text\":\"""" + WID_PID_DICT[int(wid)][int(pid)] + """\",\"icon_path":\"""" + PATH_TO_IMG_DIR + """inactive.png\"}""")