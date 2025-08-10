
# Project: MscBot
# Maintained by: HGFantasy
# License: MIT

import configparser, os
from pathlib import Path
from functools import lru_cache

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent
CONFIG_PATH = PROJECT_ROOT / "config.ini"

config = configparser.ConfigParser()
if CONFIG_PATH.exists():
    config.read(CONFIG_PATH, encoding="utf-8")
else:
    config.read_dict({
        "credentials": {"username": "", "password": ""},
        "browser_settings": {"headless": "false", "browsers": "2", "slow_mo_ms": "350"},
        "delays": {"missions": "10", "transport": "180"},
        "human": {
            "preset": "normal",          # chill | normal | sweaty
            "short_break_prob": "0.06",
            "short_break_range": "15-45",
            "medium_break_prob": "0.03",
            "medium_break_range": "120-360",
            "long_break_prob": "0.008",
            "long_break_range": "900-1800",
            "quiet_hours": "02:00-06:30",
            "idle_after_page": "0.8-2.2",
            "page_min_dwell": "1.8-3.0",
        },
        "dispatch_filter": {
            "enable_eta_filter": "true",
            "max_eta_minutes": "25",
            "max_distance_km": "25",
            "max_per_mission": "6",
            "enable_defer": "true",
            "defer_recheck_min": "5",
            "defer_recheck_max": "10",
            "adaptive_step": "0.25",
            "adaptive_max_mult": "2.0"
        },
        "mission_age": {"min_age_seconds": "60"},
        "priority": {"keywords": ""},
        "transport_prefs": {
            "max_hospital_km": "25",
            "max_hospital_tax_pct": "20",
            "hospital_fallback": "wait",
            "hospital_recheck_min": "10",
            "max_prison_km": "25",
            "max_prison_tax_pct": "20",
            "prison_fallback": "wait",
            "prison_recheck_min": "10",
            "min_free_beds": "1",
            "min_free_cells": "1",
            "blacklist_ttl_min": "45"
        },
        "backoff": {
            "enable": "true",
            "timeout_threshold_seconds": "8",
            "factor_step": "0.25",
            "factor_max": "2.0",
            "cool_down_good_seconds": "120"
        },
        "dispatch": {
            "ambulance_only": "false",
        },
        "control": {
            "command_file": "commands.txt",
        },
        "update": {
            "repo": "HGFantasy/MscBot"
        },
        "agents": {
            "enabled": "",
            "disabled": "",
        },
    })

def _get(s, k, d=""):
    try:
        return config.get(s, k)
    except Exception:
        return d

def _getint(s, k, d):
    try:
        return config.getint(s, k)
    except Exception:
        return d

def _getfloat(s, k, d):
    try:
        return config.getfloat(s, k)
    except Exception:
        return d

def _getbool(s, k, d):
    try:
        return config.getboolean(s, k)
    except Exception:
        return d

_CACHED_FUNCS = []

def _cache(fn):
    cached = lru_cache(maxsize=None)(fn)
    _CACHED_FUNCS.append(cached)
    return cached

def get_username(): return os.getenv("MISSIONCHIEF_USER") or _get("credentials","username","")
def get_password(): return os.getenv("MISSIONCHIEF_PASS") or _get("credentials","password","")

@_cache
def get_headless():
    return _getbool("browser_settings","headless", False)

@_cache
def get_threads():
    return _getint("browser_settings","browsers", 2)

@_cache
def get_slow_mo_ms():
    return _getint("browser_settings","slow_mo_ms", 350)

@_cache
def get_mission_delay():
    return _getint("delays","missions", 10)

@_cache
def get_transport_delay():
    return _getint("delays","transport", 180)

@_cache

@_cache
def get_threads():
    return _getint("browser_settings","browsers", 2)

@_cache
def get_slow_mo_ms():
    return _getint("browser_settings","slow_mo_ms", 350)

@_cache
def get_mission_delay():
    return _getint("delays","missions", 10)

@_cache
def get_transport_delay():
    return _getint("delays","transport", 180)

@_cache
def get_human():
    preset = _get("human","preset","normal").lower().strip()
    scale = {"chill":0.8, "normal":1.0, "sweaty":1.25}.get(preset,1.0)

    def _rng(s, default):
        try:
            a, b = s.split("-")
            return (float(a), float(b))
        except Exception:
            return default

    idle_lo, idle_hi = _rng(_get("human","idle_after_page","0.8-2.2"), (0.8, 2.2))
    dwell_lo, dwell_hi = _rng(_get("human","page_min_dwell","1.8-3.0"), (1.8, 3.0))
    return {
        "preset": preset,
        "short_prob": _getfloat("human","short_break_prob", 0.06),
        "short_range": _get("human","short_break_range","15-45"),
        "medium_prob": _getfloat("human","medium_break_prob", 0.03),
        "medium_range": _get("human","medium_break_range","120-360"),
        "long_prob": _getfloat("human","long_break_prob", 0.008),
        "long_range": _get("human","long_break_range","900-1800"),
        "quiet_hours": _get("human","quiet_hours","02:00-06:30"),
        "quiet_mult": _getfloat("human","quiet_break_multiplier", 2.0),
        "idle_after_page": f"{idle_lo*scale:.2f}-{idle_hi*scale:.2f}",
        "page_min_dwell": f"{dwell_lo*scale:.2f}-{dwell_hi*scale:.2f}",
    }

