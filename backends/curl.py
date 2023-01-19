import json as _json
from subprocess import check_output, CalledProcessError
from typing import Optional
from logging import debug

from utils import STR_KEY_JSON, State
from config import API_TOKEN

CURL   = "curl -s "
AUTH   = f"-u {API_TOKEN}:api_token "
HEADER = '-H "Content-Type: application/json" '
PREFIX = CURL + AUTH + HEADER

DATA   = " -d '{}' "
GET, POST, PUT, PATCH = "-X GET ", "-X POST ", "-X PUT ", "-X PATCH "

NoInternetExceptions = (CalledProcessError,)

def get(url: str) -> State:
    """ Send a GET request, including authentication, then return the result as json."""
    command = PREFIX + GET + url
    debug("Running command %s", command)

    resp: State = _json.loads(check_output(command, shell=True).decode("utf-8"), parse_int=str)
    return resp

def post(url: str, json: STR_KEY_JSON) -> State:
    """ Send a POST request with json data, including authentication, then return the result as json."""
    command = PREFIX + POST + DATA.format(_json.dumps(json)) + url
    debug("Running command %s", command)

    resp: State = _json.loads(check_output(command, shell=True).decode("utf-8"), parse_int=str)
    return resp

def put(url: str, json: Optional[STR_KEY_JSON]=None) -> State:
    """ Send a PUT request, including authentication, then return the result as json."""
    if json is not None:
        command = PREFIX + PUT + DATA.format(_json.dumps(json)) + url
    else:
        command = PREFIX + PUT + url
    debug("Running command %s", command)

    resp: State = _json.loads(check_output(command, shell=True).decode("utf-8"), parse_int=str)
    return resp

def patch(url: str, json: Optional[STR_KEY_JSON]=None) -> State:
    """ Send a PATCH request with json data, including authentication, then return the result as json."""
    if json is not None:
        command = PREFIX + PATCH + DATA.format(_json.dumps(json)) + url
    else:
        command = PREFIX + PATCH + url
    debug("Running command %s", command)

    resp: State = _json.loads(check_output(command, shell=True).decode("utf-8"), parse_int=str)
    return resp
