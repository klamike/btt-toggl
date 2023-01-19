import os, sys, json as _json
from typing import Optional
from base64 import b64encode
from logging import debug, getLogger

try:
    import urllib3, urllib3.exceptions, urllib3.poolmanager
except ImportError as e:
    print(f"{'~'*os.get_terminal_size().columns}\nRequested `urllib3` backend but could not import it.\n Install with: \n\t {sys.executable} -m pip install urllib3\n{'~'*os.get_terminal_size().columns}", flush=True)
    raise e

from utils import STR_KEY_JSON, State
from config import API_TOKEN, TIMEOUT

token = b64encode(f"{API_TOKEN}:api_token".encode("utf-8")).decode("utf-8")
headers = {"Authorization": f"Basic {token}", "Content-Type": "application/json"}

NoInternetExceptions = (urllib3.exceptions.NewConnectionError, urllib3.exceptions.MaxRetryError)
if "--debug" not in sys.argv and "--info" not in sys.argv: urllib3.disable_warnings()

http = urllib3.poolmanager.PoolManager()

def get_data(resp: urllib3.HTTPResponse) -> State:
    """ Return the json data (if any) from a HTTPResponse object."""
    out: State = _json.loads(resp.data.decode("utf-8"), parse_int=str)
    return out

def get(url: str) -> State:
    """ Send a GET request, including authentication, then return the result as json."""
    debug("GET %s", url)
    resp: urllib3.HTTPResponse = http.request("GET", url, headers=headers, timeout=TIMEOUT)
    return get_data(resp)

def post(url: str, json: STR_KEY_JSON) -> State:
    """ Send a POST request with json data, including authentication, then return the result as json."""
    debug("POST %s", url)
    resp: urllib3.HTTPResponse = http.request("POST", url, headers=headers, timeout=TIMEOUT, body=_json.dumps(json))
    return get_data(resp)

def put(url: str, json: Optional[STR_KEY_JSON]=None) -> State:
    """ Send a PUT request, including authentication, then return the result as json."""
    debug("PUT %s", url)
    kwargs = dict(headers=headers, timeout=TIMEOUT)
    if json is not None:
        kwargs['body'] = _json.dumps(json)
    resp: urllib3.HTTPResponse = http.request("PUT", url, **kwargs)
    return get_data(resp)

def patch(url: str, json: Optional[STR_KEY_JSON]=None) -> State:
    """ Send a PATCH request with json data, including authentication, then return the result as json."""
    debug("PATCH %s", url)
    kwargs = dict(headers=headers, timeout=TIMEOUT)
    if json is not None:
        kwargs['body'] = _json.dumps(json)
    resp: urllib3.HTTPResponse = http.request("PATCH", url, **kwargs)
    return get_data(resp)
