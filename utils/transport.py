# Project: MissionchiefBot-X — Transports (escalation + SLA + adaptive pacing + sentinel + reauth)
# License: MIT

from __future__ import annotations
import json, random, time
from pathlib import Path
from utils.politeness import sleep_jitter, ensure_settled
from utils.humanize import gentle_mouse
from utils.pretty_print import display_info, display_error
from utils.eta_filter import parse_km, parse_pct, parse_capacity
from data.config_settings import get_transport_prefs
from utils.metrics import inc, maybe_write
from utils import sentinel

DEFER_PATH = Path("data/deferred_transports.json")
BLACKLIST_PATH = Path("data/destination_blacklist.json")
ATTEMPT_PATH = Path("data/transport_attempts.json")
ATTEMPT_BUDGET = 2  # per vehicle per run

# Escalation: after this many deferrals for the same vehicle, try once ignoring caps
ESCALATE_AFTER_DEFERS = 3

# Option #19: wait-time SLA (minutes) — escalate to send once patient/prisoner has waited this long
SLA_HOSPITAL_MIN = 15
SLA_PRISON_MIN   = 20

def _load_json(p: Path):
    try:
        if p.exists():
            with p.open("r", encoding="utf-8") as f: return json.load(f)
    except Exception: pass
    return {}

def _save_json(p: Path, d: dict):
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f: json.dump(d, f, indent=2)
    except Exception as e:
        display_error(f"Could not save {p.name}: {e}")

def _row_label(text: str) -> str:
    return (text or "").strip().lower()[:60]

async def _choose_destination_from_modal(page, prefs, mode: str, blacklist: dict, escalate_override: bool=False):
    rows = page.locator("div.modal, .modal, .dialog, .ui-dialog, .popover, body").locator("li, tr, div")
    n = min(await rows.count(), 300)
    candidates = []
    now = int(time.time()); ttl = int(prefs.get("blacklist_ttl_min",45))*60
    min_free = int(prefs.get("min_free_beds" if mode=="hospital" else "min_free_cells", 1))

    for i in range(n):
        r = rows.nth(i)
        try:
            t = (await r.inner_text()).strip()
            if not t: continue
            lab = _row_label(t)
            if lab in blacklist and blacklist[lab] > now:
                continue
            d = parse_km(t); p = parse_pct(t)
            free,_ = parse_capacity(t)
            candidates.append({"i":i,"text":t,"label":lab,"km":d,"pct":p,"free":free})
        except Exception:
            continue
    if not candidates:
        return None

    if mode=="hospital":
        max_km = float(prefs["max_hospital_km"]); max_pct = float(prefs["max_hospital_tax_pct"])
    else:
        max_km = float(prefs["max_prison_km"]);   max_pct = float(prefs["max_prison_tax_pct"])

    def fits(c, km_mult=1.0):
        return (c["km"] <= max_km*km_mult) and (c["pct"] <= max_pct) and (c["free"] is None or c["free"] >= min_free)

    # Escalation override: ignore caps, still prefer capacity + low tax + nearer
    if escalate_override:
        best = [c for c in candidates if (c["free"] is None or c["free"] >= min_free)]
        if not best: best = candidates[:]
        best.sort(key=lambda c: (c["pct"], c["km"]))
        chosen = best[0]
        ctl = rows.nth(chosen["i"]).locator("a, button, input[type=submit]").first
        try:
            await ctl.click(); await ensure_settled(page)
            display_info(f"ESCALATE override → picked {chosen['km']:.1f}km, {chosen['pct']}%")
            return True
        except Exception:
            return None

    # Normal strict fit first
    strict = [c for c in candidates if fits(c, 1.0)]
    if strict:
        strict.sort(key=lambda c: (c["pct"], c["km"]))
        chosen = strict[0]
        ctl = rows.nth(chosen["i"]).locator("a, button, input[type=submit]").first
        try:
            await ctl.click(); await ensure_settled(page)
            return True
        except Exception:
            return None

    # Ladder widening (km only)
    for mult in (1.25, 1.5, 2.0):
        widened = [c for c in candidates if (c["km"] <= max_km*mult) and (c["free"] is None or c["free"] >= min_free)]
        if widened:
            widened.sort(key=lambda c: (c["pct"], c["km"]))
            chosen = widened[0]
            ctl = rows.nth(chosen["i"]).locator("a, button, input[type=submit]").first
            try:
                await ctl.click(); await ensure_settled(page)
                display_info(f"Ladder: widened x{mult:.2f} → picked {chosen['km']:.1f}km, {chosen['pct']}%")
                return True
            except Exception:
                return None

    # Nothing matched — blacklist top few so next pass tries different
    for c in candidates[:5]:
        blacklist[c["label"]] = now + ttl
    return None

