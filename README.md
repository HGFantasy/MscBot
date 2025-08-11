# MscBot v2.1.0
Maintainer: **HGFantasy** — License: **MIT**

## Highlights
- Agent-based architecture with an inter-agent event bus for runtime coordination.
- Command-file and dynamic-config agents enable hot reloads and runtime controls.
- HumanAgent delivers adaptive human-like pacing; missions can be deferred and agents toggled on the fly.
- Smarter auto-update with configurable branch/interval, metrics summaries, and ambulance-only dispatch mode.
- Cached config getters and precompiled mission-type checks for smoother performance.
- Environment variables can be loaded from a `.env` file.
- Browsers launch concurrently for faster startup.

## What’s New in 2.1.0
- Refactored transport handling into a clear `TransportManager` with SLA and deferral logic.
- Added environment variable overrides for all transport tuning knobs.
- Packaging hygiene (`__init__.py`), central tool config via `pyproject.toml`.
- Added smoke tests and tightened error handling in the entrypoint.

## Quickstart (Windows PowerShell)
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
 .\.venv\Scripts\python.exe -m pip install -r requirements.txt
 $env:PYTHONUNBUFFERED="1"
 .\.venv\Scripts\python.exe -u -X dev Main.py
```

Configuration lives in `config.ini`; adjust settings as needed. Environment
variables may also be placed in a `.env` file.
See `config.sample.ini` for configuration options. Copy it to `config.ini` and edit.

For details on writing your own agents, check [agents/README.md](agents/README.md).

## Example: Offloading tasks to Go

A minimal Go service lives under `go_service/` and exposes `/fib` and `/score` endpoints.
Start it in one terminal:

```bash
go run go_service/main.go
```

Then from Python you can request the result:

```python
from utils.orchestrator_client import get_fibonacci, get_priority_score
print(get_fibonacci(10))
print(get_priority_score("Major wildfire"))
```

This demonstrates delegating performance-critical work to a faster language
via a simple HTTP API. The dispatcher now relies on this Go service for
mission priority scoring, so keep it running during normal operation.

## Development

- Format: `Scripts/black.exe .` (or `black .` if on PATH)
- Lint: `Scripts/ruff.exe check .` (or `ruff check .`)
- Tests: `py -m pytest -q`

Configuration lives in `config.ini` with environment overrides:

- `MISSIONCHIEF_USER` / `MISSIONCHIEF_PASS` for credentials
- See `data/config_settings.py` for all defaults

Transport-related env overrides (examples):

- `MISSIONCHIEF_TRANSPORT_MAX_HOSPITAL_KM`
- `MISSIONCHIEF_TRANSPORT_MAX_HOSPITAL_TAX_PCT`
- `MISSIONCHIEF_TRANSPORT_HOSPITAL_FALLBACK` (e.g., `wait`)
- `MISSIONCHIEF_TRANSPORT_HOSPITAL_RECHECK_MIN`
- `MISSIONCHIEF_TRANSPORT_MAX_PRISON_KM`
- `MISSIONCHIEF_TRANSPORT_MAX_PRISON_TAX_PCT`
- `MISSIONCHIEF_TRANSPORT_PRISON_FALLBACK` (e.g., `wait`)
- `MISSIONCHIEF_TRANSPORT_PRISON_RECHECK_MIN`
- `MISSIONCHIEF_TRANSPORT_MIN_FREE_BEDS`
- `MISSIONCHIEF_TRANSPORT_MIN_FREE_CELLS`
- `MISSIONCHIEF_TRANSPORT_BLACKLIST_TTL_MIN`
- `MISSIONCHIEF_TRANSPORT_ATTEMPT_BUDGET`
- `MISSIONCHIEF_TRANSPORT_ESCALATE_AFTER_DEFERS`
- `MISSIONCHIEF_TRANSPORT_SLA_HOSPITAL_MIN`
- `MISSIONCHIEF_TRANSPORT_SLA_PRISON_MIN`

Politeness-related env overrides (examples):

- `MISSIONCHIEF_POLITE_MAX_CONCURRENCY`
- `MISSIONCHIEF_POLITE_RETRY_ATTEMPTS`
- `MISSIONCHIEF_POLITE_RETRY_BASE_DELAY`
- `MISSIONCHIEF_POLITE_SELECTOR_TIMEOUT_MS`
- `MISSIONCHIEF_POLITE_GATE_ENTRY_BASE`
- `MISSIONCHIEF_POLITE_GATE_ENTRY_SPREAD`
- `MISSIONCHIEF_POLITE_GATE_EXIT_BASE`
- `MISSIONCHIEF_POLITE_GATE_EXIT_SPREAD`
- `MISSIONCHIEF_POLITE_GOTO_DWELL_BASE`
- `MISSIONCHIEF_POLITE_GOTO_DWELL_SPREAD`
 - `MISSIONCHIEF_POLITE_HUMAN_SCALE` (scale politeness delays when HumanAgent is active)
