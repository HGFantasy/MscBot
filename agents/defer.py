from __future__ import annotations

"""Mission deferral agent for MscBot."""
import json, random, time
from pathlib import Path
from typing import Dict, Any

from .base import BaseAgent
from data.config_settings import get_defer_config
from utils.pretty_print import display_info

class DeferAgent(BaseAgent):
    def __init__(self) -> None:
        self.path = Path("data/deferred_missions.json")
        self.defer: Dict[str, Dict[str, Any]] = self._load()
        cfg = get_defer_config()
        self.enable = bool(cfg.get("enable", True))
        self.dmin = int(cfg.get("min_minutes", 5))
        self.dmax = int(cfg.get("max_minutes", 10))

    def enabled(self) -> bool:  # type: ignore[override]
        return self.enable

    def _load(self) -> Dict[str, Dict[str, Any]]:
        try:
            if self.path.exists():
                with self.path.open("r", encoding="utf-8") as f:
                    return json.load(f) or {}
        except Exception:
            pass
        return {}

    def _save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("w", encoding="utf-8") as f:
                json.dump(self.defer, f, indent=2)
        except Exception:
            pass

    def get(self, mid: str) -> Dict[str, Any]:
        return self.defer.get(mid, {"defer_count": 0, "next_check": 0})

    def skip(self, mid: str, now: int) -> bool:
        return int(self.get(mid).get("next_check", 0)) > now

    def defer_mission(self, mid: str, reason: str) -> int:
        now = int(time.time())
        delay = random.randint(self.dmin, self.dmax)
        rec = self.get(mid)
        self.defer[mid] = {
            "next_check": now + delay * 60,
            "reason": reason,
            "updated": now,
            "defer_count": int(rec.get("defer_count", 0)) + 1,
        }
        self._save()
        display_info(f"Mission {mid}: deferred {delay} min ({reason}).")
        return delay

    def clear(self, mid: str) -> None:
        if mid in self.defer:
            self.defer.pop(mid, None)
            self._save()

    def on_config_reload(self) -> None:
        cfg = get_defer_config()
        self.enable = bool(cfg.get("enable", True))
        self.dmin = int(cfg.get("min_minutes", 5))
        self.dmax = int(cfg.get("max_minutes", 10))

    async def on_event(self, event: str, **kwargs: Any) -> None:
        if event == "config_reloaded":
            self.on_config_reload()
        elif event == "defer_mission":
            mid = kwargs.get("mission_id")
            reason = kwargs.get("reason", "")
            if mid:
                self.defer_mission(str(mid), str(reason))
