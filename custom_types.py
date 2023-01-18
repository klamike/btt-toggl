from typing import Union, Optional

JSON_TYPES = Union[dict, list, str, bool, type(None)]
WID_PID_TYPE = dict[str, dict[str, str]]
CACHE_TYPE = dict[str, Union[dict[str, str], list[str]]]
JSON_DICT = dict[str, JSON_TYPES]
State = Optional[JSON_DICT]