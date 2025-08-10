# Changelog

## 2025-08-10 — v2.0
- Switched to an agent-based architecture with runtime toggling and hot-reloadable configuration.
- Added GitHub update notifications, command-file runtime controls, metrics summary, and ambulance-only dispatch mode.
- Optimized configuration access with cached getters and sped up vehicle type classification.

## 2025-08-09 — v1.0 public release
- Initial public release for Python 3.13

## 2025-08-09 — Public release
- Added human-like behavior (random breaks, quiet hours, dwell after actions)
- Capped missions per cycle to 17–31; transports per cycle to 122–189
- Reduced window thrash; browsers default to 2
- Stability: polite wrappers for navigation/click/fill with retries and jitter
- Configurable humanization via `[human]` section in `config.ini`
- MIT licensed; cleaned project branding; repository scaffolding added

