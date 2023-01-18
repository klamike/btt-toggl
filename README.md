# btt-toggl
Control [Toggl](https://track.toggl.com) timers across different workspaces and projects via [BetterTouchTool](https://folivora.ai/) touchbar widgets. Uses Toggl API v8 via `requests`. Includes tag support and caching to cut down on network requests!

![multi](readme_img/multi.png)

## Installation

`btt-toggl` depends on Python ≥3.8 and the `requests` library. If you already have a Python installation, you can use that. To get some more speed you can also use [pypy3](https://www.pypy.org/features.html), which you can install with [Homebrew](https://brew.sh/) using `brew install pypy3`. Then:

1. Clone `btt-toggl` to your local machine by running `git clone https://github.com/klamike/btt-toggl`
2. Edit the `config.py` file:
    - Get your Toggl Token from the the bottom of the [Profile Settings page](https://track.toggl.com/profile)
    - Edit the paths/images to match your setup, if needed.
    - Edit the dictionary to include your mapping of workspace and project IDs. You can find these by clicking on a project from [https://track.toggl.com/projects](https://track.toggl.com/projects) and inspecting the URL. It will have the following form: `https://track.toggl.com/<workspace_id>/projects/<project_id>/team`.
3. Done! You can quickly run `pypy3 btt-toggl.py status` to make sure everything works. You should see a JSON string with a path to your active/inactive image.

## CLI options

    btt-toggl.py status                             # prints general BTT style string (active if logging any project)
    btt-toggl.py stop                               # stops current entry

    btt-toggl.py status -w <wid> -p <pid>           # prints BTT style string for <wid> <pid> (active only if logging <wid> <pid>)
    btt-toggl.py toggle -w <wid> -p <pid> -t <tag>  # if <wid> <pid> is currently running, stop entry. otherwise, stop current and start new entry (tag optional)
    btt-toggl.py start -w <wid> -p <pid> -t <tag>   # starts new entry (tag optional)

    btt-toggl.py add_tag -t <tag>                   # adds tag to current entry
    btt-toggl.py remove_tag -t <tag>                # removes tag from current entry
    btt-toggl.py toggle_tag -t <tag>                # if tag is in current entry, remove it. otherwise, add it.

    btt-toggl.py -h                                 # shows help message

## BetterTouchTool setup

`btt-toggl` provides several useful commands to integrate with BetterTouchTool. The `status` mode returns a style string for automatically changing button icons/text, so it should be run every few seconds. The `toggle` and `add_tag` modes should be run on button click, to execute their respective actions.

To cut down on network requests and CPU load, `btt-toggl` implements a JSON file cache which is updated **only** when `btt-toggl.py status` is run without additional arguments. Thus, **you must have a button running this script for the project-specific buttons to work.**

In my configuration, I have a general status icon with an Open Button Group action, which brings up project-specific buttons. The general status icon runs `btt-toggl.py status` every 5 seconds. The project-specific buttons run `btt-toggl.py status -w <workspace_id> -p <project_id>` every 3 seconds. Each project-specific button also toggles its respective project on click, via `btt-toggl.py toggle -w <workspace_id> -p <project_id>`. I also have three tag buttons which on click run `btt-toggl.py add_tag -t <tag>`.

### Status icons

Create a Shell Script/Task widget and set:

    Launch Path: /bin/bash
    Parameters: -c
    Script: /usr/local/bin/pypy3 /path/to/folder/btt-toggl.py status

![off](readme_img/off.png)

For project-specific status, use: `btt-toggl.py status -w <workspace_id> -p <project_id>`

### Toggle projects

Create a widget and assign it the Execute Shell Script/Task action. Then, set the options to:

    Launch Path: /bin/bash
    Parameters: -c
    Script: /usr/local/bin/pypy3 /path/to/folder/btt-toggl.py toggle -w <workspace_id> -p <project_id>

![multi](readme_img/multi.png)

### Add tags

Create a widget and assign it the Execute Shell Script/Task action. Then, set the options to:

    Launch Path: /bin/bash
    Parameters: -c
    Script: /usr/local/bin/pypy3 /path/to/folder/btt-toggl.py add_tag -t <tag>

## Failure modes

When you don't have an internet connection, `btt-toggl` will silently assume that you are not logging time. However, since we do not update the cache when there is no internet, project-specific buttons will remain active/inactive. Only the general status will change, which can be nice to spot if you suddenly lose connection.

For other exceptions, `btt-toggl` will exit with error. You can run the script manually in a terminal or via the Run Script Now button in the BTT UI to invesigate further. `btt-toggl` catches common exceptions and includes a message near the top/bottom of the traceback for the user. I encourage you to [create an issue](https://github.com/klamike/btt-toggl/issues) if you run into any uncaught exceptions.

## Documentation

[Toggl Track](https://track.toggl.com),
[Toggl API](https://github.com/toggl/toggl_api_docs/blob/master/toggl_api.md), [BTT Docs](https://docs.folivora.ai/), [BTT Forum](https://community.folivora.ai/), [PyPy](https://www.pypy.org/features.html)

## To-Do:

- Add tag support for `toggle` and `status`
- Remove a tag from the current entry
