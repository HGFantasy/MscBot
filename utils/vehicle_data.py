# Project: MscBot
# License: MIT

import json
import os
from typing import Any

from utils.pretty_print import display_info, display_error
from utils.politeness import goto_safe, ensure_settled


async def gather_vehicle_data(browsers, count) -> None:
    """Fetch basic vehicle information via the site's JSON API.

    The previous implementation wrote a placeholder file which was not very
    useful.  The revamped version queries ``/api/vehicles`` and persists a
    compact mapping of vehicle ``id`` to its caption and type.  Any failure
    is logged but does not raise so the bot can continue operating.
    """

    try:
        page = browsers[0].contexts[0].pages[0]
        await goto_safe(page, "https://www.missionchief.com")
        await ensure_settled(page)

        # Fetch the vehicle list using the in-page fetch API to preserve cookies
        data: list[dict[str, Any]] = await page.evaluate(
            """async () => {
                const r = await fetch('/api/vehicles');
                if (!r.ok) { return []; }
                return await r.json();
            }"""
        )

        mapped = {
            str(v.get("id")): {
                "caption": v.get("caption", ""),
                "type": v.get("vehicle_type", v.get("type", "")),
            }
            for v in data
            if isinstance(v, dict)
        }

        os.makedirs("data", exist_ok=True)
        with open("data/vehicle_data.json", "w", encoding="utf-8") as f:
            json.dump(mapped, f, indent=2)
        display_info(f"Fetched {len(mapped)} vehicles → data/vehicle_data.json")

    except Exception as e:  # pragma: no cover - network/DOM failures
        display_error(f"gather_vehicle_data failed: {e}")
