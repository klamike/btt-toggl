import os, sys
from typing import Optional

try:
    import requests
except ImportError as e:
    print(f"Requested `requests` backend but could not import it.\n Install with: \n\t {sys.executable} -m pip install requests", flush=True)
    os._exit(1)

from custom_types import STR_KEY_JSON, State
from config import API_TOKEN, TIMEOUT

session = requests.Session()

NoInternetException = (requests.exceptions.ConnectionError, requests.exceptions.Timeout)

def get(url: str) -> State:
    """ Send a GET request, including authentication, then return the result as json."""
    resp: State = session.get(url, auth=(API_TOKEN, "api_token"), timeout=TIMEOUT).json(parse_int=str)
    return resp

def post(url: str, json: STR_KEY_JSON) -> State:
    """ Send a POST request with json data, including authentication, then return the result as json."""
    resp: State = session.post(url, auth=(API_TOKEN, "api_token"), timeout=TIMEOUT, json=json).json(parse_int=str)
    return resp

def put(url: str, json: Optional[STR_KEY_JSON]=None) -> State:
    """ Send a PUT request, including authentication, then return the result as json."""
    resp: State = session.put(url, auth=(API_TOKEN, "api_token"), timeout=TIMEOUT, json=json).json(parse_int=str)
    return resp

def patch(url: str, json: Optional[STR_KEY_JSON]=None) -> State:
    """ Send a PATCH request with json data, including authentication, then return the result as json."""
    resp: State = session.patch(url, auth=(API_TOKEN, "api_token"), timeout=TIMEOUT, json=json).json(parse_int=str)
    return resp
