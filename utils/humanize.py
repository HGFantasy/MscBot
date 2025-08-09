
# Project: MissionchiefBot-X
# License: MIT

import asyncio, random, datetime as dt
from data.config_settings import get_human

def _parse_range(s: str, default=(0.5,1.5)):
    try:
        a,b = s.split("-"); return (float(a), float(b))
    except Exception:
        return default

def _in_quiet(hours: str) -> bool:
    try:
        start, end = hours.split("-")
        sh, sm = map(int, start.split(":")); eh, em = map(int, end.split(":"))
        now = dt.datetime.now().time()
        st = dt.time(sh, sm); en = dt.time(eh, em)
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
    def __init__(self, **kw):
        self.cfg = get_human()
        self.idle_rng = _parse_range(self.cfg.get("idle_after_page","0.8-2.2"), (0.8,2.2))
        self.quiet_hours = self.cfg.get("quiet_hours","02:00-06:30")

    async def idle_after_action(self):
        lo, hi = self.idle_rng
        await asyncio.sleep(random.uniform(lo, hi))

    async def maybe_break(self):
        r = random.random()
        if _in_quiet(self.quiet_hours):
            if r < 0.08:
                await asyncio.sleep(random.uniform(60, 180))
        else:
            if r < 0.03:
                await asyncio.sleep(random.uniform(20, 60))
