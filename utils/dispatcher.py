# Project: MscBot — Mission dispatch
# Features: requirements-aware selection, second-wave top-up, priority scoring,
#           distance-band preference, soft caps per type, stuck-cancel (opt-in),
#           cooldowns + adaptive pacing + sentinel + reauth monitor kept.
# License: MIT

# ruff: noqa: E401,E402,E701,E702

from __future__ import annotations

import json
import math
import os
import random
import re
import time
from pathlib import Path
from typing import Any

from agents.defer import DeferredMission
from agents.loader import emit, get_agent
from data.config_settings import (
    get_ambulance_only,
    get_eta_filter,
    get_min_mission_age_seconds,
    get_priority_keywords,
)
from utils import sentinel

# If your build already exposes these helpers, we’ll still prefer them for basic gating.
# We’ll add type-aware finishing on top of the generic selection.
from utils.eta_filter import count_vehicles_within_limits, select_vehicles_within_limits
from utils.metrics import inc, maybe_write
from utils.orchestrator_client import get_priority_score
from utils.politeness import ensure_settled, goto_safe, sleep_jitter
from utils.pretty_print import display_error, display_info

# ----------------- Paths / Tunables -----------------
ATTEMPT_PATH = Path("data/mission_attempts.json")
VEH_CD_PATH = Path("data/vehicle_cooldowns.json")
TYPE_CAPS_PATH = Path("data/type_caps.json")
TOPUP_PATH = Path("data/topups.json")
STUCK_PATH = Path("data/stuck_missions.json")

ATTEMPT_BUDGET = 3  # retry budget per mission per run
COOLDOWN_RANGE_S = (60, 120)  # per-vehicle cooldown after use
STUCK_MINUTES = int(os.getenv("MCX_STUCK_MIN", "12"))  # minutes before smart-cancel check
CANCEL_STUCK = os.getenv("MCX_CANCEL_STUCK", "0") == "1"  # opt-in
TOPUP_MIN_SEC = 120  # second-wave recheck window (min/max randomized)
TOPUP_MAX_SEC = 240

# Type keywords → normalized type
TYPE_KEYWORDS: dict[str, list[str]] = {
    "engine": ["fire engine", "engine", "pumper", "lfb"],
    "ladder": ["ladder", "aerial", "truck", "tl", "platform"],
    "rescue": ["rescue", "heavy rescue", "rsv"],
    "hazmat": ["hazmat", "haz-mat", "hm"],
    "arff": ["arff", "crash tender", "airport fire"],
    "ambulance": ["ambulance", "als", "bls", "ems"],
    "police": ["police", "patrol", "k-9", "k9", "pd"],
}

_TYPE_PATTERNS = {
    typ: re.compile("|".join(re.escape(k) for k in kws)) for typ, kws in TYPE_KEYWORDS.items()
}

# Soft cap per type (simultaneous dispatches). Tracked by TTL so it decays naturally.
# Tweak via ENV like: MCX_SOFTCAP_LADDER=2
SOFT_CAP_TTL_S = 10 * 60
DEFAULT_SOFT_CAPS = {
    "ladder": int(os.getenv("MCX_SOFTCAP_LADDER", "2")),
    "hazmat": int(os.getenv("MCX_SOFTCAP_HAZMAT", "1")),
    "arff": int(os.getenv("MCX_SOFTCAP_ARFF", "1")),
}

# Distance bands (km)
BANDS = [(0.0, 10.0), (10.0, 20.0), (20.0, 40.0)]

# --- Hotfix from earlier: stable "first seen" per mission for this run (age gate) ---
RUN_FIRST_SEEN: dict[str, int] = {}


# ----------------- Utilities -----------------
def _load_json(p: Path) -> dict[str, Any]:
    try:
        if p.exists():
            with p.open("r", encoding="utf-8") as f:
                return json.load(f) or {}
    except Exception:
        pass
    return {}


def _save_json(p: Path, d: dict[str, Any]) -> None:
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            json.dump(d, f, indent=2)
    except Exception as e:
        display_error(f"Could not save {p.name}: {e}")


