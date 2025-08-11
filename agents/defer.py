"""Mission deferral agent for MscBot."""

from __future__ import annotations

import json
import random
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from data.config_settings import get_defer_config
from utils.pretty_print import display_info

from .base import BaseAgent


@dataclass
class DeferredMission:
    """Record of a mission that has been deferred."""

    next_check: int = 0
    reason: str = ""
    updated: int = 0
    defer_count: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> DeferredMission:
        """Create a record from a raw dict."""
        return cls(
            next_check=int(data.get("next_check", 0)),
            reason=str(data.get("reason", "")),
            updated=int(data.get("updated", 0)),
            defer_count=int(data.get("defer_count", 0)),
        )


class DeferAgent(BaseAgent):
    """Persistently track missions that should be retried later."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path("data/deferred_missions.json")
        self.defer: dict[str, DeferredMission] = self._load()
        cfg = get_defer_config()
        self.enable = bool(cfg.get("enable", True))
        self.dmin = int(cfg.get("min_minutes", 5))
        self.dmax = int(cfg.get("max_minutes", 10))

    def enabled(self) -> bool:  # type: ignore[override]
        """Return whether the agent is active."""
        return self.enable

    def _load(self) -> dict[str, DeferredMission]:
        try:
            if self.path.exists():
                raw = json.loads(self.path.read_text(encoding="utf-8")) or {}
                return {k: DeferredMission.from_dict(v) for k, v in raw.items()}
        except Exception:
            pass
        return {}

    def _save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            data = {k: asdict(v) for k, v in self.defer.items()}
            self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass

    def get(self, mid: str) -> DeferredMission:
        """Retrieve the deferral record for ``mid`` if present."""
        return self.defer.get(mid, DeferredMission())

    def should_skip(self, mid: str, now: int) -> bool:
        """Return ``True`` if mission ``mid`` should be skipped at ``now``."""
        return self.get(mid).next_check > now

    def defer_mission(self, mid: str, reason: str) -> int:
        """Defer ``mid`` for a random delay and persist the record.

        Returns the delay in minutes.
        """

        now = int(time.time())
        delay = random.randint(self.dmin, self.dmax)
        rec = self.get(mid)
        self.defer[mid] = DeferredMission(
            next_check=now + delay * 60,
            reason=reason,
            updated=now,
            defer_count=rec.defer_count + 1,
        )
        self._save()
        display_info(f"Mission {mid}: deferred {delay} min ({reason}).")
        return delay

    def clear(self, mid: str) -> None:
        """Remove any deferral record for ``mid``."""
        if mid in self.defer:
            self.defer.pop(mid, None)
            self._save()

    def on_config_reload(self) -> None:
        """Refresh configuration values when config.ini is reloaded."""
        cfg = get_defer_config()
        self.enable = bool(cfg.get("enable", True))
        self.dmin = int(cfg.get("min_minutes", 5))
        self.dmax = int(cfg.get("max_minutes", 10))

    async def on_event(self, event: str, **kwargs: object) -> None:
        match event:
            case "config_reloaded":
                self.on_config_reload()
            case "defer_mission":
                mid = kwargs.get("mission_id")
                reason = kwargs.get("reason", "")
                if mid:
                    self.defer_mission(str(mid), str(reason))
