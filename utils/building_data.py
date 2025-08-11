# Project: MscBot
# License: MIT

import json
import os
from typing import Any

from utils.pretty_print import display_info, display_error
from utils.politeness import goto_safe, ensure_settled


async def gather_building_data(browsers, count) -> None:
    """Fetch basic building information via the site's JSON API.

    Queries ``/api/buildings`` and persists a compact mapping of building
    ``id`` to its caption and type. Any failure is logged but does not raise
    so the bot can continue operating.
    """

    try:
        page = browsers[0].contexts[0].pages[0]
        await goto_safe(page, "https://www.missionchief.com")
        await ensure_settled(page)

        # Fetch the building list using the in-page fetch API to preserve cookies
        data: list[dict[str, Any]] = await page.evaluate(
            """async () => {
                const r = await fetch('/api/buildings');
                if (!r.ok) { return []; }
                return await r.json();
            }"""
        )

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