@_cache
def get_page_min_dwell_range():
    s = _get("human","page_min_dwell","1.8-3.0")
    try:
        a, b = s.split("-")
        return (float(a), float(b))
    except Exception:
        return (1.8, 3.0)

@_cache
def get_eta_filter():
    return {
        "enable": _getbool("dispatch_filter","enable_eta_filter", True),
        "max_minutes": _getint("dispatch_filter","max_eta_minutes", 25),
        "max_km": _getfloat("dispatch_filter","max_distance_km", 25.0),
        "max_per_mission": _getint("dispatch_filter","max_per_mission", 6),
        "adaptive_step": _getfloat("dispatch_filter","adaptive_step", 0.25),
        "adaptive_max_mult": _getfloat("dispatch_filter","adaptive_max_mult", 2.0),
    }

@_cache
def get_defer_config():
    return {
        "enable": _getbool("dispatch_filter","enable_defer", True),
        "min_minutes": _getint("dispatch_filter","defer_recheck_min", 5),
        "max_minutes": _getint("dispatch_filter","defer_recheck_max", 10),
    }

@_cache
def get_min_mission_age_seconds():
    return _getint("mission_age","min_age_seconds", 60)

@_cache
def get_priority_keywords():
    raw = _get("priority","keywords","")
    return [x.strip().lower() for x in raw.split(",") if x.strip()]

def _dow_key(i):
    return ["mon","tue","wed","thu","fri","sat","sun"][i]

@_cache
def get_windows_by_day():
    return {_dow_key(i): _get("scheduling", _dow_key(i), "") for i in range(7)}

@_cache
def get_blackout_dates():
    raw = _get("scheduling","blackout_dates","")
    return {d.strip() for d in raw.split(",") if d.strip()}

# Backward-compat single active_windows for all days
@_cache
def get_global_active_windows():
    return _get("scheduling", "active_windows", "")

@_cache
def get_transport_prefs():
    return {
        "max_hospital_km": _getfloat("transport_prefs","max_hospital_km", 25.0),
        "max_hospital_tax_pct": _getfloat("transport_prefs","max_hospital_tax_pct", 20.0),
        "hospital_fallback": _get("transport_prefs","hospital_fallback","wait"),
        "hospital_recheck_min": _getint("transport_prefs","hospital_recheck_min", 10),
        "max_prison_km": _getfloat("transport_prefs","max_prison_km", 25.0),
        "max_prison_tax_pct": _getfloat("transport_prefs","max_prison_tax_pct", 20.0),
        "prison_fallback": _get("transport_prefs","prison_fallback","wait"),
        "prison_recheck_min": _getint("transport_prefs","prison_recheck_min", 10),
        "min_free_beds": _getint("transport_prefs","min_free_beds", 1),
        "min_free_cells": _getint("transport_prefs","min_free_cells", 1),
        "blacklist_ttl_min": _getint("transport_prefs","blacklist_ttl_min", 45),
    }

@_cache
def get_backoff_config():
    return {
        "enable": _getbool("backoff","enable", True),
        "timeout_threshold_seconds": _getint("backoff","timeout_threshold_seconds", 8),
        "factor_step": _getfloat("backoff","factor_step", 0.25),
        "factor_max": _getfloat("backoff","factor_max", 2.0),
        "cool_down_good_seconds": _getint("backoff","cool_down_good_seconds", 120),
    }

@_cache
def get_update_repo():
    return _get("update","repo","HGFantasy/MscBot")

@_cache
def get_ambulance_only():
    return _getbool("dispatch","ambulance_only", False)

def get_command_file():
    return _get("control","command_file","commands.txt")

def get_enabled_agents():
    raw = _get("agents", "enabled", "")
    return [x.strip() for x in raw.split(",") if x.strip()]

def get_disabled_agents():
    raw = _get("agents", "disabled", "")
    return [x.strip() for x in raw.split(",") if x.strip()]

def reload_config() -> None:
    """Reload configuration from disk for hot-reload agents."""
    if CONFIG_PATH.exists():
        config.read(CONFIG_PATH, encoding="utf-8")
        for f in _CACHED_FUNCS:
            f.cache_clear()
