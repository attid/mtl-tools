# Миграция на uv с очисткой зависимостей

**Дата:** 2026-01-27

## Цель

Перейти с requirements.txt на uv (pyproject.toml), очистив при этом неиспользуемые зависимости.

## Подход

**Гибридный** — автоматически найти реальные импорты в коде, перенести только их, проверить тестами.

## Решения

- **Python**: >=3.12
- **Разделение зависимостей**: да (prod / dev)
- **Удалить точно**: fdb, firebird-driver, sqlalchemy-firebird, motor, pymongo, future
- **Оставить**: kurigram, tiktoken

## План выполнения

### 1. Сканирование импортов

- Grep по `^import ` и `^from .* import` во всех `*.py`
- Исключить стандартную библиотеку Python
- Исключить локальные импорты (routers, services, db, other)
- Применить маппинг импорт → пакет

**Известные маппинги:**

| Импорт | Пакет |
|--------|-------|
| PIL | pillow |
| bs4 | beautifulsoup4 |
| yaml | pyyaml |
| dotenv | python-dotenv |
| dateutil | python-dateutil |
| nacl | pynacl |
| Cryptodome | pycryptodomex |

### 2. Классификация зависимостей

**Dev:**
- pytest, pytest-asyncio
- mypy, mypy-extensions
- ruff

**Prod:** всё остальное что реально импортируется

### 3. Создание pyproject.toml

```toml
[project]
name = "skynet-bot"
version = "1.0.0"
description = "Telegram bot for MTL ecosystem with Stellar integration"
requires-python = ">=3.12"
dependencies = [
    # заполнится по результатам сканирования
]

[tool.uv]
dev-dependencies = [
    "pytest>=9.0.0",
    "pytest-asyncio>=1.3.0",
    "mypy>=1.5.0",
    "ruff>=0.11.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 120

[tool.mypy]
python_version = "3.12"
```

### 4. Инициализация uv

```bash
uv init
uv add <prod-dependencies>
uv add --dev pytest pytest-asyncio mypy ruff
```

### 5. Обновление Docker

**Dockerfile:**
```dockerfile
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .
CMD ["uv", "run", "python", "start.py"]
```

### 6. Верификация

1. `uv sync` — установка зависимостей
2. `uv run pytest` — все тесты проходят
3. Сухой запуск бота — проверка старта
4. `uv run mypy .` — проверка типов

### 7. Очистка и документация

- Удалить requirements.txt (только после успешной верификации)
- Обновить AGENTS.md: `pip install -r requirements.txt` → `uv sync`
- Обновить README если есть инструкции по установке

## Откат

requirements.txt удаляется только после полной верификации. До этого можно откатиться на старую схему.
