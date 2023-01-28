import os, sys, json

from pathlib import Path
from logging import debug
from typing import Optional
from traceback import format_exc
from argparse import ArgumentParser

from utils import make_status, send_to_btt, USAGE
from btt_cache import read_cache, read_cache_tag, write_cache
from toggl_api import get_current, toggle, start, stop, toggle_tag, add_tag, remove_tag, get_project_dict, NoInternetExceptions

from config import PATH_TO_ACTIVE_IMG, PATH_TO_INACTIVE_IMG, WID_PID_DICT, VALIDATION

if "--no-validation" in sys.argv:
    debug("Validation disabled")
    VALIDATION = False

debug("Imports/Setup done")


def main(general: bool, mode: str, wid: Optional[str]=None, pid: Optional[str]=None, tag: Optional[str]=None) -> None:
    # status is used to change BTT widget icons/text, so we print to stdout
    if mode == "status":
        if general and tag is None:
            debug("Getting general status with no tag")
            # rewrite cache on general/tag-only status
            send_to_btt(make_status(write_cache(get_current()), general, wid, pid, tag))
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
    elif mode == "toggle":
        return toggle(wid, pid, tag)
    elif mode == "add_tag":
        return add_tag(tag)
    elif mode == "remove_tag":
        return remove_tag(tag)
    elif mode == "toggle_tag":
        return toggle_tag(tag)
    elif mode == "start":
        return start(wid, pid, tag)
    elif mode == "stop":
        return stop()


if __name__ == "__main__":
    parser = ArgumentParser(usage=USAGE, prog='btt-toggl', description=" Quick and easy time tracking in the touch bar with Toggl API v9 and BetterTouchTool")
    parser.add_argument("mode", choices=["status", "toggle", "start", "stop", "add_tag", "remove_tag", "toggle_tag", "get_project_dict"])
    parser.add_argument("-w", "--wid", type=str, help="workspace ID")
    parser.add_argument("-p", "--pid", type=str, help="project ID")
    parser.add_argument("-t", "--tag", type=str, help="tag to add to current/new entry")
    parser.add_argument("--debug", action="store_true", help="show debug messages")
    parser.add_argument("--info", action="store_true", help="show info messages")
    parser.add_argument("--curl", action="store_true", help="use curl backend")
    parser.add_argument("--requests", action="store_true", help="use requests backend")
    parser.add_argument("--urllib", action="store_true", help="use urllib backend")
    parser.add_argument("--urllib3", action="store_true", help="use urllib3 backend")
    parser.add_argument("--pycurl", action="store_true", help="use pycurl backend")
    parser.add_argument("--no-validation", action="store_true", help="disable validation of args")
    args = parser.parse_args()
    mode = args.mode
    pid = args.pid
    wid = args.wid
    tag = args.tag
    debug_logs = args.debug
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
    except (*NoInternetExceptions, ConnectionError) as e:
        if mode == "status" and general:
            debug("Failing silently due to lack of internet connection")
            send_to_btt(make_status(data=None, general=True, wid=None, pid=None))
        os._exit(1)
    except (PermissionError, FileNotFoundError) as e:
        msg = "Is your cache file writeable?"
        print(f"\n{msg}\n{format_exc()}\n{msg}\n", file=sys.stderr)
    except Exception as e:
        msg = "Something unexpected went wrong. Please report this error at https://github.com/klamike/btt-toggl/issues"
        print(f"\n{msg}\n{format_exc()}\n{msg}\n", file=sys.stderr)

    os._exit(1)