def _cleanup_ttl(d: dict[str, int], ttl: int) -> dict[str, int]:
    now = int(time.time())
    return {k: v for k, v in d.items() if int(v) > now - ttl}


def _priority_score(name: str) -> int:
    """Score a mission title using the Go service."""
    try:
        return get_priority_score(name)
    except Exception as exc:
        display_error(f"priority score failed: {exc}")
        return 0


def _classify_type(text: str) -> str | None:
    t = (text or "").lower()
    for typ, pat in _TYPE_PATTERNS.items():
        if pat.search(t):
            return typ
    return None


_RE_MIN = re.compile(r"(\d+)\s*min", re.I)
_RE_KM = re.compile(r"(\d+(?:\.\d+)?)\s*km", re.I)


def _parse_min(text: str) -> int | None:
    m = _RE_MIN.search(text or "")
    return int(m.group(1)) if m else None


def _parse_km(text: str) -> float | None:
    m = _RE_KM.search(text or "")
    return float(m.group(1)) if m else None


async def _fetch_vehicle_rows(page) -> list[dict[str, Any]]:
    """
    Gather available vehicle checkboxes on mission page with their row text.
    """
    rows = await page.evaluate(
        """() => {
        const out = [];
        const boxes = document.querySelectorAll('input[type=checkbox][name*="vehicle"]');
        boxes.forEach(cb => {
            const row = cb.closest('tr,li,div') || cb;
            const txt = row.innerText || row.textContent || '';
            out.push({ id: String(cb.value || cb.getAttribute('data-vehicle-id') || ''), text: txt, checked: cb.checked });
        });
        return out;
    }"""
    )
    items: list[dict[str, Any]] = []
    for r in rows or []:
        txt = r.get("text") or ""
        items.append(
            {
                "id": r.get("id"),
                "text": txt,
                "type": _classify_type(txt),
                "eta_min": _parse_min(txt),
                "km": _parse_km(txt),
                "checked": bool(r.get("checked", False)),
            }
        )
    return [x for x in items if x.get("id")]


async def _check_box_by_id(page, vid: str) -> bool:
    try:
        loc = page.locator(f'input[type="checkbox"][name*="vehicle"][value="{vid}"]')
        await loc.wait_for(state="attached", timeout=2000)
        await loc.check()
        return True
    except Exception:
        return False


async def _uncheck_box_by_id(page, vid: str) -> bool:
    try:
        loc = page.locator(f'input[type="checkbox"][name*="vehicle"][value="{vid}"]')
        await loc.wait_for(state="attached", timeout=2000)
        await loc.uncheck()
        return True
    except Exception:
        return False


def _count_types(rows: list[dict[str, Any]], checked_only: bool = True) -> dict[str, int]:
    c: dict[str, int] = {}
    for r in rows:
        if checked_only and not r["checked"]:
            continue
        t = r.get("type")
        if not t:
            continue
        c[t] = c.get(t, 0) + 1
    return c


def _distance_band(km: float | None) -> int:
    if km is None:
        return 99
    for i, (lo, hi) in enumerate(BANDS):
        if lo <= km < hi:
            return i
    return 99


async def _select_more_of_type(
    page,
    rows: list[dict[str, Any]],
    typ: str,
    need: int,
    max_minutes: int,
    max_km: float,
    max_pick: int,
) -> int:
    """
    Option #1 + #17 + #18: satisfy missing type counts, with distance-band preference
    and soft caps. Returns how many additional were selected.
    """
    if need <= 0:
        return 0

    # Soft cap check
    caps = _load_json(TYPE_CAPS_PATH)
    caps = {k: int(v) for k, v in caps.items()}
    soft_cap = DEFAULT_SOFT_CAPS.get(typ, 999999)
    current = int(caps.get(typ, 0))
    if current >= soft_cap:
        inc("type_softcap_skips", 1)
        display_info(f"[softcap] Skipping extra {typ}: {current}/{soft_cap} active.")
        return 0

    # Available candidates of type within limits
    cand = [
        r
        for r in rows
        if (not r["checked"])
        and r.get("type") == typ
        and (r.get("eta_min") is None or r["eta_min"] <= max_minutes)
        and (r.get("km") is None or r["km"] <= max_km)
    ]
    # Band + distance + ETA sort
    cand.sort(
        key=lambda r: (
            _distance_band(r.get("km")),
            r.get("km") or 1e9,
            r.get("eta_min") or 1e9,
        )
    )

    added = 0
    # Count currently checked
    total_checked = sum(1 for r in rows if r["checked"])

    for r in cand:
        if added >= need:
            break
        if total_checked >= max_pick:
            break
        ok = await _check_box_by_id(page, r["id"])
        if ok:
            r["checked"] = True
            added += 1
            total_checked += 1

    # Increase cap counter for TTL tracking
    if added > 0 and soft_cap < 999999:
        # store as “count until ts”; simple approximate — increases by 1 per selection with decay on read
        caps[typ] = current + added
        _save_json(TYPE_CAPS_PATH, caps)
        display_info(f"[softcap] {typ}: +{added} (est active {caps[typ]}/{soft_cap})")

    return added


