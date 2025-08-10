"""Agent that hot-reloads config.ini when it changes."""
from __future__ import annotations

from typing import Optional

from data.config_settings import CONFIG_PATH, reload_config
from utils.pretty_print import display_error, display_info

from .base import BaseAgent

from .loader import emit
 main


class DynamicConfigAgent(BaseAgent):
    def __init__(self) -> None:
        self._last_mtime: Optional[float] = None

    async def on_start(self, **_: dict) -> None:
        if CONFIG_PATH.exists():
            self._last_mtime = CONFIG_PATH.stat().st_mtime

    async def on_mission_tick(self, **_: dict) -> None:
        await self._maybe_reload()

    async def on_transport_tick(self, **_: dict) -> None:
        await self._maybe_reload()

    async def _maybe_reload(self) -> None:
        try:
            if not CONFIG_PATH.exists():
                return
            mtime = CONFIG_PATH.stat().st_mtime
            if self._last_mtime is None:
                self._last_mtime = mtime
            elif mtime > self._last_mtime:
                reload_config()
                display_info("config.ini reloaded")
                self._last_mtime = mtime

                await emit("config_reloaded")
        except Exception as e:
            display_error(f"DynamicConfigAgent reload failed: {e}")

    async def on_event(self, event: str, **_: dict) -> None:
        if event == "config_reload":
            try:
                reload_config()
                display_info("config.ini reloaded")
                self._last_mtime = CONFIG_PATH.stat().st_mtime if CONFIG_PATH.exists() else None
                await emit("config_reloaded")
            except Exception as e:
                display_error(f"DynamicConfigAgent reload failed: {e}")


        except Exception as e:
            display_error(f"DynamicConfigAgent reload failed: {e}")

 main
