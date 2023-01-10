import pathlib
this_directory = pathlib.Path(__file__).parent.absolute()

# Your API token from Toggl (Profile settings -> API Token)
API_TOKEN = '0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a'

# Path to images. Should have files active.png and inactive.png
PATH_TO_ACTIVE_IMG = (this_directory / 'images' / 'active.png').as_posix()
PATH_TO_INACTIVE_IMG = (this_directory / 'images' / 'inactive.png').as_posix()

# Path to cache JSON file. Should be write-able.
PATH_TO_CACHE_FILE = (this_directory / 'cache.json').as_posix()

# Dictionary mapping workspace and project to display name
# WID_PID_DICT = {<wid>: {<pid>: <display name>, ...}, ...}
WID_PID_DICT: dict[str, dict[str, str]] = {'1000000':{'100000001':'W1 P1',
                                                      '100000002':'W1 P2',
                                                      '100000003':'W1 P3'},
                                           '2000000':{'200000001':'W2 P1',
                                                      '200000002':'W2 P2'}}
# by default, btt-toggl will apply the tag "btt-toggl" to all entries it creates
TAG_ALL_ENTRIES = True

# by default, btt-toggl validates that command line arguments, paths, etc.
# once you have everything working, set this to False to speed up the script slightly (~5%).
# if you run into any problems, try setting this to True before you report an issue.
VALIDATION = True
