# utils/mission_data.py
# Purpose: Snapshot missions to data/mission_data.json while preserving earliest seen_ts
#          and skipping writes when nothing changed.
# License: MIT

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Dict

from utils.pretty_print import display_error, display_info
from utils.politeness import ensure_settled, goto_safe

SNAPSHOT_PATH = Path("data/mission_data.json")
MISSION_HREF_RE = re.compile(r"/missions/(\d+)")


def _read_existing() -> Dict[str, Any]:
    try:
        if SNAPSHOT_PATH.exists():
            with SNAPSHOT_PATH.open("r", encoding="utf-8") as f:
                return json.load(f) or {}
    except Exception:
        pass
    return {}


def _merge_preserving_seen_ts(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge incoming snapshot with existing file, keeping the earliest seen_ts per mission.
    """
    prev = _read_existing()
    now = int(time.time())

    for mid, rec in snapshot.items():
        prior = prev.get(mid) or {}
        try:
            prior_seen = int(prior.get("seen_ts") or 0)
        except Exception:
            prior_seen = 0

        curr_seen = rec.get("seen_ts")
        try:
            curr_seen = int(curr_seen) if curr_seen is not None else 0
        except Exception:
            curr_seen = 0

        if curr_seen <= 0 or curr_seen > now:
            curr_seen = now

        if prior_seen > 0 and prior_seen <= now:
            rec["seen_ts"] = min(prior_seen, curr_seen)
        else:
            rec["seen_ts"] = curr_seen

    return snapshot


def write_snapshot(snapshot: Dict[str, Any]) -> None:
    """
    Write mission snapshot to disk, preserving earliest seen_ts across rewrites.
    If nothing changed since last write, skip the write to reduce churn.
    """
    snapshot = _merge_preserving_seen_ts(snapshot)

    # Skip write if unchanged
    prev = _read_existing()
    try:
        unchanged = json.dumps(prev, sort_keys=True) == json.dumps(
            snapshot, sort_keys=True
        )
    except Exception:
        unchanged = False

    if unchanged:
        display_info("mission snapshot: unchanged; skipped write.")
        return

    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SNAPSHOT_PATH.open("w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)
    display_info(f"Wrote mission_data.json with {len(snapshot)} missions.")


async def _collect_from_page(page) -> Dict[str, Any]:
    """
    Collect missions from the home page by scanning anchors like /missions/<id>.
    """
    try:
        await goto_safe(page, "https://www.missionchief.com/")
        await ensure_settled(page)
    except Exception as e:
        display_error(f"mission snapshot: navigation failed: {e}")
        return {}

    anchors = page.locator('a[href^="/missions/"]')
    count = await anchors.count()
    snapshot: Dict[str, Any] = {}
    now = int(time.time())

    for i in range(count):
        try:
            a = anchors.nth(i)
            href = (await a.get_attribute("href")) or ""
            m = MISSION_HREF_RE.search(href)
            if not m:
                continue
            mid = m.group(1)
            try:
                title = (await a.inner_text()).strip()
            except Exception:
                title = "Dispatch"
            if not title:
                title = "Dispatch"

            snapshot[mid] = {"mission_name": title, "seen_ts": now}
        except Exception:
            continue

    return snapshot


async def check_and_grab_missions(*args, **kwargs) -> None:
    """
    Entry point used by Main.py.
    - If 'snapshot' dict is provided, it is persisted (earliest seen_ts preserved).
    - Otherwise, uses browsers[0] to scrape the home page and persist results.
    """
    direct_snapshot = kwargs.get("snapshot")
    if isinstance(direct_snapshot, dict):
        try:
            write_snapshot(direct_snapshot)
        except Exception as e:
            display_error(f"mission snapshot: write failed: {e}")
        return

    browsers = args[0] if args else None
    page = None
    try:
        if browsers:
            ctx = browsers[0].contexts[0]
            page = ctx.pages[0] if ctx.pages else await ctx.new_page()
    except Exception as e:
        display_error(f"mission snapshot: could not prepare page: {e}")

    if page is not None:
        collected = await _collect_from_page(page)
        if not collected:
            display_info(
                "mission snapshot: no missions found on page; preserving existing snapshot."
            )
            collected = _read_existing()
        try:
            write_snapshot(collected)
        except Exception as e:
            display_error(f"mission snapshot: write failed: {e}")
        return

    # Fallback: preserve existing (or write empty) if no page available
    try:
        existing = _read_existing()
        if existing:
            write_snapshot(existing)
        else:
            SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
            with SNAPSHOT_PATH.open("w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
            display_info("Wrote mission_data.json with 0 missions.")
    except Exception as e:
        display_error(f"mission snapshot fallback failed: {e}")
