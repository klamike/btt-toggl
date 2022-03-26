import sys, subprocess, json
from typing import Optional as O, Union as U, NoReturn
# some helper functions for btt-toggl.py

def vprint(string: str, v:bool=True):
    return print(string) if v else string

def get_output(curl_str: str):
    return subprocess.check_output(curl_str, shell=True).decode('utf-8')
    
def get_data(curl_str) -> O[dict]:
    return json.loads(get_output(curl_str)).get('data')

def assertf(condition: bool, message: str) -> None:
    if not condition: print(message, file=sys.stderr); exit(1)