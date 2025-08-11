"""Agent to periodically clear cached configuration and data files."""

from __future__ import annotations

import time
from pathlib import Path

from data.config_settings import clear_cache
from utils.pretty_print import display_info

from .base import BaseAgent

# Data files that should be purged when clearing caches
DATA_FILES = [
    Path("data/deferred_missions.json"),
    Path("data/mission_attempts.json"),
    Path("data/stuck_missions.json"),
    Path("data/topups.json"),
    Path("data/vehicle_cooldowns.json"),
    Path("data/mission_data.json"),
    Path("data/deferred_transports.json"),
    Path("data/transport_attempts.json"),
    Path("data/destination_blacklist.json"),
    Path("data/type_caps.json"),
]


def _clear_data_files() -> None:
    for p in DATA_FILES:
        try:
            p.unlink(missing_ok=True)
        except Exception:
            continue


class CacheClearAgent(BaseAgent):
    """Clears cached configuration values and data files at a fixed interval."""

    def __init__(self) -> None:
        self._interval = 300.0  # seconds
        self._last_clear = 0.0

    async def on_start(self, **_: dict) -> None:
        self._last_clear = time.monotonic()

    async def on_mission_tick(self, **_: dict) -> None:
        await self._maybe_clear()

    async def on_transport_tick(self, **_: dict) -> None:
        await self._maybe_clear()

    async def on_event(self, event: str, **_: dict) -> None:
        if event == "cache_clear":
            self._clear_all()

    def _clear_all(self) -> None:
        clear_cache()
        _clear_data_files()
        display_info("Cache cleared")
        self._last_clear = time.monotonic()

    async def _maybe_clear(self) -> None:
        now = time.monotonic()
        if now - self._last_clear >= self._interval:
            self._clear_all()
