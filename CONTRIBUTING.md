# Contributing

Thanks for helping improve MscBot!

## Getting started
1. Install Python 3.13+
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   # Windows PowerShell:
   .\.venv\Scripts\Activate.ps1
   # macOS/Linux:
   source .venv/bin/activate
   ```
3. Install runtime dependencies:
   ```bash
   pip install -r requirements.txt
   python -m playwright install
   ```
4. Configure `config.ini` (or set env vars `MISSIONCHIEF_USER`, `MISSIONCHIEF_PASS`).

## Dev workflow
- Branch from `main`: `feat/xyz`, `fix/bug-123`
- Run lints locally:
  ```bash
  pip install -r dev-requirements.txt
  ruff check .
  ```
- Commit using clear messages (Conventional Commits encouraged).
- Open a PR with a short description of changes and testing notes.

## Code style
- Prefer small, composable async functions.
- Use `utils/politeness.py` helpers for all networked interactions.
- Keep selectors resilient; avoid brittle waits.
- Be gentle with default delays and concurrency.

## Testing
- Smoke test login on a throwaway account.
- Validate dispatch/transport loops at low concurrency (2) with headful mode first.
