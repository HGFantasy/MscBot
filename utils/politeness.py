
# Project: MscBot
# License: MIT

import asyncio, random, time
from contextlib import asynccontextmanager
from playwright.async_api import TimeoutError as PWTimeoutError
from data.config_settings import get_page_min_dwell_range
from utils.backoff import get_delay_factor, record_timeout, record_good
from utils.auth_repair import ensure_authenticated

_site_gate = asyncio.Semaphore(2)

def set_max_concurrency(n: int) -> None:
    global _site_gate
    _site_gate = asyncio.Semaphore(max(1, int(n)))

async def sleep_jitter(base: float = 0.5, spread: float = 0.5) -> None:
    f = get_delay_factor()
    await asyncio.sleep(max(0.05, f * (base + random.random() * spread)))

@asynccontextmanager
async def site_gate():
    async with _site_gate:
        await sleep_jitter(0.15, 0.35)
        try:
            yield
        finally:
            await sleep_jitter(0.10, 0.25)

async def retry(coro_fn, attempts: int = 3, base_delay: float = 0.4):
    last_exc = None
    for i in range(attempts):
        try:
            res = await coro_fn()
            record_good()
            return res
        except Exception as e:
            last_exc = e; 
            record_timeout()
        await asyncio.sleep((base_delay * (2 ** i)) + random.random() * 0.3)
    raise last_exc

async def goto_safe(page, url: str, **kwargs):
    async with site_gate():
        result = await retry(lambda: page.goto(url, **kwargs))
        if "users/sign_in" in (page.url or ""):
            if await ensure_authenticated(page):
                result = await retry(lambda: page.goto(url, **kwargs))
        await page.wait_for_load_state('networkidle')
        await sleep_jitter(0.3, 0.5)
        return result

async def click_safe(page, selector: str, **kwargs):
    async with site_gate():
        await retry(lambda: page.wait_for_selector(selector, state="visible", timeout=12000))
        result = await retry(lambda: page.click(selector, **kwargs))
        await sleep_jitter(0.15, 0.35)
        return result

async def fill_safe(page, selector: str, text: str):
    async with site_gate():
        await retry(lambda: page.wait_for_selector(selector, state="visible", timeout=12000))
        result = await retry(lambda: page.fill(selector, text))
        await sleep_jitter(0.08, 0.25)
        return result

async def ensure_settled(page, selector=None):
    lo, hi = get_page_min_dwell_range()
    t0 = time.monotonic()
    try:
        await page.wait_for_load_state("networkidle")
        if selector:
            try:
                await page.wait_for_selector(selector, state="visible", timeout=10000)
            except Exception:
                pass
    finally:
        left = random.uniform(lo, hi) - (time.monotonic() - t0)
        if left > 0:
            await asyncio.sleep(left)
