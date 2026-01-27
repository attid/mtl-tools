# Миграция на uv — План реализации

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Перенести проект с requirements.txt на uv с очисткой неиспользуемых зависимостей.

**Architecture:** Создать pyproject.toml с разделением prod/dev зависимостей. Использовать только те пакеты, которые реально импортируются в коде. Обновить Docker и документацию.

**Tech Stack:** uv, pyproject.toml, Python 3.12+

---

## Результаты сканирования импортов

**Реальные импорты в коде (prod):**
- aiogram, aiohttp, apscheduler
- dateutil → python-dateutil
- gspread_asyncio → gspread-asyncio (+ gspread)
- httpx
- loguru
- oauth2client
- openai
- openrouter
- PIL → pillow
- pydantic, pydantic_settings → pydantic-settings
- pyrogram → kurigram (форк)
- redis
- requests
- sentry_sdk → sentry-sdk
- sqlalchemy
- stellar_sdk → stellar-sdk
- tiktoken
- uvloop

**Не нужны (не импортируются или удалены):**
- fdb, firebird-driver, sqlalchemy-firebird
- motor, pymongo
- future
- numpy, beautifulsoup4, bs4
- pyzbar, pyqrcode
- jsonpickle, tqdm
- aiofiles (не используется)
- mnemonic, cryptocode
- alembic (проверить — может быть в миграциях)

---

## Task 1: Создать pyproject.toml

**Files:**
- Create: `pyproject.toml`

**Step 1: Создать файл pyproject.toml**

```toml
[project]
name = "skynet-bot"
version = "1.0.0"
description = "Telegram bot for MTL ecosystem with Stellar integration"
requires-python = ">=3.12"
dependencies = [
    "aiogram>=3.20.0",
    "aiohttp>=3.11.0",
    "apscheduler>=3.10.0",
    "gspread>=5.7.0",
    "gspread-asyncio>=1.8.0",
    "httpx>=0.28.0",
    "kurigram>=2.2.0",
    "loguru>=0.7.0",
    "oauth2client>=4.1.0",
    "openai>=2.15.0",
    "openrouter>=0.1.0",
    "pillow>=10.3.0",
    "psycopg2-binary>=2.9.9",
    "pydantic>=2.11.0",
    "pydantic-settings>=2.8.0",
    "python-dateutil>=2.8.0",
    "redis>=5.1.0",
    "requests>=2.32.0",
    "sentry-sdk>=1.45.0",
    "sqlalchemy>=2.0.28",
    "stellar-sdk>=11.1.0",
    "tiktoken>=0.12.0",
    "uvloop>=0.21.0",
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
asyncio_default_fixture_loop_scope = "function"
testpaths = ["tests"]

[tool.ruff]
line-length = 120

[tool.mypy]
python_version = "3.12"
```

**Step 2: Commit**

```bash
git add pyproject.toml
git commit -m "build: add pyproject.toml for uv migration"
```

---

## Task 2: Проверить alembic

**Files:**
- Check: `db/alembic/`

**Step 1: Проверить использование alembic**

```bash
grep -r "alembic" --include="*.py" .
ls db/alembic/ 2>/dev/null || echo "No alembic dir"
```

**Step 2: Если alembic используется — добавить в dependencies**

Добавить в pyproject.toml:
```toml
"alembic>=1.13.0",
```

---

## Task 3: Инициализировать uv и установить зависимости

**Step 1: Инициализировать uv**

```bash
uv sync
```

**Step 2: Проверить что uv.lock создан**

```bash
ls -la uv.lock
```

**Step 3: Commit lock file**

```bash
git add uv.lock
git commit -m "build: add uv.lock"
```

---

## Task 4: Запустить тесты

**Step 1: Запустить все тесты**

```bash
uv run pytest -v
```

Expected: Все тесты проходят

**Step 2: Если тесты падают из-за отсутствующих зависимостей**

Добавить недостающие:
```bash
uv add <missing-package>
```

---

## Task 5: Проверить запуск бота

**Step 1: Попробовать импортировать main модуль**

```bash
uv run python -c "import start; print('OK')"
```

Expected: OK (или ошибка только про отсутствующие env vars, не про импорты)

---

## Task 6: Обновить Dockerfile

**Files:**
- Modify: `Dockerfile`

**Step 1: Прочитать текущий Dockerfile**

```bash
cat Dockerfile
```

**Step 2: Обновить на uv**

```dockerfile
FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Install dependencies first (for caching)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy source code
COPY . .

CMD ["uv", "run", "python", "start.py"]
```

**Step 3: Commit**

```bash
git add Dockerfile
git commit -m "build: update Dockerfile for uv"
```

---

## Task 7: Обновить документацию

**Files:**
- Modify: `AGENTS.md`

**Step 1: Найти упоминания requirements.txt и pip**

```bash
grep -n "requirements\|pip install" AGENTS.md
```

**Step 2: Заменить на uv команды**

- `pip install -r requirements.txt` → `uv sync`
- `pip install` → `uv add`
- `python` → `uv run python`
- `pytest` → `uv run pytest`

**Step 3: Commit**

```bash
git add AGENTS.md
git commit -m "docs: update AGENTS.md for uv"
```

---

## Task 8: Удалить requirements.txt

**Step 1: Финальная проверка**

```bash
uv run pytest -v
uv run python -c "import start; print('OK')"
```

**Step 2: Удалить requirements.txt**

```bash
git rm requirements.txt
git commit -m "build: remove requirements.txt - migrated to uv"
```

---

## Task 9: Проверить docker build

**Step 1: Собрать образ**

```bash
docker build -t skynet-bot:uv-test .
```

Expected: Успешная сборка

**Step 2: Если есть docker-compose — проверить и его**

```bash
docker-compose build
```

---

## Финальный чеклист

- [ ] pyproject.toml создан
- [ ] uv.lock сгенерирован
- [ ] Все тесты проходят
- [ ] Бот стартует (import start работает)
- [ ] Dockerfile обновлён
- [ ] AGENTS.md обновлён
- [ ] requirements.txt удалён
- [ ] Docker build работает