def _parse_requirements(text: str) -> dict[str, int]:
    """
    Option #1: lightweight requirements parser from mission page text.
    Looks for patterns like '2 Ladder', '1 Hazmat', '3 Ambulance' etc.
    """
    if not text:
        return {}
    t = text.lower()
    req: dict[str, int] = {}
    # Common forms: "2x Ladder", "2 Ladder", "Requires: 2 Ladder", etc.
    for typ, kws in TYPE_KEYWORDS.items():
        for kw in kws:
            for m in re.finditer(rf"(\d+)\s*(?:x\s*)?{re.escape(kw)}", t):
                req[typ] = max(req.get(typ, 0), int(m.group(1)))
    return req


async def _requirements_from_page(page) -> dict[str, int]:
    try:
        # Read a reasonably big slice of text; avoid super-specific selectors
        txt = await page.inner_text("body")
    except Exception:
        txt = ""
    req = _parse_requirements(txt)
    return req


def _soft_prioritize(
    items: list[tuple[str, str, dict[str, Any]]],
) -> list[tuple[str, str, dict[str, Any]]]:
    # Items contain (title, mission_id, data). Use keyword score + age as tiebreaker.
    def score(title: str, seen_ts: int) -> int:
        s = _priority_score(title)
        age_bonus = min(10, int((int(time.time()) - seen_ts) / 60))  # +1 per minute, cap 10
        return s * 10 + age_bonus

    return sorted(items, key=lambda x: -score(x[0], int(x[2].get("seen_ts", int(time.time())))))


async def _record_cooldowns(picked_ids: list[str]) -> None:
    if not picked_ids:
        return
    cd = _load_json(VEH_CD_PATH)
    now = int(time.time())
    until = now + random.randint(*COOLDOWN_RANGE_S)
    for vid in picked_ids:
        cd[str(vid)] = until
    _save_json(VEH_CD_PATH, cd)
    display_info(
        f"[cooldown] set {len(picked_ids)} vehicles on cooldown for ~{COOLDOWN_RANGE_S[0]}–{COOLDOWN_RANGE_S[1]}s"
    )


async def _selected_vehicle_ids(page) -> list[str]:
    try:
        ids = await page.evaluate(
            """()=>{
            const out=[];
            document.querySelectorAll('input[type=checkbox][name*="vehicle"]:checked').forEach(cb=>{
                const v = cb.value || cb.getAttribute('data-vehicle-id');
                if(v) out.push(String(v));
            });
            return out;
        }"""
        )
        return [x for x in ids if x]
    except Exception:
        return []


async def _click_dispatch(page) -> bool:
    """Click the dispatch/alarm button on a mission page.

    The site uses a few variations for the dispatch button depending on
    context (regular missions, top-ups, ambulance-only, etc.).  We try a
    sequence of reasonably specific selectors and return ``True`` on the
    first successful click.  ``False`` is returned if none of the selectors
    could be activated.
    """

    selectors = [
        "#mission_alarm_btn",
        "#dispatch_button",
        "#alarm_button",
        'button:has-text("Alarm")',
        'button:has-text("Dispatch")',
        'a.btn-success:has-text("Alarm")',
        'a.btn-success:has-text("Dispatch")',
    ]
    for sel in selectors:
        try:
            btn = page.locator(sel).first
            await btn.wait_for(state="visible", timeout=4000)
            await btn.click()
            return True
        except Exception:
            continue
    return False


