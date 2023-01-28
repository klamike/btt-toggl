# btt-toggl
Control [Toggl](https://track.toggl.com) timers across different workspaces and projects via [BetterTouchTool](https://folivora.ai/) touchbar widgets. Uses Toggl API v9. Includes tag support, caching to cut down on network requests, and can use `cURL`, `PycURL`, `requests`, `urllib`, or `urllib3` to make API calls.

![multi](readme_img/multi.png)

## Installation

`btt-toggl` depends on Python ≥3.8 (and the `PycURL`/`requests`/`urllib3` libraries if you want to use those backends). To install:

1. Clone `btt-toggl` to your computer by running `git clone https://github.com/klamike/btt-toggl`
2. Edit the `config_example.py` file:
    - Rename the file from `config_example.py` to `config.py`
    - Get your API Token from the the bottom of the [Profile Settings page](https://track.toggl.com/profile)
    - Edit the dictionary to include your mapping of workspace and project IDs. You can find these by clicking on a project from [https://track.toggl.com/projects](https://track.toggl.com/projects) and inspecting the URL. It will have the following form: `https://track.toggl.com/<workspace_id>/projects/<project_id>/team`. Alternatively, run `python btt-toggl.py get_project_dict` to fetch this information from the Toggl API.
    - Edit the paths/images to match your setup, if needed.
3. Done! You can quickly run `python btt-toggl.py status` to make sure everything works. You should see a JSON string with a path to your active/inactive image.

## CLI options

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

## BetterTouchTool setup

`btt-toggl` provides several useful commands to integrate with BetterTouchTool. There are split in two groups: status and actions.

 The `status` mode prints a style string which BetterTouchTool uses to change button icons/text.

 The `toggle` and `toggle_tag` modes are designed as on-click actions. The individual `start`/`stop` and `add_tag`/`remove_tag` are also available.

To cut down on network requests and CPU load, `btt-toggl` implements a JSON file cache which is updated when an action command is run, and when the **general** status, i.e. `btt-toggl.py status` without specifying workspace/project/tag, is run. This is to prevent a bunch of project/tag-specific status buttons from all sending requests to Toggl at once. Thus, workspace/project/tag-specific status, e.g. `btt-toggl.py status -w <workspace_id> -p <project_id>` does not send a request to Toggl - it reads from the cache.

In my configuration, I have a general status icon with an Open Button Group action, which brings up project-specific buttons. The general status icon runs `btt-toggl.py status` every 5 seconds. The project-specific buttons run `btt-toggl.py status -w <workspace_id> -p <project_id>` every 5 seconds. Each project-specific button also toggles its respective project on click, via `btt-toggl.py toggle -w <workspace_id> -p <project_id>`.

### Status icons

The below examples use the placeholder `/full/path/to/python` for the full path to your Python ≥3.8 executable. Run `which python` to find this path for your computer. Likewise, `/full/path/to/btt-toggl/` is a placeholder for the full path to the local copy of the `btt-toggl` repo.

Create a Shell Script/Task widget and set:

    Launch Path: /bin/bash
    Parameters: -c
    Script: /full/path/to/python /full/path/to/btt-toggl/btt-toggl.py status

![off](readme_img/off.png)

For project-specific status, use: `btt-toggl.py status -w <workspace_id> -p <project_id>`

### Toggle projects

Create a widget and assign it the Execute Shell Script/Task action. Then, set the options to:

    Launch Path: /bin/bash
    Parameters: -c
    Script: /full/path/to/python /full/path/to/btt-toggl/btt-toggl.py toggle -w <workspace_id> -p <project_id>

![multi](readme_img/multi.png)

### Add tags

Create a widget and assign it the Execute Shell Script/Task action. Then, set the options to:

    Launch Path: /bin/bash
    Parameters: -c
    Script: /full/path/to/python /full/path/to/btt-toggl/btt-toggl.py add_tag -t <tag>

## Failure modes

When you don't have an internet connection, `btt-toggl` will silently assume that you are not logging time. However, since we do not update the cache when there is no internet, project-specific buttons will remain active/inactive. Only the general status will change, which can be nice to spot if you suddenly lose connection.

For other exceptions, `btt-toggl` will exit with error. You can run the script manually in a terminal or via the Run Script Now button in the BTT UI to invesigate further. `btt-toggl` catches common exceptions and includes a message near the top/bottom of the traceback for the user. I encourage you to [create an issue](https://github.com/klamike/btt-toggl/issues) if you run into any uncaught exceptions.

## Documentation

[Toggl Track](https://track.toggl.com),
[Toggl API v9](https://developers.track.toggl.com/docs/), [BTT Docs](https://docs.folivora.ai/), [BTT Forum](https://community.folivora.ai/), [PyPy](https://www.pypy.org/features.html)

## To-Do:

- Update backend comparison to include POST/PUT/PATCH requests
- Update docs with backend comparison
