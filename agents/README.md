# Agent Development Guide

MscBot supports a lightweight agent system. Each `*.py` file inside the
`agents/` directory is inspected on start. Any class deriving from
`BaseAgent` will be instantiated automatically.

## Creating an agent

1. Create a new module in `agents/` (e.g. `my_agent.py`).
2. Subclass `BaseAgent` and override the hooks you need:
   - `on_start` – called once after configuration validation.
   - `on_mission_tick` – called every mission loop iteration.
   - `on_transport_tick` – called every transport loop iteration.
   - `on_shutdown` – called once when the bot exits.
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

### Runtime control

When the `command_file` agent is active, agents can be toggled while the bot
is running. Write commands to the configured command file, for example:

```
agent-disable metrics_summary
agent-enable update_check
```

Each line is processed and the file is deleted after reading.
