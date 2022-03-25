import subprocess, json
from typing import Optional
# some helper functions for btt-toggl.py

def vprint(string: str, v:bool=True):
    return print(string) if v else string

class CurlReturnCodeException(Exception):
    def __init__(self, e:subprocess.CalledProcessError):
        self.cmd        = e.cmd
        self.output     = e.output
        self.stderr     = e.stderr
        self.returncode = e.returncode
        super().__init__(f"cURL exited with error code {self.returncode}. Likely no internet connection.")

def get_output(curl_str: str):
    try:
        return subprocess.check_output(curl_str, shell=True).decode('utf-8')
    except subprocess.CalledProcessError as e:
        raise CurlReturnCodeException(e)
    
def get_data(curl_str) -> Optional[dict]:
    return json.loads(get_output(curl_str)).get('data')