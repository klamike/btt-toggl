import sys, subprocess, json
from typing import Union as U
# some helper functions for btt-toggl.py

def get_output(curl_str: str):
    return subprocess.check_output(curl_str, shell=True).decode('utf-8')
    
def get_data(curl_str) -> U[dict, None]:
    return json.loads(get_output(curl_str)).get('data')

def vprint(string: str, v: bool=True):
    return print(string) if v else string

def assertf(condition: bool, message: str) -> None:
    if not condition: print(message, file=sys.stderr); exit(1)