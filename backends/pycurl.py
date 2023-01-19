import os, sys, json as _json

try:
    import pycurl as pc
except ImportError as e:
    print(f"{'~'*os.get_terminal_size().columns}\nRequested `pycurl` backend but could not import it.\n Install with: \n\t {sys.executable} -m pip install --compile --install-option=\"--with-openssl\" pycurl\n{'~'*os.get_terminal_size().columns}", flush=True)
    raise e

from io import BytesIO
from typing import Optional
from base64 import b64encode
from logging import debug

from utils import STR_KEY_JSON, State
from config import API_TOKEN, TIMEOUT

NoInternetExceptions = (pc.error,)

token = b64encode(f"{API_TOKEN}:api_token".encode("utf-8")).decode("utf-8")
headers = ["Authorization: Basic %s" % token, "Content-Type: application/json"]


def get_data(bio: BytesIO) -> State:
    return _json.loads(bio.getvalue(), parse_int=str)

def get(url: str) -> State:
    """ Send a GET request, including authentication, then return the result as json."""
    debug("GET %s", url)
    c = pc.Curl()
    bio = BytesIO()
    c.setopt(pc.URL, url)
    c.setopt(pc.HTTPHEADER, headers)
    c.setopt(pc.TIMEOUT, TIMEOUT)
    c.setopt(pc.HTTPGET, 1)
    c.setopt(pc.WRITEDATA, bio)
    c.perform()
    c.close()
    return get_data(bio)

def post(url: str, json: STR_KEY_JSON) -> State:
    """ Send a POST request with json data, including authentication, then return the result as json."""
    debug("POST %s", url)
    c = pc.Curl()
    bio = BytesIO()
    c.setopt(pc.URL, url)
    c.setopt(pc.HTTPHEADER, headers)
    c.setopt(pc.TIMEOUT, TIMEOUT)
    c.setopt(pc.POST, 1)
    c.setopt(pc.POSTFIELDS, _json.dumps(json))
    c.setopt(pc.WRITEDATA, bio)
    c.perform()
    c.close()
    return get_data(bio)

def put(url: str, json: Optional[STR_KEY_JSON]=None) -> State:
    """ Send a PUT request, including authentication, then return the result as json."""
    debug("PUT %s", url)
    c = pc.Curl()
    bio = BytesIO()
    c.setopt(pc.URL, url)
    c.setopt(pc.HTTPHEADER, headers)
    c.setopt(pc.TIMEOUT, TIMEOUT)
    c.setopt(pc.CUSTOMREQUEST, "PUT")
    if json is not None:
        c.setopt(pc.POSTFIELDS, _json.dumps(json))
    c.setopt(pc.WRITEDATA, bio)
    c.perform()
    c.close()
    return get_data(bio)

def patch(url: str, json: Optional[STR_KEY_JSON]=None) -> State:
    """ Send a PATCH request with json data, including authentication, then return the result as json."""
    debug("PATCH %s", url)
    c = pc.Curl()
    bio = BytesIO()
    c.setopt(pc.URL, url)
    c.setopt(pc.HTTPHEADER, headers)
    c.setopt(pc.TIMEOUT, TIMEOUT)
    c.setopt(pc.CUSTOMREQUEST, "PATCH")
    if json is not None:
        c.setopt(pc.POSTFIELDS, _json.dumps(json))
    c.setopt(pc.WRITEDATA, bio)
    c.perform()
    c.close()
    return get_data(bio)


