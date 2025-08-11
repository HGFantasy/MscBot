# Project: MscBot — Auto re-auth (cycle-free)
# License: MIT

import os, time
from utils.pretty_print import display_info, display_error
from data.config_settings import get_username, get_password

async def _trace_once(context, name: str):
    try:
        os.makedirs("logs", exist_ok=True)
        await context.tracing.start(screenshots=True, snapshots=True, sources=False)
        await context.tracing.stop(path=f"logs/trace-{name}-{int(time.time())}.zip")
    except Exception:
        pass

async def _maybe_accept_cookies(page):
    for sel in [
        'button:has-text("Accept")','button:has-text("I agree")',
        '[id*="cookie"] button:has-text("Accept")','button[aria-label*="accept"]',
    ]:
        try:
            btn = await page.wait_for_selector(sel, timeout=1200)
            if btn:
                await btn.click()
                await page.wait_for_load_state("networkidle")
                break
        except Exception:
            pass

async def _perform_inline_login(page, username, password):
    # No imports from setup.login or utils.politeness to avoid circular deps.
    await page.goto("https://www.missionchief.com/users/sign_in", wait_until="domcontentloaded")
    try:
        await page.wait_for_selector("form#new_user", timeout=12000)
    except Exception:
        pass
    await _maybe_accept_cookies(page)
    try:
        await page.fill('input[name="user[email]"]', username)
        await page.fill('input[name="user[password]"]', password)
        submit = page.locator('input[type="submit"], button[type="submit"], input[name="commit"]').first
        if await submit.count() > 0:
            await submit.click()
        else:
            await page.press('input[name="user[password]"]', "Enter")
    except Exception as e:
        display_error(f"Inline login form interaction failed: {e}")
    try:
        await page.wait_for_load_state("networkidle")
    except Exception:
        pass
    return "users/sign_in" not in (page.url or "")

async def ensure_authenticated(page) -> bool:
    """If on sign_in, try to re-login inline and refresh storage_state. Returns True if fixed."""
    try:
        if "users/sign_in" not in (page.url or ""):
            return False
        display_info("Detected auth loss — attempting inline re-login…")
        ctx = page.context
        await _trace_once(ctx, "pre-relogin")
        ok = await _perform_inline_login(page, get_username(), get_password())
        if not ok:
            display_error("Inline re-login did not navigate away from sign_in.")
            await _trace_once(ctx, "relogin-failed")
            return False
        try:
            await ctx.storage_state(path="auth/storage.json")
        except Exception:
            pass
        display_info("Session repaired and storage_state refreshed.")
        return True
    except Exception as e:
        display_error(f"Auto re-auth failed: {e}")
        try:
            await _trace_once(page.context, "relogin-failed")
        except Exception:
            pass
        return False
