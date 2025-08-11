# Changelog

## 2025-08-11 — v2.1.0

- Transport: refactored into a `TransportManager` with clearer flow and helpers.
- Transport: added env var overrides for all tuning (SLA, defers, attempt budget, caps).
- Politeness: made concurrency, retry, selector timeouts, and jitters configurable via env.
  - Added HumanAgent-aware scaling via `MISSIONCHIEF_POLITE_HUMAN_SCALE` to avoid stacked delays.
- Packaging: added `__init__.py` in packages; centralized Black/Ruff config via `pyproject.toml`.
- Tests: added basic smoke tests for config and agent loader.
- Main: safer entrypoint error handling and KeyboardInterrupt support.
- Docs: expanded README with development workflow and transport env vars.

## 2025-08-10 — v2.0

- Switched to an agent-based architecture with a central event bus for runtime coordination.
- Dynamic configuration and command-file agents allow hot reloads and runtime controls.
- HumanAgent provides fatigue-aware pacing; missions can be deferred and agents toggled on the fly.
- Added GitHub update notifications, metrics summaries, and ambulance-only dispatch mode.
- Optimized configuration lookups and dispatch classification, and removed obsolete legacy scripts.

## 2025-08-09 — v1.0 public release

- Switched to an agent-based architecture with runtime toggling and hot-reloadable configuration.
- Added GitHub update notifications, command-file runtime controls, metrics summary, and ambulance-only dispatch mode.
- Optimized configuration access with cached getters and sped up vehicle type classification.
- Added human-like behavior (random breaks, quiet hours, dwell after actions)
- Capped missions per cycle to 17–31; transports per cycle to 122–189
- Reduced window thrash; browsers default to 2
- Stability: polite wrappers for navigation/click/fill with retries and jitter
- Configurable humanization via `[human]` section in `config.ini`
- MIT licensed; cleaned project branding; repository scaffolding added

