# 2026-04-10-telegram-api-url: Configurable Telegram Bot API server URL

## Контекст
- Сейчас `start.py` создаёт `AiohttpSession()` без параметров, поэтому бот всегда ходит на `api.telegram.org`.
- Нужна возможность направить бота на self-hosted `telegram-bot-api` (снять лимит 50 МБ на загрузку файлов, работать в изолированной инфраструктуре).
- Параметр — единый для prod и test режимов, опциональный: если пусто — поведение не меняется.
- Связанных issue/ADR нет (уточнение в живом диалоге).

## План изменений
1. [x] `other/config_reader.py`: добавить в `Settings` опциональное поле `telegram_api_url: str | None = None` рядом с токенами (после `test_token`, строка ~19).
2. [x] `start.py`:
   - Импорт `from aiogram.client.telegram import TelegramAPIServer`.
   - В `main()` (строки 167-168) заменить безусловное `AiohttpSession()` на ветку: если `config.telegram_api_url` задан — `AiohttpSession(api=TelegramAPIServer.from_base(config.telegram_api_url, is_local=True))` + `logger.info("Using local Telegram Bot API: ...")`; иначе — как сейчас.
   - Остальной код (`session.middleware(...)`, создание `Bot(...)` для test/prod) не меняется — одна и та же `session` используется в обеих ветках.
3. [x] `.env.example`: в секцию `# --- Telegram Bot ---` добавить закомментированную строку `# TELEGRAM_API_URL=http://telegram-bot-api:8081` с коротким пояснением.
4. [x] Тесты: существующие тесты `start.main` не запускают, поэтому новых тестов не добавляем (изменение сводится к условному построению сессии). Если в ходе реализации обнаружится подходящее место для unit-теста хелпера — добавить его.
5. [x] docs/: публичных контрактов не затрагиваем, правки в `docs/` не требуются.
6. [x] Проверка: `just lint`, `just types`, `just test`.

## Риски и открытые вопросы
- **`is_local=True`**: корректный режим для self-hosted bot-api (иначе `download_file` и работа с большими файлами сломаются). Риск — если пользователь захочет указать URL прокси-зеркала `api.telegram.org` без режима local, флаг будет мешать. Решение: сейчас цель — именно локальный bot-api (пользователь подтвердил), поэтому фиксируем `is_local=True`. Если понадобится прокси-режим — добавим отдельный флаг позднее.
- **Импорт**: `aiogram.client.telegram.TelegramAPIServer` должен существовать в текущей версии aiogram — проверить при реализации (`uv run python -c "from aiogram.client.telegram import TelegramAPIServer"`).
- Миграции БД/конфигов не требуются — поле опциональное со значением по умолчанию.

## Верификация
1. **Без env**: не задавать `TELEGRAM_API_URL`, запустить `uv run python start.py` — в логах нет строки `Using local Telegram Bot API`, бот поллит `api.telegram.org` как раньше.
2. **С env**: `TELEGRAM_API_URL=http://localhost:8081` в `.env`, запустить бота — в логах появится `Using local Telegram Bot API: http://localhost:8081`. Поллинг упадёт с сетевой ошибкой к 8081 (если реального сервера нет) — это ожидаемо и доказывает, что параметр применился.
3. **Статика**: `just lint` + `just types` без новых ошибок.
4. **Тесты**: `just test` — без регрессий.

## Затрагиваемые файлы (для Task Intake Protocol)
- `other/config_reader.py`
- `start.py`
- `.env.example`
