
# Project: MissionchiefBot-X
# License: MIT

import asyncio, os

async def wait_if_paused():
    while os.path.exists("PAUSE"):
        await asyncio.sleep(2)

def should_stop() -> bool:
    return os.path.exists("STOP")
