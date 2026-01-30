# mtl-tools

Инструменты и боты для экосистемы MTL (aiogram).

## Архитектура (текущая)

Проект следует принципам Clean Architecture с адаптацией под Telegram‑бота:

- **Delivery**: `routers/` (handlers) и `middlewares/` (db/app_context/throttling и т.п.).
- **Application**: `services/` — прикладные сервисы и use‑cases. Входная точка DI — `services/app_context.py`.
- **Domain**: `shared/domain/` — сущности и статусы (например, `SpamStatus`, `AdminStatus`).
- **Infrastructure**: `db/` (SQLAlchemy репозитории) и `shared/infrastructure/database/` (модели и Alembic).
- **Utilities/Integrations**: `other/` — утилиты, внешние сервисы, Telegram‑хелперы.

Важно: статус спама пользователя хранится в `BotUsers.user_type` и читается через `SpamStatusService`.

## Локальный запуск

1. Установите зависимости: `uv sync`.
2. Скопируйте `.env.example` в `.env` и заполните обязательные значения.
3. Запустите бота: `uv run python start.py`.

## Запуск через Docker Compose

1. Подготовьте конфигурацию окружения (`.env`). Его использует и приложение, и Alembic.
2. Соберите образы: `docker compose build`.
3. Запустите стек: `docker compose up -d`.
4. Первым делом стартует сервис `migrations`: он применит `alembic upgrade head` и завершится.
5. После успешного применения миграций автоматически стартует основной сервис `bot`, а также вспомогательные `postgres` и `redis`.
6. Для просмотра логов используйте `docker compose logs -f bot`.


## Запуск тестов

Для запуска тестов используется `uv`:

```bash
uv run pytest -q
```

Подробнее — `TESTING.md`.

## Полезные команды

- Остановить стек: `docker compose down`.
- Перезапустить бота: `docker compose restart bot`.
- Ручной прогон миграций (при необходимости): `docker compose run --rm migrations`.

Перед запуском в production убедитесь, что значения в `.env` соответствуют боевой инфраструктуре и что доступ к PostgreSQL и Redis ограничен.
