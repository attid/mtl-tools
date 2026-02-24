# Architecture

## Purpose
This document defines the current architectural boundaries of the project and the allowed dependency directions.

## Current Layer Map

1. `routers/`, `middlewares/`, `start.py`
- Delivery/interface layer.
- Accepts Telegram updates, validates context, calls application services.

2. `services/`
- Application layer.
- Contains use-case orchestration and cross-module workflows.
- Depends on domain models and repository/service interfaces.

3. `shared/domain/`
- Domain layer.
- Contains entities/enums/value semantics for business rules.
- Must not depend on Telegram SDK or DB adapters.

4. `db/`, `shared/infrastructure/database/`, `other/` integrations
- Infrastructure/adapters.
- DB repositories, SQLAlchemy models/migrations, external API clients.

## Dependency Direction (Target)

```text
interface (routers/middlewares) -> application (services) -> domain (shared/domain)
interface/application -> infrastructure adapters (db/other) through service/repository abstractions
```

## Practical Rules

1. Routers stay thin.
- No complex business logic in handlers.
- Handlers delegate to `services/` or focused helper modules.

2. Domain is framework-agnostic.
- No aiogram imports in `shared/domain/`.
- No direct SQLAlchemy model usage in domain entities.

3. Infrastructure is replaceable.
- DB and external integrations should be isolated in `db/` and `other/`.
- Public behavior should be testable via fakes/mocks.

4. Cross-cutting concerns belong to middlewares/services.
- User resolution, throttling, app context wiring should not be duplicated in routers.

## Known Deviations

The codebase is in transition and still contains legacy couplings. They are allowed temporarily but should be reduced iteratively with tests.
