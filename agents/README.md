# Agent Development Guide

MscBot supports a lightweight agent system. Each `*.py` file inside the
`agents/` directory is inspected on start. Any class deriving from
`BaseAgent` will be instantiated automatically.

Built-in agents such as `update_check`, `cache_clear`, `command_file`, and
`dynamic_config` provide reference implementations and useful runtime
features.

## Creating an agent

1. Create a new module in `agents/` (e.g. `my_agent.py`).
2. Subclass `BaseAgent` and override the hooks you need:
   - `on_start` – called once after configuration validation.
   - `on_mission_tick` – called every mission loop iteration.
   - `on_transport_tick` – called every transport loop iteration.
   - `after_mission_tick` – called after mission logic completes each iteration.
   - `after_transport_tick` – called after transport logic completes each iteration.
   - `on_event` – react to custom events broadcast by other agents.
   - `on_shutdown` – called once when the bot exits.
   - `enabled` – return `False` to skip loading by default.
3. Place your class in the module's global scope so the loader can find it.
4. Restart the bot; the agent is loaded automatically—no registration is
   necessary.

Example:

```python
from agents.base import BaseAgent

class MyAgent(BaseAgent):
    async def on_start(self, **kwargs):
        print("Agent ready!")
```

Agents can use any utilities from the rest of the project and may read
configuration via the helpers in `data.config_settings`.

### Inter-agent events

Agents may communicate by broadcasting events:

```python
from agents import emit

await emit("config_reload")  # ask dynamic config agent to reload
```

Handle events by overriding `on_event`:

```python
class MyAgent(BaseAgent):
    async def on_event(self, event: str, **kwargs):
        if event == "config_reloaded":
            print("config updated!")
```

## Enabling or disabling agents

Agents are loaded automatically, but you can selectively enable or disable
them via the `[agents]` section in `config.ini`:

```ini
[agents]
enabled = update_check,command_file
disabled = logger
```

If `enabled` is non-empty, only the listed agents are loaded. Any names in
`disabled` are always skipped.

Agents may also implement an `enabled()` method that returns `False` to opt out
of loading entirely until conditions change.

### Runtime control

When the `command_file` agent is active, agents can be toggled while the bot
is running. Write commands to the configured command file, for example:

```
agent-disable metrics_summary
agent-enable update_check
```

Each line is processed and the file is deleted after reading.
