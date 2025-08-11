# utils/metrics.py
# Purpose: metrics counters persisted to logs/metrics.json + periodic heartbeat
# License: MIT

from __future__ import annotations
import json, time
from pathlib import Path
from typing import Dict, Any
from utils.pretty_print import display_info, display_error

METRICS_PATH = Path("logs/metrics.json")
WRITE_INTERVAL_SEC = 60        # ~once a minute
HEARTBEAT_INTERVAL_SEC = 90    # console health ping

# In-memory counters
_COUNTERS: Dict[str, int] = {
    "missions_seen": 0,
    "missions_deferred": 0,
    "missions_dispatched": 0,
    "transports_seen": 0,
    "transports_deferred": 0,
    "transports_completed": 0,
    "errors": 0,
    # New health/sentinel counters
    "rate_limit_hits": 0,
    "timeouts": 0,
    "reauths": 0,
    "state_reload": 0,
}
_LAST_WRITE_TS = 0
_LAST_HEARTBEAT_TS = 0

def _load_existing() -> Dict[str, Any]:
    try:
        if METRICS_PATH.exists():
            with METRICS_PATH.open("r", encoding="utf-8") as f:
                d = json.load(f) or {}
                for k, v in d.items():
                    if isinstance(v, int) and k not in _COUNTERS:
                        _COUNTERS[k] = v
                return d
    except Exception:
        pass
    return {}

def inc(name: str, n: int = 1) -> None:
    global _COUNTERS
    _COUNTERS[name] = int(_COUNTERS.get(name, 0)) + int(n)
    _COUNTERS["updated"] = int(time.time())

def set_value(name: str, value: int) -> None:
    global _COUNTERS
    _COUNTERS[name] = int(value)
    _COUNTERS["updated"] = int(time.time())

def snapshot() -> Dict[str, Any]:
    s = dict(_COUNTERS)
    s["updated"] = int(time.time())
    return s

def _write_now() -> None:
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with METRICS_PATH.open("w", encoding="utf-8") as f:
        json.dump(snapshot(), f, ensure_ascii=False, indent=2)

def maybe_write(force: bool = False) -> None:
    """
    Persist metrics ~once a minute and print a heartbeat every ~90 seconds.
    Safe to call frequently from loops.
    """
    global _LAST_WRITE_TS, _LAST_HEARTBEAT_TS
    now = int(time.time())

    if force or (now - _LAST_WRITE_TS) >= WRITE_INTERVAL_SEC:
        try:
            _write_now()
            _LAST_WRITE_TS = now
        except Exception as e:
            display_error(f"metrics write failed: {e}")

    if (now - _LAST_HEARTBEAT_TS) >= HEARTBEAT_INTERVAL_SEC:
        s = snapshot()
        display_info(
            f"[hb] missions {s.get('missions_seen',0)}/{s.get('missions_dispatched',0)}/{s.get('missions_deferred',0)} "
            f"| transports {s.get('transports_seen',0)}/{s.get('transports_completed',0)}/{s.get('transports_deferred',0)} "
            f"| reauths={s.get('reauths',0)} rl={s.get('rate_limit_hits',0)} to={s.get('timeouts',0)} err={s.get('errors',0)}"
        )
        _LAST_HEARTBEAT_TS = now
