# Project: MscBot
# License: MIT

"""Helpers for acting politely toward the MissionChief website.

These wrappers centralise concurrency limits, retry logic, and human-like
delays so the rest of the codebase can focus on high level behaviour.  They
also play nicely with the dynamic backoff system introduced in v2 and will
honour any configuration reloads at runtime.
"""

from __future__ import annotations

import asyncio
import random
import time
from contextlib import asynccontextmanager
from typing import Any
from collections.abc import Awaitable, Callable

from data.config_settings import get_page_min_dwell_range
from utils.auth_repair import ensure_authenticated
from utils.backoff import get_delay_factor, record_good, record_timeout

_site_gate = asyncio.Semaphore(2)


def set_max_concurrency(n: int) -> None:
    """Update the semaphore controlling concurrent page interactions."""
    global _site_gate
    _site_gate = asyncio.Semaphore(max(1, int(n)))


async def sleep_jitter(base: float = 0.5, spread: float = 0.5) -> None:
    """Sleep for a randomised duration scaled by the backoff factor."""
    f = get_delay_factor()
    await asyncio.sleep(max(0.05, f * (base + random.random() * spread)))


@asynccontextmanager
async def site_gate():
    """Limit concurrent site interactions and add a small entry/exit delay."""
    async with _site_gate:
        await sleep_jitter(0.15, 0.35)
        try:
            yield
        finally:
            await sleep_jitter(0.10, 0.25)


async def retry(
    coro_fn: Callable[[], Awaitable[Any]], attempts: int = 3, base_delay: float = 0.4
) -> Any:
    """Retry ``coro_fn`` with exponential backoff.

    ``record_good``/``record_timeout`` integrate with the adaptive backoff
    system so repeated timeouts will slow subsequent requests.  The function
    returns the result of ``coro_fn`` on success or raises the last
    encountered exception once attempts are exhausted.
    """
    last_exc: Exception | None = None
    for i in range(attempts):
        try:
            res = await coro_fn()
            record_good()
            return res
        except Exception as e:  # noqa: BLE001 - we want to bubble up original
            last_exc = e
            record_timeout()
        await asyncio.sleep((base_delay * (2**i)) + random.random() * 0.3)
    raise last_exc  # type: ignore[misc]


async def goto_safe(page, url: str, **kwargs):
    """Navigate to ``url`` with retries and polite gating."""
    async with site_gate():
        result = await retry(lambda: page.goto(url, **kwargs))
        if "users/sign_in" in (page.url or ""):
            if await ensure_authenticated(page):
                result = await retry(lambda: page.goto(url, **kwargs))
        await page.wait_for_load_state("networkidle")
        await sleep_jitter(0.3, 0.5)
        return result


async def click_safe(page, selector: str, **kwargs):
    """Click ``selector`` after waiting for it to be visible."""
    async with site_gate():
        await retry(
            lambda: page.wait_for_selector(selector, state="visible", timeout=12000)
        )
        result = await retry(lambda: page.click(selector, **kwargs))
        await sleep_jitter(0.15, 0.35)
        return result


async def fill_safe(page, selector: str, text: str):
    """Fill ``selector`` with ``text`` in a polite manner."""
    async with site_gate():
        await retry(
            lambda: page.wait_for_selector(selector, state="visible", timeout=12000)
        )
        result = await retry(lambda: page.fill(selector, text))
        await sleep_jitter(0.08, 0.25)
        return result


async def ensure_settled(page, selector: str | None = None) -> None:
    """Wait for ``page`` to reach ``networkidle`` and dwell a minimum time."""
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
