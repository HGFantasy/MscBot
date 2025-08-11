"""Transport handling with clearer flow and reusable helpers.

This refactor keeps existing behavior while improving readability:
- Structured as a `TransportManager` with small, testable methods
- Centralizes JSON I/O, blacklisting, and SLA/deferral logic
- Reduces duplicated modal-selection code (hospital vs prison)
"""

from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from data.config_settings import get_transport_prefs
from utils import sentinel
from utils.eta_filter import parse_capacity, parse_km, parse_pct
from utils.humanize import gentle_mouse
from utils.metrics import inc, maybe_write
from utils.politeness import ensure_settled, sleep_jitter
from utils.pretty_print import display_error, display_info


DEFER_PATH = Path("data/deferred_transports.json")
BLACKLIST_PATH = Path("data/destination_blacklist.json")
ATTEMPT_PATH = Path("data/transport_attempts.json")


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
    except Exception as e:  # pragma: no cover
        display_error(f"Could not save {p.name}: {e}")


def _row_label(text: str) -> str:
    return (text or "").strip().lower()[:60]


@dataclass
class _Rec:
    next_check: int
    defer_count: int
    first_seen: int

    @classmethod
    def from_dict(cls, d: dict[str, Any], now: int) -> "_Rec":
        return cls(
            next_check=int(d.get("next_check", 0)),
            defer_count=int(d.get("defer_count", 0)),
            first_seen=int(d.get("first_seen", 0)) or now,
        )


