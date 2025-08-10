"""Agent package for MscBot v2"""

from .loader import (
    load_agents,
    iter_active_agents,
    enable_agent,
    disable_agent,
    get_agent,
    emit,
)

__all__ = [
    "load_agents",
    "iter_active_agents",
    "enable_agent",
    "disable_agent",
    "get_agent",
    "emit",
]
