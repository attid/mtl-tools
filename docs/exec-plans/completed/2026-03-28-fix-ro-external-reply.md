# 2026-03-28-fix-ro-external-reply: Поддержка external_reply в команде !ro

## Контекст

Команда `!ro <duration>` не работает в Telegram Forum-группах (с топиками), когда
администратор отвечает на сообщение из **другого топика** того же чата.

В этом случае Telegram Bot API выставляет `message.external_reply` вместо
`message.reply_to_message`. Код проверяет только `reply_to_message is None` и
возвращает ошибку «Please send for reply message to set ro», хотя в клиенте
цитата видна.

## План изменений

1. [x] Написать падающий тест `test_ro_command_external_reply` в `tests/routers/test_admin_core.py`
2. [x] Убедиться что тест падает (RED)
3. [x] Добавить `MessageOriginUser` в импорты `routers/admin_core.py`
4. [x] Исправить `cmd_set_ro`: если `reply_to_message is None`, проверять `external_reply.origin`
       типа `MessageOriginUser` и использовать `sender_user` как целевого пользователя
5. [x] Убедиться что тест проходит (GREEN)
6. [x] `just lint` + `pyright routers/admin_core.py` — чисто (pre-existing ошибки в mic.py не затронуты)

## Риски и открытые вопросы

- `external_reply.origin` может быть `MessageOriginHiddenUser` (анонимный пользователь) —
  в этом случае ограничить нельзя, нужно вернуть понятную ошибку
- `external_reply.origin` может быть `MessageOriginChat` (канал/анонимный администратор) —
  аналогично, обрабатывается существующим «Please reply to a user message.»

## Верификация

- Тест `test_ro_command_external_reply`: `restrictChatMember` вызван с `user_id=789`
  при `reply_to_message=None` и `external_reply` с `MessageOriginUser` ✓
- Существующий тест `test_ro_command_no_reply` по-прежнему проходит ✓
- 90 тестов в `test_admin_core.py` — все зелёные ✓