class TransportManager:
    def __init__(self, browser) -> None:
        self.browser = browser
        # Page will be ensured lazily in _prepare_home
        self.page = None  # type: ignore[assignment]
        self.prefs = get_transport_prefs()
        self.defer = _load_json(DEFER_PATH)
        self.attempts = _load_json(ATTEMPT_PATH)
        self.blacklist = _load_json(BLACKLIST_PATH)
        # time provider for SLA/defers; call self._now() when needed

    def _now(self) -> int:
        return int(time.time())

    async def run(self) -> None:
        if not await self._prepare_home():
            return
        vehicle_ids = await self._gather_requests()
        inc("transports_seen", len(vehicle_ids))

        for vid in vehicle_ids:
            try:
                await self._process_vehicle(vid)
                await sleep_jitter(0.2, 0.4)
            except Exception as e:  # pragma: no cover - defensive
                display_error(f"Transport error: {e}")
                sentinel.observe_error(str(e))

        # Persist state
        _save_json(DEFER_PATH, self.defer)
        _save_json(BLACKLIST_PATH, self.blacklist)
        _save_json(ATTEMPT_PATH, self.attempts)
        maybe_write()

        # Adaptive pacing: fewer requests → longer rest; include sentinel hint
        extra = 6.0 if len(vehicle_ids) == 0 else 3.0 if len(vehicle_ids) <= 3 else 0.5
        extra += sentinel.recommend_extra_delay()
        await sleep_jitter(extra, extra + 1.0)

    async def _prepare_home(self) -> bool:
        try:
            # Ensure we have a page
            if not self.browser.contexts:
                ctx = await self.browser.new_context()
            else:
                ctx = self.browser.contexts[0]
            if not ctx.pages:
                self.page = await ctx.new_page()
            else:
                self.page = ctx.pages[0]

            await self.page.goto("https://www.missionchief.com")
            await ensure_settled(self.page)
            await gentle_mouse(self.page)
            # Session drift monitor
            try:
                if "sign_in" in (self.page.url or "") or "login" in (self.page.url or ""):
                    inc("reauths", 1)
                    maybe_write()
                    display_info("[auth] session reauth detected during transport.")
            except Exception:
                pass
            return True
        except Exception as e:
            display_error(f"Transport navigation failed: {e}")
            sentinel.observe_error(str(e))
            return False

    async def _gather_requests(self) -> list[str]:
        reqs = await self.page.query_selector_all("ul#radio_messages_important li")
        total = len(reqs)
        cap = random.randint(122, 189)  # UI throughput cap
        reqs = reqs[:cap]
        display_info(f"Found {total} transport requests; processing up to {len(reqs)} this cycle.")
        vids: list[str] = []
        for r in reqs:
            try:
                img = await r.query_selector("img")
                vid = await img.get_attribute("vehicle_id") if img else None
                if vid:
                    vids.append(vid)
            except Exception:
                continue
        return vids

    async def _open_vehicle(self, vid: str) -> bool:
        try:
            await self.page.goto(f"https://www.missionchief.com/vehicles/{vid}")
            await ensure_settled(self.page)
            await gentle_mouse(self.page)
            try:
                if "sign_in" in (self.page.url or "") or "login" in (self.page.url or ""):
                    inc("reauths", 1)
                    maybe_write()
                    display_info("[auth] session reauth detected at vehicle page.")
            except Exception:
                pass
            return True
        except Exception as e:
            display_error(f"Vehicle open failed for {vid}: {e}")
            sentinel.observe_error(str(e))
            return False

    async def _process_vehicle(self, vid: str) -> None:
        rec = _Rec.from_dict(self.defer.get(vid, {}), self._now())
        if rec.next_check > self._now():
            return
        attempt_budget = int(self.prefs.get("attempt_budget", 2))
        ntry = int(self.attempts.get(vid, 0))
        if ntry >= attempt_budget:
            return
        self.attempts[vid] = ntry + 1
        self.defer.setdefault(vid, {})  # keep slot available for updates
        self.defer[vid]["first_seen"] = rec.first_seen

        if not await self._open_vehicle(vid):
            return

        # Attempt hospital and prison flows if present on page
        acted = await self._try_mode(vid, "hospital", rec) or await self._try_mode(
            vid, "prison", rec
        )

        if not acted:
            # Try to release if available (keeps previous behavior)
            release = self.page.locator("a.btn.btn-xs.btn-danger").first
            try:
                await release.wait_for(state="visible", timeout=2000)
                await release.click()
                await ensure_settled(self.page)
                display_info(f"Released at vehicle {vid}")
            except Exception:
                pass

    async def _try_mode(self, vid: str, mode: str, rec: _Rec) -> bool:
        # Locate action button(s) by text for the given mode
        btns = self.page.locator("a.btn-success, button.btn-success")
        count = await btns.count()
        for i in range(count):
            b = btns.nth(i)
            try:
                txt = (await b.inner_text() or "").lower()
            except Exception:
                continue
            if mode == "hospital" and ("hospital" in txt or "transport" in txt):
                return await self._handle_destination_click(vid, b, mode, rec)
            if mode == "prison" and ("prison" in txt or "jail" in txt):
                return await self._handle_destination_click(vid, b, mode, rec)
        return False

    async def _handle_destination_click(self, vid, button, mode: str, rec: _Rec) -> bool:
        await button.click()
        await ensure_settled(self.page)

        # SLA override if waited long enough
        sla_min = (
            int(self.prefs.get("sla_hospital_min", 15))
            if mode == "hospital"
            else int(self.prefs.get("sla_prison_min", 20))
        )
        sla_due = (self._now() - int(rec.first_seen)) >= (sla_min * 60)

        ok = await self._choose_destination_from_modal(mode, escalate_override=sla_due)
        if ok:
            inc("transports_completed", 1)
            self.defer.pop(vid, None)
            return True

        # Fallback with deferral and potential escalate-after-N-defers
        fb_key = f"{mode}_fallback"
        recheck_key = f"{mode}_recheck_min"
        if self.prefs.get(fb_key, "wait") == "wait":
            new_count = int(self.defer.get(vid, {}).get("defer_count", 0)) + 1
            # try once with escalation after enough defers
            escalate_after = int(self.prefs.get("escalate_after_defers", 3))
            if new_count >= escalate_after:
                ok2 = await self._choose_destination_from_modal(mode, escalate_override=True)
                if ok2:
                    inc("transports_completed", 1)
                    self.defer.pop(vid, None)
                    display_info(
                        f"Vehicle {vid}: ESCALATE → sent beyond caps after {new_count} defers."
                    )
                    return True

            minutes = max(1, int(self.prefs.get(recheck_key, 10)))
            self.defer[vid] = {
                "next_check": self._now() + minutes * 60,
                "reason": f"{mode} limits",
                "updated": self._now(),
                "defer_count": new_count,
                "first_seen": int(rec.first_seen),
            }
            inc("transports_deferred", 1)
            display_info(
                f"Vehicle {vid}: deferring {mode} transport {minutes} min. (n={new_count})"
            )
            return True  # we acted (deferred)
        else:
            return True  # non-wait fallback: we consider it handled

    async def _choose_destination_from_modal(
        self, mode: str, *, escalate_override: bool
    ) -> bool | None:
        rows = self.page.locator("div.modal, .modal, .dialog, .ui-dialog, .popover, body").locator(
            "li, tr, div"
        )
        n = min(await rows.count(), 300)
        candidates: list[dict[str, Any]] = []
        now = self._now()
        ttl = int(self.prefs.get("blacklist_ttl_min", 45)) * 60
        min_free = int(
            self.prefs.get("min_free_beds" if mode == "hospital" else "min_free_cells", 1)
        )

        for i in range(n):
            r = rows.nth(i)
            try:
                t = (await r.inner_text()).strip()
                if not t:
                    continue
                lab = _row_label(t)
                if lab in self.blacklist and self.blacklist[lab] > now:
                    continue
                d = parse_km(t)
                p = parse_pct(t)
                free, _ = parse_capacity(t)
                # Guard against parse failures by assigning large values
                km_val = d if d is not None else 1e9
                pct_val = p if p is not None else 1e9
                candidates.append(
                    {"i": i, "text": t, "label": lab, "km": km_val, "pct": pct_val, "free": free}
                )
            except Exception:
                continue
        if not candidates:
            return None

        if mode == "hospital":
            max_km = float(self.prefs["max_hospital_km"])
            max_pct = float(self.prefs["max_hospital_tax_pct"])
        else:
            max_km = float(self.prefs["max_prison_km"])
            max_pct = float(self.prefs["max_prison_tax_pct"])

        def fits(c: dict[str, Any], km_mult: float = 1.0) -> bool:
            return (
                (c["km"] <= max_km * km_mult)
                and (c["pct"] <= max_pct)
                and (c["free"] is None or c["free"] >= min_free)
            )

        # Escalation override: ignore distance/tax caps; still require capacity if available
        if escalate_override:
            best = [
                c for c in candidates if (c["free"] is None or c["free"] >= min_free)
            ] or candidates[:]
            best.sort(key=lambda c: (c["pct"], c["km"]))
            chosen = best[0]
            ctl = rows.nth(chosen["i"]).locator("a, button, input[type=submit]").first
            try:
                await ctl.click()
                await ensure_settled(self.page)
                display_info(f"ESCALATE override → picked {chosen['km']:.1f}km, {chosen['pct']}%")
                return True
            except Exception:
                return None

        # Strict fit first
        strict = [c for c in candidates if fits(c, 1.0)]
        if strict:
            strict.sort(key=lambda c: (c["pct"], c["km"]))
            chosen = strict[0]
            ctl = rows.nth(chosen["i"]).locator("a, button, input[type=submit]").first
            try:
                await ctl.click()
                await ensure_settled(self.page)
                return True
            except Exception:
                return None

        # Ladder widening (km only)
        for mult in (1.25, 1.5, 2.0):
            widened = [
                c
                for c in candidates
                if (c["km"] <= max_km * mult) and (c["free"] is None or c["free"] >= min_free)
            ]
            if widened:
                widened.sort(key=lambda c: (c["pct"], c["km"]))
                chosen = widened[0]
                ctl = rows.nth(chosen["i"]).locator("a, button, input[type=submit]").first
                try:
                    await ctl.click()
                    await ensure_settled(self.page)
                    display_info(
                        f"Ladder: widened x{mult:.2f} → picked {chosen['km']:.1f}km, {chosen['pct']}%"
                    )
                    return True
                except Exception:
                    return None

        # Nothing matched — blacklist top few so next pass tries different
        for c in candidates[:5]:
            self.blacklist[c["label"]] = now + ttl
        return None


async def handle_transport_requests(browser):
    """Process pending hospital or prison transport requests (refactored)."""
    await TransportManager(browser).run()
