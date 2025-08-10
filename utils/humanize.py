
# Project: MscBot
# License: MIT

import asyncio, random, datetime as dt
from data.config_settings import get_human


def _parse_range(s: str, default=(0.5, 1.5)):
    """Return a (lo, hi) tuple from a ``"lo-hi"`` string."""
    try:
        a, b = s.split("-")
        return (float(a), float(b))
    except Exception:
        return default


def _in_quiet(hours: str) -> bool:
    """Return True if the current time is within ``hours`` ("HH:MM-HH:MM")."""
    try:
        start, end = hours.split("-")
        sh, sm = map(int, start.split(":"))
        eh, em = map(int, end.split(":"))
        now = dt.datetime.now().time()
        st = dt.time(sh, sm)
        en = dt.time(eh, em)
        return (st <= en and st <= now <= en) or (st > en and (now >= st or now <= en))
    except Exception:
        return False

async def gentle_mouse(page):
    try:
        box = await page.evaluate("""
            () => { return { w: window.innerWidth, h: window.innerHeight }; }
        """)
        x = random.randint(0, max(1, int(box["w"]*0.9)))
        y = random.randint(0, max(1, int(box["h"]*0.9)))
        await page.mouse.move(x, y)
    except Exception:
        pass

class Humanizer:
    """Simulate human pacing with configurable idles and breaks."""

    def __init__(self, **cfg):
        self.update_config(cfg or get_human())

    def update_config(self, cfg: dict) -> None:
        """Update internal timings from a config dict."""
        self.cfg = cfg
        self.idle_rng = _parse_range(cfg.get("idle_after_page", "0.8-2.2"), (0.8, 2.2))
        self.dwell_rng = _parse_range(cfg.get("page_min_dwell", "1.8-3.0"), (1.8, 3.0))
        self.quiet_hours = cfg.get("quiet_hours", "02:00-06:30")
        self.quiet_mult = float(cfg.get("quiet_mult", 2.0))
        self.break_profiles = [
            (float(cfg.get("long_prob", 0.008)), _parse_range(cfg.get("long_range", "900-1800"), (900, 1800))),
            (float(cfg.get("medium_prob", 0.03)), _parse_range(cfg.get("medium_range", "120-360"), (120, 360))),
            (float(cfg.get("short_prob", 0.06)), _parse_range(cfg.get("short_range", "15-45"), (15, 45))),
        ]

    async def idle_after_action(self) -> None:
        """Sleep briefly after an action to mimic natural pacing."""
        await asyncio.sleep(random.uniform(*self.idle_rng))

    async def page_dwell(self) -> None:
        """Ensure a minimum dwell time on pages after navigation."""
        await asyncio.sleep(random.uniform(*self.dwell_rng))

    async def maybe_break(self) -> None:
        """Occasionally take short, medium, or long breaks."""
        multiplier = self.quiet_mult if _in_quiet(self.quiet_hours) else 1.0
        for prob, rng in self.break_profiles:
            if random.random() < prob * multiplier:
                lo, hi = rng
                await asyncio.sleep(random.uniform(lo, hi))
                return
