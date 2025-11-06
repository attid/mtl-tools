# Управление миграциями Alembic для PostgreSQL

Эта директория содержит конфигурацию и скрипты миграций Alembic для базы данных PostgreSQL.

## Конфигурация

Основной файл конфигурации: `alembic.ini`.

Строка подключения к базе данных определяется в `env.py` следующим образом:

1.  **Переменная окружения `POSTGRES_URL`**: Если эта переменная установлена, ее значение будет использовано в первую очередь.
2.  **`sqlalchemy.url` в `alembic.ini`**: Если `POSTGRES_URL` не установлена, будет использовано значение из `alembic.ini`.

**Рекомендуется использовать `POSTGRES_URL` для production-окружений и `alembic.ini` для локальной разработки.**

## Запуск команд Alembic

Все команды Alembic должны запускаться из корня проекта, указывая путь к `alembic.ini` с помощью флага `-c`.

**Пример:**

```bash
# Активируйте ваше виртуальное окружение (например, .venv_tmp_alembic, если вы его используете)
# source .venv_tmp_alembic/bin/activate

# Установите переменную окружения для production (если нужно)
# export DATABASE_URL="postgresql://prod_user:prod_password@prod_host:5432/prod_db"

# 1. Сгенерировать новую миграцию (после изменения моделей SQLAlchemy)
#    Alembic сравнит текущее состояние моделей с состоянием БД и предложит изменения.
#    Обязательно проверьте сгенерированный файл миграции перед применением!
#    alembic -c shared/infrastructure/database/alembic/alembic.ini revision --autogenerate -m "Описание изменений"

# 2. Применить все ожидающие миграции к базе данных
#    alembic -c shared/infrastructure/database/alembic/alembic.ini upgrade head

# 3. Откатить последнюю миграцию
#    alembic -c shared/infrastructure/database/alembic/alembic.ini downgrade -1

# 4. Показать историю миграций
#    alembic -c shared/infrastructure/database/alembic/alembic.ini history

# 5. Показать текущую версию базы данных
#    alembic -c shared/infrastructure/database/alembic/alembic.ini current

# Деактивируйте виртуальное окружение (если вы его использовали)
# deactivate
```

**Важно:** Всегда проверяйте сгенерированные Alembic скрипты миграции перед их применением к базе данных, особенно в production-окружении.
