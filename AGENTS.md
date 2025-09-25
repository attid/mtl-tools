# Repository Guidelines

## Project Structure & Module Organization
- `start.py`: Entry point. Creates bot, registers middlewares/routers, starts polling.
- `routers/`: Aiogram handlers grouped by feature (e.g., `admin_system.py`, `stellar.py`). Each module should expose `register_handlers(dp, bot)` and may set `register_handlers.priority = <int>` for load order.
- `middlewares/`: Cross‑cutting concerns (`db`, `throttling`, `retry`, `sentry_error_handler`).
- `db/`: SQLAlchemy models and data access, plus Firebird/Mongo helpers.
- `other/`: Utilities (config, Stellar, caching, OpenAI, etc.). Avoid business logic in routers when possible.
- `scripts/`: Operational scripts (reports, exchanges, ledger checks).
- `deploy/`: Systemd units and update scripts for production.
- `docs/`: Design and improvement notes.

## Build, Test, and Development Commands
- Setup env: `python -m venv .venv && source .venv/bin/activate`
- Install deps: `pip install -r requirements.txt`
- Configure: copy `.env_sample` to `.env` and fill required keys.
- Run bot locally: `python start.py`
- Type check: `mypy .` (incrementally fix violations)
- Lint (if installed): `ruff .` (or your preferred linter)
- Clean caches/logs: `./clean.sh`

## Coding Style & Naming Conventions
- You must communicate in Russian; code comments and docstrings must stay in English.
- Python 3, 4‑space indentation, UTF‑8.
- Names: `snake_case` for functions/vars, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants.
- Prefer type hints across public functions; keep routers thin and delegate to services in `other/`.
- Logging: use `loguru` logger; no `print()` in runtime paths.

## Testing Guidelines
- No formal suite yet. Add `pytest` tests under `tests/` for new logic (pure utils in `other/`, DB helpers, router helpers via unit‑level functions).
- Keep tests isolated from Telegram/DB: mock network and DB calls; use small fixtures.
- Run locally (if added): `pytest -q`.

## Commit & Pull Request Guidelines
- Use Conventional Commits: `feat(scope):`, `fix(scope):`, `refactor(scope):` (emojis optional, keep scope meaningful).
- PRs: concise description, motivation, screenshots/log snippets when UI/log behavior changes; reference issues; note config or migration impacts.
- Keep diffs focused; include follow‑ups in separate PRs.

## Security & Configuration Tips
- Never commit secrets. `.env` is ignored; keep tokens/DSNs there. Validate critical settings on startup.
- Limit admin capabilities to configured chat/user IDs; avoid username‑based checks.
- Be mindful of rate limits; use provided throttling middleware.

## Router/Agent Instructions
- New feature: create `routers/<feature>.py` with `register_handlers(dp, bot)`. Optionally set `register_handlers.priority` (lower loads earlier).
- Add pure helpers to `other/` and DB access in `db/` to keep handlers small, testable, and reusable.
