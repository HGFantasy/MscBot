# MissionchiefBot-X v1.1 (py3.13)
Maintainer: **HGFantasy** — License: **MIT**

## Quickstart (Windows PowerShell)
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install
# Or set env vars instead of editing config.ini:
# $env:MISSIONCHIEF_USER="you@example.com"; $env:MISSIONCHIEF_PASS="yourpassword"
$env:PYTHONUNBUFFERED="1"
.\.venv\Scripts\python.exe -u -X dev Main.py
```

See `config.sample.ini` for configuration options. Copy it to `config.ini` and edit.
