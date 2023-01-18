import json as _json
from typing import Optional
from base64 import b64encode
from logging import debug

from custom_types import STR_KEY_JSON, State
from config import API_TOKEN, TIMEOUT

token = b64encode(f"{API_TOKEN}:api_token".encode("utf-8")).decode("utf-8")
headers = {"Authorization": f"Basic {token}", "Content-Type": "application/json"}

import urllib.request, urllib.error, urllib.parse

NoInternetException = (urllib.error.URLError, urllib.error.HTTPError)

def do_request(req: urllib.request.Request) -> State:
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        resp: State = _json.loads(resp.read(), parse_int=str)
    return resp

def get(url: str) -> State:
    """ Send a GET request, including authentication, then return the result as json."""
    req = urllib.request.Request(url, headers=headers, method="GET")
    debug("GET %s", url)
    return do_request(req)

def post(url: str, json: STR_KEY_JSON) -> State:
    """ Send a POST request with json data, including authentication, then return the result as json."""
    req = urllib.request.Request(url, headers=headers, method="POST", data=_json.dumps(json).encode("utf-8"))
    debug("POST %s", url)
    return do_request(req)

def put(url: str, json: Optional[STR_KEY_JSON]=None) -> State:
    """ Send a PUT request, including authentication, then return the result as json."""
    kwargs = dict(headers=headers, method="PUT")
    if json is not None:
        kwargs['data'] = _json.dumps(json).encode("utf-8")

    req = urllib.request.Request(url, **kwargs)
    debug("PUT %s", url)
    return do_request(req)

def patch(url: str, json: Optional[STR_KEY_JSON]=None) -> State:
    """ Send a PATCH request with json data, including authentication, then return the result as json."""
    kwargs = dict(headers=headers, method="PATCH")
    if json is not None:
        kwargs['data'] = _json.dumps(json).encode("utf-8")

    req = urllib.request.Request(url, **kwargs)
    debug("PATCH %s", url)
    return do_request(req)
