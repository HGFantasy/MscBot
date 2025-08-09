
# Project: MissionchiefBot-X — Scheduling windows
# License: MIT

import asyncio, datetime as dt
from utils.pretty_print import display_info
from data.config_settings import get_windows_by_day, get_blackout_dates, get_global_active_windows

def _parse_hhmm(hhmm:str):
    h,m = hhmm.split(":"); return dt.time(int(h), int(m))

def _in_interval(now: dt.time, start: dt.time, end: dt.time):
    return (start <= end and start <= now <= end) or (start > end and (now >= start or now <= end))

def _intervals_for_day(day: dt.date):
    dow = day.weekday()  # Mon=0
    key = ["mon","tue","wed","thu","fri","sat","sun"][dow]
    per_day = get_windows_by_day().get(key,"")
    if not per_day:
        per_day = get_global_active_windows()
    out = []
    for rng in [x.strip() for x in per_day.split(",") if x.strip()]:
        s,e = rng.split("-")
        out.append((_parse_hhmm(s), _parse_hhmm(e)))
    return out

def is_blackout(day: dt.date) -> bool:
    return day.isoformat() in get_blackout_dates()

def is_now_active(now_dt=None) -> bool:
    now_dt = now_dt or dt.datetime.now()
    if is_blackout(now_dt.date()):
        return False
    for s,e in _intervals_for_day(now_dt.date()):
        if _in_interval(now_dt.time(), s, e):
            return True
    return False

def _next_start_after(now_dt: dt.datetime) -> dt.datetime:
    for d in range(0, 8):
        day = now_dt.date() + dt.timedelta(days=d)
        if is_blackout(day):
            continue
        ivals = _intervals_for_day(day)
        if not ivals:
            continue
        for s,_ in ivals:
            cand = dt.datetime.combine(day, s)
            if cand > now_dt:
                return cand
    return now_dt + dt.timedelta(minutes=10)

async def wait_if_outside():
    now_dt = dt.datetime.now()
    if is_now_active(now_dt):
        return
    next_start = _next_start_after(now_dt)
    display_info(f"Outside active hours — sleeping until {next_start.strftime('%Y-%m-%d %H:%M')}")
    await asyncio.sleep(max(1, (next_start - now_dt).total_seconds()))
