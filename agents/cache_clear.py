"""Agent to periodically clear cached configuration getters."""

from __future__ import annotations

import time

from data.config_settings import clear_cache
from utils.pretty_print import display_info

from .base import BaseAgent


class CacheClearAgent(BaseAgent):
    """Clears cached configuration values at a fixed interval."""

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
            clear_cache()
            display_info("Cache cleared")
            self._last_clear = time.monotonic()

    async def _maybe_clear(self) -> None:
        now = time.monotonic()
        if now - self._last_clear >= self._interval:
            clear_cache()
            display_info("Cache cleared")
            self._last_clear = now
