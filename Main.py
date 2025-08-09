
# Project: MscBot
# Maintained by: HGFantasy
# License: MIT

import asyncio, os, json, urllib.request
from playwright.async_api import async_playwright

from setup.login import login_and_save_state, launch_with_state
from data.config_settings import (
    get_username, get_password, get_threads, get_headless,
    get_mission_delay, get_transport_delay, get_human,
    get_eta_filter, get_transport_prefs, get_update_repo
)
from utils.dispatcher import navigate_and_dispatch
from utils.mission_data import check_and_grab_missions
from utils.pretty_print import display_info, display_error
from utils.transport import handle_transport_requests
from utils.vehicle_data import gather_vehicle_data
from utils.politeness import set_max_concurrency, sleep_jitter
from utils.humanize import Humanizer
from utils.runtime_flags import wait_if_paused, should_stop
from utils.schedule_windows import wait_if_outside
from utils.metrics import maybe_write

human = Humanizer(**get_human())

def _validate_or_die():
    from data.config_settings import get_eta_filter, get_transport_prefs
    filt = get_eta_filter(); tp = get_transport_prefs()
    errs = []
    if filt["max_km"] <= 0 or filt["max_minutes"] <= 0: errs.append("dispatch_filter: max_km/minutes must be > 0")
    if tp["max_hospital_km"] <= 0 or tp["max_prison_km"] <= 0: errs.append("transport_prefs: max_*_km must be > 0")
    if tp["max_hospital_tax_pct"] < 0 or tp["max_prison_tax_pct"] < 0: errs.append("transport_prefs: tax pct must be >= 0")
    if errs:
        for e in errs: display_error("CONFIG ERROR: " + e)
        raise SystemExit(2)
    display_info("Config validation: OK.")

def _read_version():
    try:
        with open("VERSION","r",encoding="utf-8") as f: return f.read().strip()
    except Exception: return "v0.0"

def _check_update():
    try:
        repo = get_update_repo()
        req = urllib.request.Request(
            f"https://api.github.com/repos/{repo}/releases/latest",
            headers={"User-Agent": "MscBot"},
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read().decode("utf-8"))
            latest = (data.get("tag_name") or "").strip()
            local = _read_version()
            if latest and latest != local:
                display_info(f"Update available: {local} → {latest} (repo {repo})")
    except Exception:
        pass

async def transport_logic(browser):
    display_info("Starting transportation logic.")
    while True:
        try:
            if should_stop(): display_info("STOP requested: exiting transport loop."); break
            await wait_if_paused(); await wait_if_outside(); await human.maybe_break()
            await handle_transport_requests(browser)
            await human.idle_after_action(); await sleep_jitter(0.6, 0.8)
            await asyncio.sleep(get_transport_delay()); maybe_write()
        except Exception as e:
            display_error(f"Error in transport logic: {e}")

async def mission_logic(browsers_for_missions):
    display_info("Starting mission logic.")
    while True:
        try:
            if should_stop(): display_info("STOP requested: exiting mission loop."); break
            await wait_if_paused(); await wait_if_outside(); await human.maybe_break()
            if os.path.exists("data/vehicle_data.json"):
                await check_and_grab_missions(browsers_for_missions, len(browsers_for_missions))
            else:
                try: await gather_vehicle_data([browsers_for_missions[0]], 1)
                except Exception as e: display_error(f"Vehicle data gather failed: {e}")
            await navigate_and_dispatch(browsers_for_missions)
            await human.idle_after_action(); await sleep_jitter(0.6, 0.8)
            await asyncio.sleep(get_mission_delay()); maybe_write()
        except Exception as e:
            display_error(f"Error in mission logic: {e}")

async def main():
    display_info("MscBot starting…")
    _validate_or_die()
    _check_update()

    username, password = get_username(), get_password()
    headless, threads = get_headless(), max(2, int(get_threads()))
    display_info(f"Config → threads={threads}, headless={headless}, has_user={bool(username)}")
    if not username or not password:
        display_error("Missing credentials. Set them in config.ini or via env vars."); return

    state_path = "auth/storage.json"; os.makedirs("auth", exist_ok=True)

    async with async_playwright() as p:
        if not os.path.exists(state_path):
            ok = await login_and_save_state(username, password, headless, p, state_path=state_path)
            if not ok: display_error("Login-once failed; cannot continue."); return

        try: set_max_concurrency(threads)
        except Exception: set_max_concurrency(2)

        display_info(f"Launching {threads} authenticated browsers…")
        browsers = [await launch_with_state(headless, p, state_path) for _ in range(threads)]
        if len(browsers) < 2:
            display_error("Unexpected: <2 browsers after launch_with_state.")
            for b in browsers:
                try: await b.close()
                except Exception: pass
            return

        browser_for_transport, browsers_for_missions = browsers[0], browsers[1:]
        display_info("Launching mission/transport tasks…")
        mission_task = asyncio.create_task(mission_logic(browsers_for_missions))
        transport_task = asyncio.create_task(transport_logic(browser_for_transport))
        try:
            await asyncio.gather(mission_task, transport_task)
        finally:
            display_info("Shutting down browsers…")
            for i, b in enumerate(browsers, 1):
                try: display_info(f"Closing browser {i}"); await b.close()
                except Exception: pass

if __name__ == "__main__":
    asyncio.run(main())
