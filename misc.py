import subprocess
# some helper functions for btt-toggl.py

def is_logging(data): return bool(data)
def vprint(string, v=True): return print(string) if v else string
def get_output(curl_output): return subprocess.check_output(curl_output, shell=True).decode('utf-8')