async def _handle_stuck_cancel(ctx) -> None:
    """Option #13: if enabled and missions look stuck for long, recall one unit."""
    if not CANCEL_STUCK:
        return
    stuck = _load_json(STUCK_PATH)
    if not stuck:
        return
    now = int(time.time())
    for mid, rec in list(stuck.items()):
        ts = int(rec.get("dispatched_ts", 0))
        if ts and (now - ts) >= STUCK_MINUTES * 60:
            try:
                page = ctx.pages[0] if ctx.pages else await ctx.new_page()
                await goto_safe(page, f"https://www.missionchief.com/missions/{mid}")
                await ensure_settled(page)
                # Primitive progress check: if “0%” text visible, act.
                body = (await page.inner_text("body")).lower()
                if "0%" in body or "0 % " in body:
                    rel = page.locator("a.btn.btn-xs.btn-danger").first
                    try:
                        await rel.wait_for(state="visible", timeout=1500)
                        await rel.click()
                        await ensure_settled(page)
                        inc("stuck_cancels", 1)
                        maybe_write()
                        display_info(
                            f"[stuck] Mission {mid}: released one unit (0% for ≥{STUCK_MINUTES}m)."
                        )
                    except Exception:
                        pass
                # In all cases, schedule next check later
                stuck[mid]["dispatched_ts"] = now  # push out window
                _save_json(STUCK_PATH, stuck)
            except Exception as e:
                display_error(f"[stuck] check failed on {mid}: {e}")
                sentinel.observe_error(str(e))


async def _handle_topups(ctx, max_minutes: int, max_km: float, max_pick: int) -> None:
    """Option #2: run second-wave top-ups that are due now."""
    due = _load_json(TOPUP_PATH)
    if not due:
        return
    now = int(time.time())
    dirty = False
    for mid, rec in list(due.items()):
        if int(rec.get("topup_due", 0)) > now:
            continue
        try:
            page = ctx.pages[0] if ctx.pages else await ctx.new_page()
            await goto_safe(page, f"https://www.missionchief.com/missions/{mid}")
            await ensure_settled(page, selector="#missionH1")
            # Parse requirements and available rows
            rows = await _fetch_vehicle_rows(page)
            req = await _requirements_from_page(page)
            # Count currently checked (already assigned on this page selection)
            have = _count_types(rows, checked_only=True)
            added_total = 0
            for typ, need in req.items():
                missing = max(0, need - have.get(typ, 0))
                if missing > 0:
                    added_total += await _select_more_of_type(
                        page, rows, typ, missing, max_minutes, max_km, max_pick
                    )
                    # refresh have map
                    have = _count_types(await _fetch_vehicle_rows(page), checked_only=True)
            if added_total > 0:
                if await _click_dispatch(page):
                    await ensure_settled(page)
                    inc("missions_topped_up", 1)
                    maybe_write()
                    display_info(f"[topup] Mission {mid}: sent +{added_total} (req-based).")
            # Clear the record (single pass)
            due.pop(mid, None)
            dirty = True
        except Exception as e:
            display_error(f"[topup] {mid} failed: {e}")
            sentinel.observe_error(str(e))
            # try again later
            due[mid]["topup_due"] = now + 120
            dirty = True
    if dirty:
        _save_json(TOPUP_PATH, due)


