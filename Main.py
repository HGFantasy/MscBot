# Project: MscBot
# Maintained by: HGFantasy
# License: MIT

import asyncio
from pathlib import Path

from dotenv import load_dotenv
from playwright.async_api import async_playwright

from setup.login import login_and_save_state, launch_with_state
from data.config_settings import (
    get_username,
    get_password,
    get_threads,
    get_headless,
    get_mission_delay,
    get_transport_delay,
    get_eta_filter,
    get_transport_prefs,
)
from utils.dispatcher import navigate_and_dispatch
from utils.mission_data import check_and_grab_missions
from utils.pretty_print import display_info, display_error
from utils.transport import handle_transport_requests
from utils.vehicle_data import gather_vehicle_data
from utils.building_data import gather_building_data
from utils.politeness import set_max_concurrency
from utils.runtime_flags import wait_if_paused, should_stop
from utils.metrics import maybe_write
from utils.browser import close_browsers
from agents import load_agents, emit
from agents.update_check import UpdateCheckAgent


def _validate_or_die() -> None:
    """Validate configuration values and exit on invalid entries."""
    filt = get_eta_filter()
    tp = get_transport_prefs()
    errs = []

    if filt["max_km"] <= 0 or filt["max_minutes"] <= 0:
        errs.append("dispatch_filter: max_km/minutes must be > 0")

    if tp["max_hospital_km"] <= 0 or tp["max_prison_km"] <= 0:
        errs.append("transport_prefs: max_*_km must be > 0")

    if tp["max_hospital_tax_pct"] < 0 or tp["max_prison_tax_pct"] < 0:
        errs.append("transport_prefs: tax pct must be >= 0")

    if errs:
        for e in errs:
            display_error(f"CONFIG ERROR: {e}")
        raise SystemExit(2)

    display_info("Config validation: OK.")


async def transport_logic(browser):
    """Process transport requests using the first browser."""

    display_info("Starting transportation logic.")
    while True:
        try:
            await emit("transport_tick", browser=browser)
            if should_stop():
                display_info("STOP requested: exiting transport loop.")
                break
            await wait_if_paused()
            await handle_transport_requests(browser)
            await emit("after_transport_tick", browser=browser)
            await asyncio.sleep(get_transport_delay())
            maybe_write()
        except Exception as e:
            display_error(f"Error in transport logic: {e}")


async def mission_logic(browsers_for_missions):
    """Handle mission dispatching using the remaining browsers."""

    display_info("Starting mission logic.")
    while True:
        try:
            await emit("mission_tick", browsers=browsers_for_missions)
            if should_stop():
                display_info("STOP requested: exiting mission loop.")
                break
            await wait_if_paused()
            vehicle_data = Path("data/vehicle_data.json")
            building_data = Path("data/building_data.json")
            if vehicle_data.exists() and building_data.exists():
                await check_and_grab_missions(
                    browsers_for_missions, len(browsers_for_missions)
                )
            else:
                try:
                    if not vehicle_data.exists():
                        await gather_vehicle_data([browsers_for_missions[0]], 1)
                    if not building_data.exists():
                        await gather_building_data([browsers_for_missions[0]], 1)
                except Exception as e:
                    display_error(f"Vehicle/building data gather failed: {e}")
            await navigate_and_dispatch(browsers_for_missions)
            await emit("after_mission_tick", browsers=browsers_for_missions)
            await asyncio.sleep(get_mission_delay())
            maybe_write()
        except Exception as e:
            display_error(f"Error in mission logic: {e}")


async def main():
    """Program entrypoint."""

    display_info("MscBot starting…")
    _validate_or_die()
    await emit("start")

    username, password = get_username(), get_password()
    headless, threads = get_headless(), max(2, int(get_threads()))
    display_info(
        f"Config → threads={threads}, headless={headless}, has_user={bool(username)}"
    )
    if not username or not password:
        display_error("Missing credentials. Set them in config.ini or via env vars.")
        return

    state_path = Path("auth") / "storage.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        if not state_path.exists():
            ok = await login_and_save_state(
                username, password, headless, p, state_path=state_path
            )
            if not ok:
                display_error("Login-once failed; cannot continue.")
                return

        try:
            set_max_concurrency(threads)
        except Exception:
            set_max_concurrency(2)

        display_info(f"Launching {threads} authenticated browsers…")
        launchers = [launch_with_state(headless, p, state_path) for _ in range(threads)]
        browsers = await asyncio.gather(*launchers)
        if len(browsers) < 2:
            display_error("Unexpected: <2 browsers after launch_with_state.")
            for b in browsers:
                try:
                    await b.close()
                except Exception:
                    pass
            return

        browser_for_transport, browsers_for_missions = browsers[0], browsers[1:]
        display_info("Launching mission/transport tasks…")
        mission_task = asyncio.create_task(mission_logic(browsers_for_missions))
        transport_task = asyncio.create_task(transport_logic(browser_for_transport))
        try:
            await asyncio.gather(mission_task, transport_task)
        finally:
            display_info("Shutting down browsers…")
            await close_browsers(browsers)
            await emit("shutdown")


async def bootstrap() -> None:
    """Run the update check before loading the bot."""

    await UpdateCheckAgent()._check_now(auto_update=True)
    load_dotenv()
    load_agents()
    await main()


if __name__ == "__main__":
    asyncio.run(bootstrap())
