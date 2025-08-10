"""Agent that checks the GitHub repo for newer commits."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request

from data.config_settings import get_update_repo
from utils.pretty_print import display_error, display_info

from .base import BaseAgent


class UpdateCheckAgent(BaseAgent):
    """Periodically checks the configured repo for new commits and updates."""

    def __init__(self) -> None:
        self._next_check = 0.0

    async def on_start(self, **_: dict) -> None:
        await self._check_now(auto_update=True)

    async def on_mission_tick(self, **_: dict) -> None:
        await self._maybe_check()

    async def on_transport_tick(self, **_: dict) -> None:
        await self._maybe_check()

    async def _maybe_check(self) -> None:
        if time.time() >= self._next_check:
            self._next_check = time.time() + 3600  # once per hour
            await self._check_now(auto_update=True)

    async def _check_now(self, auto_update: bool = False) -> None:
        try:
            repo = get_update_repo()
            req = urllib.request.Request(
                f"https://api.github.com/repos/{repo}/commits?per_page=1",
                headers={"User-Agent": "MscBot"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            latest = (data[0].get("sha") or "").strip() if data else ""
            local = self._local_commit()
            if latest and local and latest != local:
                display_info(
                    f"Update available: {local[:7]} → {latest[:7]} (repo {repo})"
                )
                if auto_update:
                    self._auto_update(repo)
        except Exception as e:
            display_error(f"UpdateCheckAgent failed: {e}")

    def _local_commit(self) -> str:
        try:
            return (
                subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    check=True,
                    text=True,
                    capture_output=True,
                ).stdout.strip()
            )
        except Exception:
            return ""

    def _auto_update(self, repo: str) -> None:
        try:
            subprocess.run([
                "git",
                "pull",
                f"https://github.com/{repo}.git",
            ], check=True)
            display_info("Repository auto-updated to latest commit. Restarting…")
            python = sys.executable
            os.execl(python, python, *sys.argv)
        except Exception as e:
            display_error(f"Auto-update failed: {e}")
