"""Dynamic agent loader for MscBot."""
from __future__ import annotations

import importlib
import inspect
import pkgutil

import asyncio
from pathlib import Path
from typing import Any, Dict, List

from pathlib import Path
from typing import Dict, List
 main

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


def iter_active_agents() -> List[BaseAgent]:
    """Return a list of currently enabled agent instances."""
    return [_AGENTS[n] for n in list(_ACTIVE)]



def get_agent(name: str) -> BaseAgent | None:
    """Retrieve a specific agent instance by module name."""
    return _AGENTS.get(name.lower())


async def emit(event: str, **kwargs: Any) -> None:
    """Broadcast an event to all active agents."""
    tasks = []
    for name in list(_ACTIVE):
        agent = _AGENTS.get(name)
        if not agent:
            continue
        handler = getattr(agent, "on_event", None)
        if not handler:
            continue
        try:
            if inspect.iscoroutinefunction(handler):
                tasks.append(handler(event=event, **kwargs))
            else:
                handler(event=event, **kwargs)
        except Exception as e:  # pragma: no cover - defensive
            display_error(f"Agent {name} event error: {e}")
    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                display_error(f"Agent event error: {r}")



 main
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

