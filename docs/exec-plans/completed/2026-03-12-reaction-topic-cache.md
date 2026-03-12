# 2026-03-12-reaction-topic-cache: Redis cache для reaction moderation

## Контекст
- `MessageReactionUpdated` в текущей версии aiogram не содержит `message_thread_id`, поэтому reaction-based topic moderation не может надёжно определить топик.
- Pyrogram lookup слишком дорогой для каждой реакции, поэтому нужен дешёвый локальный индекс `chat_id + message_id -> thread_id`.
- В проекте уже есть Redis, поэтому индекс логично хранить там с TTL 24 часа и использовать и для mute по реакции, и для удаления по `X`.

## План изменений
1. [x] Добавить тесты для Redis-backed message-thread cache и fake-реализацию сервиса для router-тестов.
2. [x] Добавить RED-тесты для `message_reaction`: mute работает через cache mapping, `X` удаляет сообщение и логирует в `SpamGroup`, отсутствие mapping ничего не делает.
3. [x] Добавить новый сервис message-thread cache в `AppContext` и wiring в runtime/test context.
4. [x] Наполнить cache на входящих сообщениях с `message_thread_id`.
5. [x] Переписать `message_reaction` в `routers/admin_core.py` на использование cache вместо несуществующего `message_thread_id`, и реализовать delete по `X`.
6. [x] Прогнать целевые тесты и затем весь `tests/routers/test_admin_core.py`.
7. [x] Перенести план в `docs/exec-plans/completed/` с отмеченными чекбоксами.

## Риски и открытые вопросы
- Реакции будут работать только для сообщений, которые бот уже видел и успел записать в cache.
- Нужно аккуратно встроиться в существующий поток входящих сообщений, не ломая другую логику `last_handler`.

## Верификация
- По reaction event без `message_thread_id` mute и delete всё равно находят топик через cache mapping.
- `X`-reaction пересылает пользовательское сообщение в `SpamGroup`, пишет кто удалил, затем удаляет target message.
- При отсутствии mapping handler безопасно ничего не делает и не шлёт ошибки в чат.
