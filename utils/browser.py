"""
Utilities for working with Playwright browser instances.
"""

from __future__ import annotations

import asyncio
from typing import Iterable

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
        tasks.append(browser.close())

    results = await asyncio.gather(*tasks, return_exceptions=True)
    for i, result in enumerate(results, 1):
        if isinstance(result, Exception):
            display_error(f"Browser {i} close failed: {result}")