# ----------------- Main entry -----------------
async def navigate_and_dispatch(browsers):
    # Load snapshot
    try:
        with open("data/mission_data.json", encoding="utf-8") as f:
            all_missions = json.load(f) or {}
    except Exception as e:
        display_error(f"Could not read mission_data.json: {e}")
        sentinel.observe_error(str(e))
        return

    # Config
    min_age = get_min_mission_age_seconds()
    prios = get_priority_keywords()
    filt = get_eta_filter()
    ambulance_only_mode = get_ambulance_only()
    adaptive_step = float(filt.get("adaptive_step", 0.25))
    adaptive_max = float(filt.get("adaptive_max_mult", 2.0))
    max_minutes_base = int(filt.get("max_minutes", 25))
    max_km_base = float(filt.get("max_km", 25.0))
    max_pick = int(filt.get("max_per_mission", 6))

    defer_agent = get_agent("defer")
    now = int(time.time())
    attempts = _load_json(ATTEMPT_PATH)

    total_loaded = len(all_missions)
    display_info(f"[dispatch] loaded {total_loaded} missions from snapshot; min_age={min_age}s")

    # Build candidates (exclude too-young; then apply our own priority scoring)
    cand: list[tuple[str, str, dict[str, Any]]] = []
    for mid, data in all_missions.items():
        if mid not in RUN_FIRST_SEEN:
            s = int(data.get("seen_ts", now))
            s = s if 0 < s <= now else now
            RUN_FIRST_SEEN[mid] = s
        if (now - RUN_FIRST_SEEN[mid]) < min_age:
            continue
        title = data.get("mission_name", "") or ""
        # Keep old priority bucket influence by boosting score if it matches keywords
        if any((kw and kw.lower() in title.lower()) for kw in prios):
            title = "major " + title
        cand.append((title, mid, data))

    # Score & cap
    cand = _soft_prioritize(cand)
    # 17–31 per cycle (per docs)
    picked = cand[: random.randint(17, 31)]
    inc("missions_seen", len(picked))
    maybe_write()
    display_info(
        f"[dispatch] after age filter => candidates={len(picked)} (of loaded={total_loaded})"
    )

    # Page/context
    try:
        ctx = browsers[0].contexts[0]
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
    except Exception as e:
        display_error(f"Could not prepare mission page: {e}")
        sentinel.observe_error(str(e))
        return

    # Option #13: check stuck missions (opt-in)
    await _handle_stuck_cancel(ctx)

    # Option #2: run second-wave top-ups due now (skip if ambulance-only)
    if not ambulance_only_mode:
        await _handle_topups(ctx, max_minutes_base, max_km_base, max_pick)

    # Iterate missions
    for _title, mission_id, _data in picked:
        ntry = int(attempts.get(mission_id, 0))
        if ntry >= ATTEMPT_BUDGET:
            continue

        rec = defer_agent.get(mission_id) if defer_agent else DeferredMission()
        if defer_agent and defer_agent.should_skip(mission_id, now):
            continue

        widen_mult = min(1.0 + rec.defer_count * adaptive_step, adaptive_max)
        max_minutes = int(math.ceil(max_minutes_base * widen_mult))
        max_km = max_km_base * widen_mult

        try:
            # Visit mission page
            await goto_safe(page, f"https://www.missionchief.com/missions/{mission_id}")
            await ensure_settled(page, selector="#missionH1")

            # Reauth bounce monitor
            try:
                if "sign_in" in (page.url or "") or "login" in (page.url or ""):
                    inc("reauths", 1)
                    maybe_write()
                    display_info("[auth] session reauth detected during mission dispatch.")
            except Exception:
                pass

            if ambulance_only_mode:
                rows = await _fetch_vehicle_rows(page)
                amb = next(
                    (
                        r
                        for r in rows
                        if r.get("type") == "ambulance"
                        and (r.get("eta_min") is None or r["eta_min"] <= max_minutes)
                        and (r.get("km") is None or r["km"] <= max_km)
                    ),
                    None,
                )
                if not amb:
                    await emit(
                        "defer_mission",
                        mission_id=mission_id,
                        reason="no ambulance within limits",
                    )
                    inc("missions_deferred", 1)
                    maybe_write()
                    continue
                await _check_box_by_id(page, amb["id"])
                try:
                    picked_ids = [amb["id"]]
                    if not await _click_dispatch(page):
                        raise RuntimeError("dispatch button not ready")
                    await ensure_settled(page)
                    inc("missions_dispatched", 1)
                    maybe_write()
                    display_info(f"Mission {mission_id}: dispatched ambulance-only.")
                    await _record_cooldowns(picked_ids)
                    stuck = _load_json(STUCK_PATH)
                    stuck[mission_id] = {"dispatched_ts": int(time.time())}
                    _save_json(STUCK_PATH, stuck)
                    if defer_agent:
                        defer_agent.clear(mission_id)
                    attempts.pop(mission_id, None)
                except Exception as e:
                    attempts[mission_id] = ntry + 1
                    display_error(
                        f"Mission {mission_id}: dispatch button not ready (attempt {attempts[mission_id]}/{ATTEMPT_BUDGET})."
                    )
                    sentinel.observe_error(str(e))
                await ensure_settled(page)
                continue

            # Check eligibility (generic gate)
            eligible = await count_vehicles_within_limits(page, max_minutes, max_km, stop_at=1)
            if eligible < 1:
                await emit(
                    "defer_mission",
                    mission_id=mission_id,
                    reason=f"no vehicles within limits (x{widen_mult:.2f})",
                )
                inc("missions_deferred", 1)
                maybe_write()
                continue

            # First pass selection (generic)
            base_selected = await select_vehicles_within_limits(
                page, max_minutes, max_km, max_pick=max_pick
            )

            # Requirements-aware finishing (Options #1, #17, #18)
            rows = await _fetch_vehicle_rows(page)
            req = await _requirements_from_page(page)
            have = _count_types(rows, checked_only=True)

            added = 0
            for typ, need in req.items():
                missing = max(0, need - have.get(typ, 0))
                if missing <= 0:
                    continue
                added += await _select_more_of_type(
                    page, rows, typ, missing, max_minutes, max_km, max_pick
                )
                # refresh rows/have
                rows = await _fetch_vehicle_rows(page)
                have = _count_types(rows, checked_only=True)

            # If we exceeded max_pick, uncheck some non-required types
            total_checked = sum(1 for r in rows if r["checked"])
            if total_checked > max_pick:
                # Prefer keeping required types; uncheck untyped/extra
                over = total_checked - max_pick
                extras = [r for r in rows if r["checked"] and (r.get("type") not in req)]
                for r in extras[:over]:
                    await _uncheck_box_by_id(page, r["id"])

            # Dispatch / click
            try:
                # Capture chosen IDs for cooldowns/soft caps
                picked_ids = await _selected_vehicle_ids(page)
                if not await _click_dispatch(page):
                    raise RuntimeError("dispatch button not ready")
                await ensure_settled(page)
                inc("missions_dispatched", 1)
                maybe_write()
                display_info(
                    f"Mission {mission_id}: dispatched (base {base_selected}, +types {added}, widen x{widen_mult:.2f})."
                )

                # Record cooldowns and soft-cap timestamps for types we used
                await _record_cooldowns(picked_ids)
                # Mark for stuck-check & schedule a top-up
                stuck = _load_json(STUCK_PATH)
                stuck[mission_id] = {"dispatched_ts": int(time.time())}
                _save_json(STUCK_PATH, stuck)

                due = _load_json(TOPUP_PATH)
                due[mission_id] = {
                    "topup_due": int(time.time()) + random.randint(TOPUP_MIN_SEC, TOPUP_MAX_SEC)
                }
                _save_json(TOPUP_PATH, due)

                if defer_agent:
                    defer_agent.clear(mission_id)
                attempts.pop(mission_id, None)
            except Exception as e:
                attempts[mission_id] = ntry + 1
                display_error(
                    f"Mission {mission_id}: dispatch button not ready (attempt {attempts[mission_id]}/{ATTEMPT_BUDGET})."
                )
                sentinel.observe_error(str(e))
        except Exception as e:
            attempts[mission_id] = ntry + 1
            display_error(f"Dispatch error on {mission_id}: {e}")
            sentinel.observe_error(str(e))

        await ensure_settled(page)

    # Persist state & adaptive pacing
    _save_json(ATTEMPT_PATH, attempts)
    maybe_write()

    # Adaptive pacing within active windows (busy → short, quiet → longer)
    extra = 0.0
    cand_n = len(picked)
    if cand_n <= 3:
        extra = 6.0
    elif cand_n <= 8:
        extra = 3.0
    else:
        extra = 0.5
    extra += sentinel.recommend_extra_delay()
    await sleep_jitter(extra, extra + 1.0)
