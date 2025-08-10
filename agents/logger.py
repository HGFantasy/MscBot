"""Example agent that logs lifecycle events."""
from __future__ import annotations

from utils.pretty_print import display_info

from .base import BaseAgent


class LoggerAgent(BaseAgent):
    async def on_start(self, **_: dict) -> None:
        display_info("LoggerAgent: bot starting")

    async def on_shutdown(self, **_: dict) -> None:
        display_info("LoggerAgent: bot shutting down")

