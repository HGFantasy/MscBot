# utils/sentinel.py
# Purpose: classify transient errors (rate limit / timeouts) and recommend extra delay
# License: MIT

from __future__ import annotations

import re
import time
from collections import deque

from utils.metrics import inc

# Keep the last ~2 minutes of error timestamps
_RATE_LIMITS: deque[int] = deque(maxlen=64)
_TIMEOUTS: deque[int] = deque(maxlen=64)

# Simple classifiers (tweakable without breaking callers)
_RE_RATE = re.compile(r"\b(429|too\s+many\s+requests|rate[-\s]?limit)\b", re.I)
_RE_TO = re.compile(r"\b(timeout|timed\s*out|net::ERR_|ETIMEDOUT|TimeoutError)\b", re.I)


def observe_error(msg: str) -> None:
    """Record error categories and raise metrics counters."""
    ts = int(time.time())
    if _RE_RATE.search(msg or ""):
        _RATE_LIMITS.append(ts)
        inc("rate_limit_hits", 1)
        inc("errors", 1)
    elif _RE_TO.search(msg or ""):
        _TIMEOUTS.append(ts)
        inc("timeouts", 1)
        inc("errors", 1)
    else:
        inc("errors", 1)


def _count_recent(q: deque[int], window_sec: int = 60) -> int:
    now = int(time.time())
    return sum(1 for t in q if now - t <= window_sec)


def recommend_extra_delay() -> float:
    """
    Suggest an extra sleep in seconds based on recent spikes.
    - >=5 RL/TO in last 60s  -> +10s
    - >=3 RL/TO in last 60s  -> +5s
    - otherwise               -> +0s
    """
    n = _count_recent(_RATE_LIMITS, 60) + _count_recent(_TIMEOUTS, 60)
    if n >= 5:
        return 10.0
    if n >= 3:
        return 5.0
    return 0.0
