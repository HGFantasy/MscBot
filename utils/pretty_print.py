
# Project: MscBot
# Maintained by: HGFantasy
# License: MIT

import sys, datetime as dt

def _ts(): return dt.datetime.now().strftime("%H:%M:%S")

def display_info(msg: str):
    print(f"[{_ts()}] INFO: {msg}", flush=True)

def display_error(msg: str):
    print(f"[{_ts()}] ERROR: {msg}", file=sys.stderr, flush=True)