async def handle_transport_requests(browser):
    prefs = get_transport_prefs()
    page = browser.contexts[0].pages[0]
    try:
        await page.goto("https://www.missionchief.com")
        await ensure_settled(page)
        await gentle_mouse(page)
        # Session drift monitor
        try:
            if "sign_in" in (page.url or "") or "login" in (page.url or ""):
                inc("reauths", 1); maybe_write()
                display_info("[auth] session reauth detected during transport.")
        except Exception:
            pass
    except Exception as e:
        display_error(f"Transport navigation failed: {e}")
        sentinel.observe_error(str(e))
        return

    requests = await page.query_selector_all('ul#radio_messages_important li')
    total = len(requests)
    cap = random.randint(122, 189)  # per docs
    requests = requests[:cap]
    display_info(f"Found {total} transport requests; processing up to {len(requests)} this cycle.")
    inc("transports_seen", len(requests))

    defer = _load_json(DEFER_PATH)
    attempts = _load_json(ATTEMPT_PATH)
    blacklist = _load_json(BLACKLIST_PATH)
    now = int(time.time())

    for req in requests:
        try:
            img = await req.query_selector('img')
            vehicle_id = await img.get_attribute('vehicle_id') if img else None
            if not vehicle_id:
                continue

            rec = defer.get(vehicle_id, {"next_check":0, "defer_count":0, "first_seen": now})
            # Track first_seen for SLA
            if int(rec.get("first_seen", 0)) == 0:
                rec["first_seen"] = now

            if int(rec.get("next_check", 0)) > now:
                continue

            ntry = int(attempts.get(vehicle_id, 0))
            if ntry >= ATTEMPT_BUDGET:
                continue

            try:
                await page.goto(f"https://www.missionchief.com/vehicles/{vehicle_id}")
                await ensure_settled(page); await gentle_mouse(page)
                # Reauth check
                try:
                    if "sign_in" in (page.url or "") or "login" in (page.url or ""):
                        inc("reauths", 1); maybe_write()
                        display_info("[auth] session reauth detected at vehicle page.")
                except Exception:
                    pass
            except Exception as e:
                display_error(f"Vehicle open failed for {vehicle_id}: {e}")
                sentinel.observe_error(str(e))
                continue

            buttons = page.locator('a.btn-success, button.btn-success')
            clicked = False
            count = await buttons.count()
            for i in range(count):
                b = buttons.nth(i)
                try:
                    txt = (await b.inner_text() or "").lower()
                    if "hospital" in txt or "transport" in txt:
                        await b.click(); await ensure_settled(page)
                        # SLA override?
                        sla_due = (now - int(rec["first_seen"])) >= (SLA_HOSPITAL_MIN*60)
                        ok = await _choose_destination_from_modal(page, prefs, mode="hospital", blacklist=blacklist, escalate_override=sla_due)
                        if ok:
                            inc("transports_completed", 1); clicked=True
                            defer.pop(vehicle_id, None)
                            break

                        # fallback logic with escalation-after-N-defers
                        if prefs.get("hospital_fallback","wait") == "wait":
                            new_count = int(rec.get("defer_count",0)) + 1
                            if new_count >= ESCALATE_AFTER_DEFERS:
                                ok2 = await _choose_destination_from_modal(page, prefs, mode="hospital", blacklist=blacklist, escalate_override=True)
                                if ok2:
                                    inc("transports_completed", 1); clicked=True
                                    display_info(f"Vehicle {vehicle_id}: ESCALATE → sent beyond caps after {new_count} defers.")
                                    defer.pop(vehicle_id, None)
                                    break
                            minutes = max(1, int(prefs.get("hospital_recheck_min", 10)))
                            defer[vehicle_id] = {"next_check": now + minutes*60, "reason":"hospital limits", "updated": now,
                                                 "defer_count": new_count, "first_seen": int(rec["first_seen"])}
                            inc("transports_deferred", 1)
                            display_info(f"Vehicle {vehicle_id}: deferring hospital transport {minutes} min. (n={new_count})")
                            clicked=True; break
                        else:
                            clicked=True; break

                    if "prison" in txt or "jail" in txt:
                        await b.click(); await ensure_settled(page)
                        sla_due = (now - int(rec["first_seen"])) >= (SLA_PRISON_MIN*60)
                        ok = await _choose_destination_from_modal(page, prefs, mode="prison", blacklist=blacklist, escalate_override=sla_due)
                        if ok:
                            inc("transports_completed", 1); clicked=True
                            defer.pop(vehicle_id, None)
                            break

                        if prefs.get("prison_fallback","wait") == "wait":
                            new_count = int(rec.get("defer_count",0)) + 1
                            if new_count >= ESCALATE_AFTER_DEFERS:
                                ok2 = await _choose_destination_from_modal(page, prefs, mode="prison", blacklist=blacklist, escalate_override=True)
                                if ok2:
                                    inc("transports_completed", 1); clicked=True
                                    display_info(f"Vehicle {vehicle_id}: ESCALATE → sent beyond caps after {new_count} defers.")
                                    defer.pop(vehicle_id, None)
                                    break
                            minutes = max(1, int(prefs.get("prison_recheck_min", 10)))
                            defer[vehicle_id] = {"next_check": now + minutes*60, "reason":"prison limits", "updated": now,
                                                 "defer_count": new_count, "first_seen": int(rec["first_seen"])}
                            inc("transports_deferred", 1)
                            display_info(f"Vehicle {vehicle_id}: deferring prison transport {minutes} min. (n={new_count})")
                            clicked=True; break
                        else:
                            clicked=True; break
                except Exception:
                    pass

            if not clicked:
                release = page.locator('a.btn.btn-xs.btn-danger').first
                try:
                    await release.wait_for(state="visible", timeout=2000)
                    await release.click(); await ensure_settled(page)
                    display_info(f"Released at vehicle {vehicle_id}")
                except Exception:
                    pass

            await sleep_jitter(0.2, 0.4)
        except Exception as e:
            display_error(f"Transport error: {e}")
            sentinel.observe_error(str(e))

    _save_json(DEFER_PATH, defer)
    _save_json(BLACKLIST_PATH, blacklist)
    _save_json(ATTEMPT_PATH, attempts)
    maybe_write()

    # Adaptive pacing: fewer requests → longer rest; consider sentinel hint
    extra = 0.0
    if   len(requests) == 0: extra = 6.0
    elif len(requests) <= 3: extra = 3.0
    else:                    extra = 0.5
    extra += sentinel.recommend_extra_delay()
    await sleep_jitter(extra, extra + 1.0)
