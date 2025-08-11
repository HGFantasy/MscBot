# Project: MscBot
# License: MIT

import asyncio
import json
from pathlib import Path
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
        async with asyncio.timeout(10):
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

        data_path = Path("data") / "building_data.json"
        data_path.parent.mkdir(parents=True, exist_ok=True)
        data_path.write_text(json.dumps(mapped, indent=2), encoding="utf-8")
        display_info(f"Fetched {len(mapped)} buildings → {data_path}")

    except Exception as e:  # pragma: no cover - network/DOM failures
        display_error(f"gather_building_data failed: {e}")
