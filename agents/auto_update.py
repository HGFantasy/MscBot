"""Agent that checks the GitHub repo for updates and auto-updates."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request

from data.config_settings import PROJECT_ROOT, get_update_settings
from utils.pretty_print import display_error, display_info

from .base import BaseAgent


class AutoUpdateAgent(BaseAgent):
    """Periodically checks the configured repo for new commits and updates."""

    def __init__(self) -> None:
        self._next_check = 0.0

    async def on_start(self, **_: dict) -> None:
        await self._check_now()

    async def on_mission_tick(self, **_: dict) -> None:
        await self._maybe_check()

    async def on_transport_tick(self, **_: dict) -> None:
        await self._maybe_check()

    async def check_now(self) -> None:
        await self._check_now()

    async def _maybe_check(self) -> None:
        cfg = get_update_settings()
        interval = max(cfg["interval"], 1) * 60
        if time.time() >= self._next_check:
            self._next_check = time.time() + interval
            await self._check_now()

    async def _check_now(self) -> None:
        cfg = get_update_settings()
        repo, branch, auto = cfg["repo"], cfg["branch"], cfg["auto"]
        try:
            req = urllib.request.Request(
                f"https://api.github.com/repos/{repo}/commits/{branch}",
                headers={"User-Agent": "MscBot"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            latest = (data.get("sha") or "").strip()
            local = self._local_commit()
            if latest and local and latest != local:
                display_info(f"Update available: {local[:7]} → {latest[:7]} (branch {branch})")
                if auto and self._can_update():
                    self._auto_update(repo, branch)
        except Exception as e:
            display_error(f"AutoUpdateAgent failed: {e}")

    def _local_commit(self) -> str:
        try:
            return subprocess.run(
                ["git", "rev-parse", "HEAD"],
                check=True,
                text=True,
                capture_output=True,
                cwd=str(PROJECT_ROOT),
            ).stdout.strip()
        except Exception:
            return ""

    def _can_update(self) -> bool:
        try:
            dirty = subprocess.run(
                ["git", "status", "--porcelain"],
                check=True,
                text=True,
                capture_output=True,
                cwd=str(PROJECT_ROOT),
            ).stdout.strip()
            if dirty:
                display_error("Local changes detected; skipping auto-update.")
                return False
            return True
        except Exception:
            return False

    def _auto_update(self, repo: str, branch: str) -> None:
        try:
            subprocess.run(
                ["git", "pull", f"https://github.com/{repo}.git", branch],
                check=True,
                cwd=str(PROJECT_ROOT),
            )
            display_info("Repository auto-updated to latest commit. Restarting…")
            python = sys.executable
            os.execl(python, python, *sys.argv)
        except Exception as e:
            display_error(f"Auto-update failed: {e}")
