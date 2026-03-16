# 2026-03-12: Guard my_chat_member auto-messages

## Контекст
- При `my_chat_member` бот пытается отправить авто-приветствие в групповой чат.
- В части чатов Telegram отвечает `Bad Request: not enough rights to send text messages to the chat`, из-за чего хендлер падает.

## План изменений
1. [x] Добавить regression-test для `my_chat_member`, который воспроизводит отказ Telegram на `sendMessage`.
2. [x] Обернуть авто-приветствия в `routers/admin_core.py` в безопасный guard с логированием вместо падения.
3. [x] Обновить/добавить тесты для нового поведения.
4. [x] Обновить docs/: перенести exec-plan в `completed/`.
5. [x] Проверка: `uv run pytest -q tests/routers/test_admin_core.py -k my_chat_member`.

## Риски и открытые вопросы
- Важно не проглотить несвязанные ошибки; guard должен покрывать именно telegram-ошибки отправки приветствия.
- Нужно сохранить текущее поведение для успешных сценариев без изменения текстов сообщений.

## Верификация
- Воспроизвести `my_chat_member` update для `MEMBER`/`ADMINISTRATOR` со стороны группового чата.
- Подменить ответ Telegram на `400 not enough rights to send text messages to the chat`.
- Убедиться, что dispatcher не падает, а existing success tests остаются зелёными.
