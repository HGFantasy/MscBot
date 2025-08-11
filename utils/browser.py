"""
Utilities for working with Playwright browser instances.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable

from utils.pretty_print import display_error, display_info


async def close_browsers(browsers: Iterable) -> None:
    """Close all browser instances concurrently.

    Each browser is closed in parallel and any exception raised during shutdown
    is logged and suppressed so that remaining browsers still have a chance to
    close.
    """

    async def _close(i: int, browser) -> None:
        try:
            await browser.close()
        except Exception as e:  # pragma: no cover - best effort shutdown
            display_error(f"Browser {i} close failed: {e}")

    async with asyncio.TaskGroup() as tg:
        for i, browser in enumerate(browsers, 1):
            display_info(f"Closing browser {i}")
            tg.create_task(_close(i, browser))
