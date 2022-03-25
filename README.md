# btt-toggl
Control Toggl timers across different workspaces and projects via BetterTouchTool touchbar widgets. Uses Toggl API v8 via cURL. Also includes caching to cut down on network requests. I suggest using [pypy3](https://www.pypy.org/download.html) for speed.

## Status icons

Create a Shell Script/Task widget and set:

    Launch Path: /bin/bash
    Parameters: -c
    Script: /usr/local/bin/pypy3 /path/to/folder/btt-toggl.py status general

![off](readme_img/off.png)

For project-specific status, use: `btt-toggl.py status <workspace_id> <project_id>`

## Toggle projects

Set the respective widget's Action to Execute Shell Script/Task and set the script to:

    Launch Path: /bin/bash
    Parameters: -c
    Script: /usr/local/bin/pypy3 /path/to/folder/btt-toggl.py toggle <workspace_id> <project_id>

![multi](readme_img/multi.png)

## Documentation
[Toggl Track](https://track.toggl.com),
[Toggl API](https://github.com/toggl/toggl_api_docs/blob/master/toggl_api.md), [BTT Docs](https://docs.folivora.ai/), [BTT Forum](https://community.folivora.ai/), [PyPy](https://www.pypy.org/features.html)
