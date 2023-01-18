import os, sys
from typing import Optional

try:
    import requests
except ImportError as e:
    print(f"btt-toggl v1 requires `requests` to communicate with the Toggl API.\n Install with: \n\t {sys.executable} -m pip install requests", flush=True)
    os._exit(1)

from custom_types import JSON_DICT, State
from config import API_TOKEN, TIMEOUT

session = requests.Session()

def get(url: str) -> State:
    """ Send a GET request, including authentication, then return the result as json."""
    resp: JSON_DICT = session.get(url, auth=(API_TOKEN, "api_token"), timeout=TIMEOUT).json(parse_int=str)
    return resp

def post(url: str, json: JSON_DICT) -> State:
    """ Send a POST request with json data, including authentication, then return the result as json."""
    resp: JSON_DICT = session.post(url, auth=(API_TOKEN, "api_token"), timeout=TIMEOUT, json=json).json(parse_int=str)
    return resp

def put(url: str, json: Optional[JSON_DICT]=None) -> State:
    """ Send a PUT request, including authentication, then return the result as json."""
    resp: JSON_DICT = session.put(url, auth=(API_TOKEN, "api_token"), timeout=TIMEOUT, json=json).json(parse_int=str)
    return resp

def patch(url: str, json: Optional[JSON_DICT]=None) -> State:
    """ Send a PATCH request with json data, including authentication, then return the result as json."""
    resp: JSON_DICT = session.patch(url, auth=(API_TOKEN, "api_token"), timeout=TIMEOUT, json=json).json(parse_int=str)
    return resp