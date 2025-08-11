# Project: MscBot
# License: MIT

import os
from playwright.async_api import TimeoutError as PWTimeoutError
from utils.pretty_print import display_info, display_error
from utils.politeness import goto_safe, fill_safe, click_safe, ensure_settled
from data.config_settings import get_slow_mo_ms

async def maybe_accept_cookies(page):
    for sel in [
        'button:has-text("Accept")','button:has-text("I agree")',
        '[id*="cookie"] button:has-text("Accept")','button[aria-label*="accept"]',
    ]:
        try:
            btn = await page.wait_for_selector(sel, timeout=1200)
            if btn: await btn.click(); await ensure_settled(page); return
        except Exception: pass

async def _perform_login(page, username, password):
    # Important: navigate directly (not via goto_safe) to avoid auto-repair
    # intercepting the explicit sign_in visit.
    await page.goto("https://www.missionchief.com/users/sign_in", wait_until="domcontentloaded")
    try:
        await page.wait_for_load_state("networkidle")
    except Exception:
        pass

    # If we already got logged-in by cookies/session restore, bail out early.
    if "users/sign_in" not in (page.url or ""):
        return

    # Otherwise proceed with the form.
    try:
        await page.wait_for_selector("form#new_user", timeout=12000)
    except Exception:
        # Some layouts inject the form a bit later; keep going if still on sign_in.
        if "users/sign_in" in (page.url or ""):
            pass
        else:
            return  # we navigated away, so consider it logged-in

    await maybe_accept_cookies(page)
    try:
        await fill_safe(page, 'input[name="user[email]"]', username)
        await fill_safe(page, 'input[name="user[password]"]', password)
        await click_safe(page, 'input[type="submit"]')
    except Exception:
        # Fallback submit
        try:
            await page.press('input[name="user[password]"]', "Enter")
        except Exception:
            pass
    await ensure_settled(page)
    if "users/sign_in" in (page.url or ""):
        try:
            if await page.locator('text=Invalid email or password').is_visible(timeout=1200):
                raise PWTimeoutError("Invalid email or password")
        except Exception: pass
        raise PWTimeoutError("Login did not navigate away from sign_in")

async def login_and_save_state(username, password, headless, playwright, state_path="auth/storage.json"):
    display_info("Login-once: creating fresh session and saving storage_state")
    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    slow_mo = get_slow_mo_ms()
    browser = await playwright.chromium.launch(headless=headless, devtools=False, slow_mo=slow_mo)
    try:
        context = await browser.new_context()
        page = await context.new_page()
        await _perform_login(page, username, password)
        # If still at sign_in here, treat as failure
        if "users/sign_in" in (page.url or ""):
            raise PWTimeoutError("Still on sign_in after login attempt")
        # Land home
        await goto_safe(page, "https://www.missionchief.com/")
        await context.storage_state(path=state_path)
        display_info(f"Saved storage_state to {state_path}")
        return True
    except Exception as e:
        display_error(f"Login-once failed: {e}"); return False
    finally:
        try: await browser.close()
        except Exception: pass

async def launch_with_state(headless, playwright, state_path="auth/storage.json"):
    slow_mo = get_slow_mo_ms()
    browser = await playwright.chromium.launch(headless=headless, devtools=False, slow_mo=slow_mo)
    context = await browser.new_context(storage_state=state_path if os.path.exists(state_path) else None)
    page = await context.new_page()
    await goto_safe(page, "https://www.missionchief.com/")
    await ensure_settled(page)
    return browser
