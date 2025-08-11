# Project: MscBot
# License: MIT

"""Login helpers that previously depended on Playwright.

This module now uses ``requests`` sessions and simple cookie persistence to
avoid the greenlet dependency pulled in by Playwright.  The functions keep the
same async signatures as before so the rest of the codebase can interact with
them without modification.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

import requests

from utils.pretty_print import display_error, display_info


async def login_and_save_state(
    username: str,
    password: str,
    headless: bool,  # kept for compatibility
    playwright: Any | None = None,
    state_path: str = "auth/storage.json",
) -> bool:
    """Login using ``requests`` and persist cookies to ``state_path``.

    The ``headless`` and ``playwright`` arguments are accepted for API
    compatibility but are otherwise unused.
    """

    display_info("Login-once: creating session and saving cookie state")
    os.makedirs(os.path.dirname(state_path), exist_ok=True)

    session = requests.Session()
    try:
        resp = await asyncio.to_thread(
            session.post,
            "https://www.missionchief.com/users/sign_in",
            data={"user[email]": username, "user[password]": password},
            allow_redirects=True,
        )
        if "users/sign_in" in resp.url:
            raise RuntimeError("Login did not navigate away from sign_in")
        await asyncio.to_thread(
            lambda: open(state_path, "w", encoding="utf-8").write(
                json.dumps(session.cookies.get_dict())
            )
        )
        display_info(f"Saved cookies to {state_path}")
        return True
    except Exception as e:  # noqa: BLE001 - bubble up original error
        display_error(f"Login-once failed: {e}")
        return False
    finally:
        await asyncio.to_thread(session.close)


async def launch_with_state(
    headless: bool,  # kept for compatibility
    playwright: Any | None = None,
    state_path: str = "auth/storage.json",
):
    """Create a ``requests`` session and load cookies from ``state_path``."""

    session = requests.Session()
    if os.path.exists(state_path):
        try:
            with open(state_path, encoding="utf-8") as f:
                cookies = json.load(f)
            for k, v in cookies.items():
                session.cookies.set(k, v)
        except Exception:
            display_error(f"Failed loading cookies from {state_path}")
    return session
