from typing import Union, Optional

WID_PID_TYPE = dict[str, dict[str, str]] # JSON {wid -> {pid -> display name, ...}}
CACHE_TYPE = dict[str, Union[dict[str, str], list[str]]] # JSON {wid -> {pid -> style string, ...}, ..., tags}
STR_KEY_JSON = dict[str, Union[dict, list, str, bool, type(None)]] # JSON with string keys
State = Optional[STR_KEY_JSON] # JSON if currently logging, None otherwise