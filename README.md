# mtl-tools

Инструменты и боты для экосистемы MTL.

## Локальный запуск

1. Создайте виртуальное окружение: `python -m venv .venv && source .venv/bin/activate`.
2. Установите зависимости: `pip install -r requirements.txt`.
3. Скопируйте `.env_sample` в `.env` и заполните обязательные значения.
4. Запустите бота: `python start.py`.

## Запуск через Docker Compose

1. Подготовьте конфигурацию окружения (`.env`). Его использует и приложение, и Alembic.
2. Соберите образы: `docker compose build`.
3. Запустите стек: `docker compose up -d`.
4. Первым делом стартует сервис `migrations`: он применит `alembic upgrade head` и завершится.
5. После успешного применения миграций автоматически стартует основной сервис `bot`, а также вспомогательные `postgres` и `redis`.
6. Для просмотра логов используйте `docker compose logs -f bot`.

## Полезные команды

- Остановить стек: `docker compose down`.
- Перезапустить бота: `docker compose restart bot`.
- Ручной прогон миграций (при необходимости): `docker compose run --rm migrations`.

Перед запуском в production убедитесь, что значения в `.env` соответствуют боевой инфраструктуре и что доступ к PostgreSQL и Redis ограничен.
