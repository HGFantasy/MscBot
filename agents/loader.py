"""Dynamic agent loader for MscBot."""

from __future__ import annotations

import asyncio
import importlib
import inspect
import pkgutil
from collections.abc import Awaitable
from pathlib import Path
from typing import Any

from data.config_settings import (
    get_agent_handler_timeout_ms,
    get_disabled_agents,
    get_enabled_agents,
)
from utils.pretty_print import display_error, display_info

from .base import BaseAgent

_AGENTS: dict[str, BaseAgent] = {}
_ACTIVE: set[str] = set()
_HANDLERS_CACHE: dict[str, list[tuple[str, str, bool]]] = {}


def load_agents() -> None:
    """Discover and instantiate all agents in the agents package."""
    _AGENTS.clear()
    _ACTIVE.clear()
    _HANDLERS_CACHE.clear()
    pkg_path = Path(__file__).resolve().parent
    allow = {a.lower() for a in get_enabled_agents()}
    deny = {a.lower() for a in get_disabled_agents()}
    for mod in sorted(pkgutil.iter_modules([str(pkg_path)]), key=lambda m: m.name):
        name = mod.name
        if name in {"base", "loader", "__init__"} or name.startswith("_"):
            continue
        if allow and name not in allow:
            continue
        if name in deny:
            continue
        try:
            module = importlib.import_module(f"agents.{name}")
        except Exception as e:
            display_error(f"Failed to import agent module {name}: {e}")
            continue
        for obj in module.__dict__.values():
            if inspect.isclass(obj) and issubclass(obj, BaseAgent) and obj is not BaseAgent:
                try:
                    inst = obj()
                    enabled = getattr(inst, "enabled", lambda: True)
                    if enabled():
                        _AGENTS[name] = inst
                        _ACTIVE.add(name)
                except Exception as e:
                    display_error(f"Failed to init agent {obj.__name__}: {e}")
    msg = (
        "Loaded agents: " + ", ".join(_AGENTS[n].__class__.__name__ for n in _ACTIVE)
        if _ACTIVE
        else "Loaded agents: none"
    )
    display_info(msg)


def _clear_cache() -> None:
    _HANDLERS_CACHE.clear()


def _get_handlers(event: str) -> list[tuple[str, str, bool]]:
    handlers = _HANDLERS_CACHE.get(event)
    if handlers is not None:
        return handlers
    handlers = []
    for name in list(_ACTIVE):
        agent = _AGENTS.get(name)
        if not agent:
            continue
        # Specific event handler
        attr = f"on_{event}"
        if hasattr(agent, attr):
            handlers.append((name, attr, False))
        # Generic fallback
        if hasattr(agent, "on_event"):
            handlers.append((name, "on_event", True))
    _HANDLERS_CACHE[event] = handlers
    return handlers


def iter_active_agents() -> list[BaseAgent]:
    """Return a list of currently enabled agent instances."""
    return [_AGENTS[n] for n in _ACTIVE]


def get_agent(name: str) -> BaseAgent | None:
    """Retrieve a specific agent instance by module name."""
    return _AGENTS.get(name.lower())


async def emit(event: str, *, collect: bool = False, **kwargs: Any) -> dict[str, Any]:
    """Broadcast ``event`` to all active agents.

    For an ``event`` named ``foo`` this will invoke an ``on_foo`` method on
    each agent if present. Agents may also implement a generic ``on_event``
    handler which receives the event name via a keyword argument.

    If ``collect`` is ``True`` the return values of handlers are gathered and
    returned in a dictionary keyed by agent name. Handlers may be regular
    functions or coroutines. Exceptions are reported but omitted from the
    results.
    """

    timeout = max(0, int(get_agent_handler_timeout_ms())) / 1000.0
    tasks: list[tuple[str, str, Awaitable[Any]]] = []
    results: dict[str, Any] = {} if collect else {}
    for name, attr, pass_name in _get_handlers(event):
        agent = _AGENTS.get(name)
        if not agent:
            continue
        handler = getattr(agent, attr, None)
        if not handler:
            continue
        try:
            if pass_name:
                coro_or_val = handler(event=event, **kwargs)
            else:
                coro_or_val = handler(**kwargs)
            if inspect.isawaitable(coro_or_val):
                async def _timed(coro: Awaitable[Any]) -> Any:
                    try:
                        return await asyncio.wait_for(coro, timeout=timeout) if timeout else await coro
                    except Exception as e:
                        raise e
                tasks.append((name, attr, _timed(coro_or_val)))
            elif collect:
                results[name] = coro_or_val
        except Exception as e:  # pragma: no cover - defensive
            display_error(f"Agent {name}.{attr} failed: {e}")
    if tasks:
        gathered = await asyncio.gather(*(t for _, _, t in tasks), return_exceptions=True)
        for (name, attr, _), res in zip(tasks, gathered, strict=False):
            if isinstance(res, Exception):
                display_error(f"Agent {name}.{attr} failed: {res}")
            elif collect:
                results[name] = res
    return results


def enable_agent(name: str) -> bool:
    """Enable an agent by module name. Returns True if successful."""
    key = name.lower()
    if key in _AGENTS:
        _ACTIVE.add(key)
        _clear_cache()
        display_info(f"Agent enabled: {key}")
        return True
    display_error(f"Enable failed: unknown agent '{name}'")
    return False


def disable_agent(name: str) -> bool:
    """Disable an agent by module name. Returns True if successful."""
    key = name.lower()
    if key in _ACTIVE:
        _ACTIVE.remove(key)
        _clear_cache()
        display_info(f"Agent disabled: {key}")
        return True
    display_error(f"Disable failed: unknown or inactive agent '{name}'")
    return False
