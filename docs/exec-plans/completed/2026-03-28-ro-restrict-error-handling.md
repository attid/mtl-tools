# 2026-03-28-ro-restrict-error-handling: Обработка ошибок restrict в !ro

## Контекст

Команда `!ro` не обрабатывает `TelegramBadRequest` при вызове `restrict`.
Это может произойти если пользователя нет в чате (например, при кросс-топик
`external_reply` из другого чата) — исключение уйдёт необработанным в sentry.

## План изменений

1. [x] Написать падающий тест на случай когда `restrictChatMember` возвращает ошибку
2. [x] Убедиться что тест падает (RED)
3. [x] Обернуть `restrict` в `try/except TelegramBadRequest` с понятным ответом
4. [x] Убедиться что тест проходит (GREEN)
5. [x] `just lint` + `pyright routers/admin_core.py` — чисто

## Риски и открытые вопросы

- Нет

## Верификация

- `uv run pytest -q tests/routers/test_admin_core.py -k 'ro_command'` → `6 passed`
- `just lint` → `All checks passed!`
- `uv run pyright routers/admin_core.py` → `0 errors, 0 warnings, 0 informations`
- При ошибке `restrictChatMember` бот отвечает понятным сообщением
- Существующие тесты `!ro` — зелёные
