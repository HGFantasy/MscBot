"""Dynamic agent loader for MscBot."""

from __future__ import annotations

import asyncio
import importlib
import inspect
import pkgutil
from collections.abc import Awaitable
from pathlib import Path
from typing import Any, Dict, List

from data.config_settings import get_enabled_agents, get_disabled_agents
from utils.pretty_print import display_error, display_info

from .base import BaseAgent


_AGENTS: Dict[str, BaseAgent] = {}
_ACTIVE: set[str] = set()


def load_agents() -> None:
    """Discover and instantiate all agents in the agents package."""
    _AGENTS.clear()
    _ACTIVE.clear()
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
            if (
                inspect.isclass(obj)
                and issubclass(obj, BaseAgent)
                and obj is not BaseAgent
            ):
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


def iter_active_agents() -> List[BaseAgent]:
    """Return a list of currently enabled agent instances."""
    return [_AGENTS[n] for n in _ACTIVE]


def get_agent(name: str) -> BaseAgent | None:
    """Retrieve a specific agent instance by module name."""
    return _AGENTS.get(name.lower())


async def emit(event: str, **kwargs: Any) -> None:
    """Broadcast ``event`` to all active agents.

    For an ``event`` named ``foo`` this will invoke an ``on_foo`` method on
    each agent if present. Agents may also implement a generic ``on_event``
    handler which receives the event name via a keyword argument.
    """

    tasks: List[tuple[str, str, Awaitable[Any]]] = []
    for name in list(_ACTIVE):
        agent = _AGENTS.get(name)
        if not agent:
            continue
        for attr, pass_name in ((f"on_{event}", False), ("on_event", True)):
            handler = getattr(agent, attr, None)
            if not handler:
                continue
            try:
                if pass_name:
                    result = handler(event=event, **kwargs)
                else:
                    result = handler(**kwargs)
                if inspect.isawaitable(result):
                    tasks.append((name, attr, result))
            except Exception as e:  # pragma: no cover - defensive
                display_error(f"Agent {name}.{attr} failed: {e}")
    if tasks:
        results = await asyncio.gather(
            *(t for _, _, t in tasks), return_exceptions=True
        )
        for (name, attr, _), res in zip(tasks, results):
            if isinstance(res, Exception):
                display_error(f"Agent {name}.{attr} failed: {res}")


def enable_agent(name: str) -> bool:
    """Enable an agent by module name. Returns True if successful."""
    key = name.lower()
    if key in _AGENTS:
        _ACTIVE.add(key)
        display_info(f"Agent enabled: {key}")
        return True
    display_error(f"Enable failed: unknown agent '{name}'")
    return False


def disable_agent(name: str) -> bool:
    """Disable an agent by module name. Returns True if successful."""
    key = name.lower()
    if key in _ACTIVE:
        _ACTIVE.remove(key)
        display_info(f"Agent disabled: {key}")
        return True
    display_error(f"Disable failed: unknown or inactive agent '{name}'")
    return False
