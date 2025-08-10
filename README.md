# MscBot v2.0
Maintainer: **HGFantasy** — License: **MIT**

## What's new in v2.0
- Agent-based architecture with runtime enabling/disabling and hot-reloadable configuration.
- GitHub update alerts, command-file controls, metrics summaries, and ambulance-only dispatch mode.
- Cached config getters and precompiled mission-type checks for smoother performance.

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

See `config.sample.ini` for configuration options. Copy it to `config.ini` and edit.

For details on writing your own agents, check [agents/README.md](agents/README.md).
