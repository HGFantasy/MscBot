"""Agent to execute commands from a file at runtime."""

from __future__ import annotations

from pathlib import Path

from data.config_settings import get_command_file, reload_config
from utils.pretty_print import display_error, display_info

from .base import BaseAgent
from .loader import disable_agent, emit, enable_agent


class CommandFileAgent(BaseAgent):
    """Reads commands from a file and applies runtime controls."""

    def __init__(self) -> None:
        self._path = Path(get_command_file())

    async def on_start(self, **_: dict) -> None:
        await self._maybe_run()

    async def on_mission_tick(self, **_: dict) -> None:
        await self._maybe_run()

    async def on_transport_tick(self, **_: dict) -> None:
        await self._maybe_run()

    async def _maybe_run(self) -> None:
        if not self._path.exists():
            return
        try:
            lines = [
                line.strip().lower()
                for line in self._path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self._path.unlink()
        except Exception as e:
            display_error(f"CommandFileAgent read failed: {e}")
            return
        for cmd in lines:
            try:
                if cmd == "pause":
                    Path("PAUSE").touch()
                    display_info("CommandFileAgent: pause")
                elif cmd == "resume":
                    try:
                        Path("PAUSE").unlink()
                    except FileNotFoundError:
                        pass
                    display_info("CommandFileAgent: resume")
                elif cmd == "stop":
                    Path("STOP").touch()
                    display_info("CommandFileAgent: stop")
                elif cmd == "reload-config":
                    await emit("config_reloaded")
                    display_info("CommandFileAgent: config reload requested")
                    reload_config()
                    display_info("CommandFileAgent: config reloaded")
                elif cmd.startswith("agent-enable "):
                    name = cmd.split(" ", 1)[1]
                    if enable_agent(name):
                        display_info(f"CommandFileAgent: enabled {name}")
                    else:
                        display_error(f"CommandFileAgent: unknown agent '{name}'")
                elif cmd.startswith("agent-disable "):
                    name = cmd.split(" ", 1)[1]
                    if disable_agent(name):
                        display_info(f"CommandFileAgent: disabled {name}")
                    else:
                        display_error(f"CommandFileAgent: unknown agent '{name}'")
                else:
                    display_error(f"CommandFileAgent: unknown command '{cmd}'")
            except Exception as e:
                display_error(f"CommandFileAgent command '{cmd}' failed: {e}")
