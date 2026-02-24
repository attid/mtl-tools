# Conventions

## Scope
Coding and integration conventions for this repository.

## Code Structure

1. Handlers
- Keep router handlers minimal.
- Parse input, enforce access checks, call services, send response.
- Non-trivial behavior belongs in `services/` or focused modules in `other/`.

2. Services
- Services orchestrate business flow and adapters.
- Prefer explicit dependencies via `AppContext`.
- Keep method names behavior-oriented.

3. Persistence
- DB reads/writes go through repositories in `db/repositories/`.
- Avoid ad-hoc SQL in routers.

## Data and Contracts

1. Parse, do not guess.
- Validate required fields for commands/events.
- For channel contracts (`#skynet ... command=...`), reject invalid payloads with explicit error paths.

2. Keep contracts explicit.
- If changing external/event behavior, update `docs/contracts` (to be added in later iteration) and tests in the same change.

## Logging

1. Use `loguru`.
- No `print()` in runtime paths.
- Log moderation actions and failures with stable fields (`action`, `chat_id`, `user_id`, `source` where applicable).

2. Prefer artifacts for moderation decisions.
- Ban/restrict/unban flows should leave observable artifacts (logs and/or SpamGroup messages).

## Tests

1. Add tests for behavior changes.
- Router-level behavior in `tests/routers/`.
- Repository/service logic in dedicated test modules.

2. Keep tests deterministic.
- Use mocks/fakes for network and external APIs.
- Avoid hidden time/random coupling unless explicitly controlled.

## Commit Style

Use Conventional Commits:
- `feat(scope): ...`
- `fix(scope): ...`
- `refactor(scope): ...`
- `docs(scope): ...`
- `chore(scope): ...`
