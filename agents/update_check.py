"""Agent that notifies when a newer GitHub release is available."""
from __future__ import annotations

import json
import time
import urllib.request

from data.config_settings import get_update_repo
from utils.pretty_print import display_error, display_info

from .base import BaseAgent


class UpdateCheckAgent(BaseAgent):
    """Periodically checks the configured repo for new releases."""

    def __init__(self) -> None:
        self._next_check = 0.0

    async def on_start(self, **_: dict) -> None:
        await self._check_now()

    async def on_mission_tick(self, **_: dict) -> None:
        await self._maybe_check()

    async def on_transport_tick(self, **_: dict) -> None:
        await self._maybe_check()

    async def _maybe_check(self) -> None:
        if time.time() >= self._next_check:
            self._next_check = time.time() + 3600  # once per hour
            await self._check_now()

    async def _check_now(self) -> None:
        try:
            repo = get_update_repo()
            req = urllib.request.Request(
                f"https://api.github.com/repos/{repo}/releases/latest",
                headers={"User-Agent": "MscBot"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            latest = (data.get("tag_name") or "").strip()
            local = self._read_version()
            if latest and latest != local:
                display_info(f"Update available: {local} → {latest} (repo {repo})")
        except Exception as e:
            display_error(f"UpdateCheckAgent failed: {e}")

    def _read_version(self) -> str:
        try:
            with open("VERSION", "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            return "v0.0"
