import subprocess, json
from typing import Optional
# some helper functions for btt-toggl.py

def vprint(string: str, v:bool=True):
    return print(string) if v else string

def get_output(curl_str: str):
    return subprocess.check_output(curl_str, shell=True).decode('utf-8')
    
def get_data(curl_str) -> Optional[dict]:
    return json.loads(get_output(curl_str)).get('data')