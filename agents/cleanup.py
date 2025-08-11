"""Cleanup agent to clear ephemeral data on shutdown.

Removes or resets per-run tracking files like deferred queues, attempts, and
blacklists to ensure a clean start next run.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from utils.pretty_print import display_info

from .base import BaseAgent

EPHEMERAL_FILES: tuple[str, ...] = (
    "data/deferred_missions.json",
    "data/deferred_transports.json",
    "data/destination_blacklist.json",
    "data/mission_attempts.json",
    "data/transport_attempts.json",
    "data/stuck_missions.json",
    "data/topups.json",
    "data/type_caps.json",
    "data/vehicle_cooldowns.json",
)


def _reset_json_files(paths: Iterable[str]) -> None:
    for p in paths:
        path = Path(p)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as f:
                json.dump({}, f)
        except Exception:
            # Best effort: ignore errors; shutdown should not be blocked
            pass


class CleanupAgent(BaseAgent):
    async def on_shutdown(self, **_: dict) -> None:
        display_info("CleanupAgent: clearing ephemeral data files…")
        _reset_json_files(EPHEMERAL_FILES)
        display_info("CleanupAgent: done.")
