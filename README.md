# MscBot v2.0
Maintainer: **HGFantasy** — License: **MIT**

## Highlights
- Agent-based architecture with an inter-agent event bus for runtime coordination.
- Command-file and dynamic-config agents enable hot reloads and runtime controls.
- Cache clearing agent purges cached configuration values and mission/transport caches periodically.
- HumanAgent delivers adaptive human-like pacing; missions can be deferred and agents toggled on the fly.
- GitHub update alerts, metrics summaries, and ambulance-only dispatch mode.
- Update check tracks main repository commits and auto-updates by pulling new files and restarting automatically.
- Cached config getters and precompiled mission-type checks for smoother performance.
- Environment variables can be loaded from a `.env` file.
- Browsers launch concurrently for faster startup.
- Simplified configuration validation for clarity.

## Quickstart (Windows PowerShell)
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install
$env:PYTHONUNBUFFERED="1"
.\.venv\Scripts\python.exe -u -X dev Main.py
```

Configuration lives in `config.ini`; adjust settings as needed. Environment
variables may also be placed in a `.env` file.
See `config.sample.ini` for configuration options. Copy it to `config.ini` and edit.

For details on writing your own agents, check [agents/README.md](agents/README.md).
