import json as _json
from subprocess import check_output
from typing import Optional
from logging import debug

from custom_types import JSON_DICT, State
from config import API_TOKEN

CURL   = "curl -s "
AUTH   = f"-u {API_TOKEN}:api_token "
HEADER = '-H "Content-Type: application/json" '
DATA   = " -d '{}' "
GET, POST, PUT, PATCH = "-X GET ", "-X POST ", "-X PUT ", "-X PATCH "

def get(url: str) -> State:
    """ Send a GET request, including authentication, then return the result as json."""
    command = CURL + AUTH + GET + url
    debug("Running command %s", command)
    resp: JSON_DICT = check_output(command, shell=True).decode("utf-8")
    return _json.loads(resp, parse_int=str)

def post(url: str, json: JSON_DICT) -> State:
    """ Send a POST request with json data, including authentication, then return the result as json."""
    command = CURL + AUTH + HEADER + POST + DATA.format(_json.dumps(json)) + url
    debug("Running command %s", command)
    resp: JSON_DICT = check_output(command, shell=True).decode("utf-8")
    return _json.loads(resp, parse_int=str)

def put(url: str, json: Optional[JSON_DICT]=None) -> State:
    """ Send a PUT request, including authentication, then return the result as json."""
    if json is not None:
        command = CURL + AUTH + HEADER + PUT + DATA.format(_json.dumps(json)) + url
        debug("Running command %s", command)
        resp: JSON_DICT = check_output(command, shell=True).decode("utf-8")
    else:
        command = CURL + AUTH + HEADER + PUT + url
        debug("Running command %s", command)
        resp: JSON_DICT = check_output(command, shell=True).decode("utf-8")
    return _json.loads(resp, parse_int=str)

def patch(url: str, json: Optional[JSON_DICT]=None) -> State:
    """ Send a PATCH request with json data, including authentication, then return the result as json."""
    if json is not None:
        command = CURL + AUTH + HEADER + PATCH + DATA.format(_json.dumps(json)) + url
        debug("Running command %s", command)
        resp: JSON_DICT = check_output(command, shell=True).decode("utf-8")
    else:
        command = CURL + AUTH + HEADER + PATCH + url
        debug("Running command %s", command)
        resp: JSON_DICT = check_output(command, shell=True).decode("utf-8")
    return _json.loads(resp, parse_int=str)