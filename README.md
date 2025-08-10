# MscBot v2.0
Maintainer: **HGFantasy** — License: **MIT**

## What's new in v2.0
- Agent-based architecture with an inter-agent event bus for runtime coordination.
- Command-file and dynamic-config agents enable hot reloads and runtime controls.
- HumanAgent delivers adaptive human-like pacing; missions can be deferred and agents toggled on the fly.
- GitHub update alerts, metrics summaries, and ambulance-only dispatch mode.

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

Configuration lives in `config.ini`; adjust settings as needed.

For details on writing your own agents, check [agents/README.md](agents/README.md).
