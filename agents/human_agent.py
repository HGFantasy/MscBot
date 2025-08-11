"""Agent that governs adaptive human-like pacing."""

from __future__ import annotations

from data.config_settings import get_human
from utils.humanize import Humanizer
from utils.politeness import set_human_active, sleep_jitter

from .base import BaseAgent


class HumanAgent(BaseAgent):
    """Insert human-like delays before and after each bot action."""

    def __init__(self) -> None:
        self._human = Humanizer(**get_human())

    async def on_start(self, **_: dict) -> None:
        set_human_active(True)

    async def on_mission_tick(self, **_: dict) -> None:
        await self._human.maybe_break()

    async def on_transport_tick(self, **_: dict) -> None:
        await self._human.maybe_break()

    async def on_event(self, event: str, **_: dict) -> None:
        if event == "config_reloaded":
            self._human.update_config(get_human())

    async def after_mission_tick(self, **_: dict) -> None:
        await self._pace()

    async def after_transport_tick(self, **_: dict) -> None:
        await self._pace()

    async def on_shutdown(self, **_: dict) -> None:
        set_human_active(False)

    async def _pace(self) -> None:
        await self._human.page_dwell()
        await self._human.idle_after_action()
        await sleep_jitter(0.6, 0.8)
