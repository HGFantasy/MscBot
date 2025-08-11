# Project: MscBot
# License: MIT

import asyncio
import json
import os
from typing import Any

from utils.pretty_print import display_error, display_info


async def gather_building_data(browsers, count) -> None:
    """Fetch basic building information via the site's JSON API.

    Queries ``/api/buildings`` and persists a compact mapping of building
    ``id`` to its caption and type. Any failure is logged but does not raise
    so the bot can continue operating.
    """

    try:
        session = browsers[0]
        resp = await asyncio.to_thread(session.get, "https://www.missionchief.com/api/buildings")
        data: list[dict[str, Any]] = resp.json() if resp.ok else []

        mapped = {
            str(b.get("id")): {
                "caption": b.get("caption", ""),
                "type": b.get("building_type", b.get("type", "")),
            }
            for b in data
            if isinstance(b, dict)
        }

        os.makedirs("data", exist_ok=True)
        with open("data/building_data.json", "w", encoding="utf-8") as f:
            json.dump(mapped, f, indent=2)
        display_info(f"Fetched {len(mapped)} buildings → data/building_data.json")

    except Exception as e:  # pragma: no cover - network/DOM failures
        display_error(f"gather_building_data failed: {e}")
