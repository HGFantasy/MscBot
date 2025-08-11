# Project: MscBot
# License: MIT

import asyncio
import os


async def wait_if_paused():
    while os.path.exists("PAUSE"):
        await asyncio.sleep(2)


def should_stop() -> bool:
    return os.path.exists("STOP")
