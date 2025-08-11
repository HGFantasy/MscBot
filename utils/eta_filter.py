"""ETA and destination helper functions for MscBot."""

# License: MIT

import math
import re

from utils.pretty_print import display_info


_TIME_RE = re.compile(
    r"(?:(\d+)\s*h)?\s*(?:(\d+)\s*m(?:in)?)?\s*(?:(\d+)\s*s(?:ec)?)?",
    re.I,
)
_KM_RE = re.compile(r"([\d\.,]+)\s*km", re.I)
_M_RE = re.compile(r"([\d\.,]+)\s*m(?![a-z])", re.I)
_PCT_RE = re.compile(r"(\d+)\s*%")
_FREE_RE = re.compile(r"(free|available)\s*[:\-]?\s*(\d+)", re.I)
_BEDS_RE = re.compile(r"beds?\s*[:\-]?\s*(\d+)\s*/\s*(\d+)", re.I)
_CELLS_RE = re.compile(r"cells?\s*[:\-]?\s*(\d+)\s*/\s*(\d+)", re.I)


def _to_float(s: str) -> float:
    try:
        return float(s.replace(",", "."))
    except Exception:
        return math.inf


def parse_seconds(text: str) -> int:
    match = _TIME_RE.search(text or "")
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


def parse_km(text: str) -> float:
    text = text or ""
    match = _KM_RE.search(text)
    if match:
        return _to_float(match.group(1))
    match = _M_RE.search(text)
    if match:
        return _to_float(match.group(1)) / 1000.0
    return math.inf


def parse_pct(text: str) -> float:
    match = _PCT_RE.search(text or "")
    return float(match.group(1)) if match else math.inf


def parse_capacity(text: str):
    t = text or ""
    match = _BEDS_RE.search(t) or _CELLS_RE.search(t)
    if match:
        try:
            return int(match.group(2)) - int(match.group(1)), int(match.group(2))
        except Exception:
            pass
    match = _FREE_RE.search(t)
    if match:
        try:
            return int(match.group(2)), None
        except Exception:
            pass
    return (None, None)


async def count_vehicles_within_limits(
    page, max_minutes: int, max_km: float, stop_at: int = 1
) -> int:
    rows = page.locator("li, tr, div")
    n = min(await rows.count(), 400)
    good = 0
    for i in range(n):
        r = rows.nth(i)
        try:
            text = (await r.inner_text()).strip()
            eta_sec = parse_seconds(text)
            dist_km = parse_km(text)
            too_far = (eta_sec and eta_sec > max_minutes * 60) or (
                dist_km and dist_km > max_km
            )
            if too_far:
                continue
            good += 1
            if good >= stop_at:
                break
        except Exception:
            continue
    return good


async def select_vehicles_within_limits(
    page, max_minutes: int, max_km: float, max_pick: int = 6
) -> int:
    rows = page.locator("li, tr, div")
    n = min(await rows.count(), 400)
    picked = 0
    for i in range(n):
        if picked >= max_pick:
            break
        r = rows.nth(i)
        try:
            text = (await r.inner_text()).strip()
            eta_sec = parse_seconds(text)
            dist_km = parse_km(text)
            too_far = (eta_sec and eta_sec > max_minutes * 60) or (
                dist_km and dist_km > max_km
            )
            if too_far:
                continue
            ctl = r.locator(
                "input[type=checkbox], input[type=radio], button.select, a.select"
            )
            if await ctl.count() == 0:
                continue
            await ctl.first.click()
            picked += 1
        except Exception:
            continue
    display_info(
        f"Vehicle picker: selected {picked} within {max_minutes} min / {max_km} km"
    )
    return picked
