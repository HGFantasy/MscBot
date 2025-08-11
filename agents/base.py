"""Base classes and interfaces for MscBot agents."""

from __future__ import annotations

from typing import Any


class BaseAgent:
    """Lightweight async agent interface.

    Agents can override any of these coroutine hooks to extend the bot's
    behaviour. Hooks are awaited if defined as coroutines; regular functions
    are also supported for convenience. Agents may also implement an
    ``enabled`` method returning ``False`` to opt out of loading.
    """

    def enabled(self) -> bool:  # type: ignore[override]
        """Return ``True`` if the agent should be loaded."""
        return True

    async def on_start(self, **kwargs: Any) -> None:  # noqa: D401
        """Called once when the bot has validated configuration and starts."""

    async def on_mission_tick(self, **kwargs: Any) -> None:  # noqa: D401
        """Called each iteration of the mission loop."""

    async def after_mission_tick(self, **kwargs: Any) -> None:  # noqa: D401
        """Called after mission logic completes each iteration."""

    async def on_transport_tick(self, **kwargs: Any) -> None:  # noqa: D401
        """Called each iteration of the transport loop."""

    async def after_transport_tick(self, **kwargs: Any) -> None:  # noqa: D401
        """Called after transport logic completes each iteration."""

    async def on_event(self, event: str, **kwargs: Any) -> None:  # noqa: D401
        """Handle an arbitrary event broadcast by other agents."""

    async def on_shutdown(self, **kwargs: Any) -> None:  # noqa: D401
        """Called once after all browsers have been closed."""
