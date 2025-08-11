"""
Utilities for working with browser/session instances.
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

    tasks = []
    for i, browser in enumerate(browsers, 1):
        display_info(f"Closing browser {i}")
        close = getattr(browser, "close", None)
        if close is None:
            continue
        if asyncio.iscoroutinefunction(close):
            tasks.append(close())
        else:
            tasks.append(asyncio.to_thread(close))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    for i, result in enumerate(results, 1):
        if isinstance(result, Exception):
            display_error(f"Browser {i} close failed: {result}")
