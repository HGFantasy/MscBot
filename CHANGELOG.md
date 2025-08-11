# Changelog

## Unreleased

- No unreleased changes.

## 2025-08-11 — v2.0

- Switched to an agent-based architecture with a central event bus for runtime coordination.
- Dynamic configuration and command-file agents allow hot reloads and runtime controls.
- HumanAgent provides fatigue-aware pacing; missions can be deferred and agents toggled on the fly.
- Added GitHub update notifications, metrics summaries, and ambulance-only dispatch mode.
- Optimized configuration lookups and dispatch classification, and removed obsolete legacy scripts.
- Load environment variables from a `.env` file at startup.
- Launch authenticated browsers concurrently for faster startup.
- Simplified configuration validation for clarity.
- Updated documentation and licensing.
- Reworked update check to track main repository commits and auto-update on startup.
- Auto-update now pulls new files and restarts the bot when updates are detected.
- Added cache clearing agent to periodically purge cached configuration values.
- Cache clearing agent now wipes mission and transport cache files.

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

