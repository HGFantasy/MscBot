"""Agent that prints metrics summary at shutdown."""

from __future__ import annotations

from utils.metrics import snapshot
from utils.pretty_print import display_info

from .base import BaseAgent


class MetricsSummaryAgent(BaseAgent):
    async def on_shutdown(self, **_: dict) -> None:
        s = snapshot()
        display_info(
            "Summary: missions {seen}/{disp}/{defer} | transports {tseen}/{tcomp}/{tdefer} | errors={err}".format(
                seen=s.get("missions_seen", 0),
                disp=s.get("missions_dispatched", 0),
                defer=s.get("missions_deferred", 0),
                tseen=s.get("transports_seen", 0),
                tcomp=s.get("transports_completed", 0),
                tdefer=s.get("transports_deferred", 0),
                err=s.get("errors", 0),
            )
        )
