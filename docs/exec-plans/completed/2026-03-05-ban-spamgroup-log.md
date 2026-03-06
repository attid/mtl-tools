# ban-spamgroup-log: обязательный SpamGroup-лог для ручных банов

## Контекст
- Ручной бан через интерфейс Telegram не всегда оставляет сообщение в `SpamGroup`.
- Причина по коду: ветка `routers/welcome.py:left_chat_member` отправляет уведомление только для `skyuser.is_skynet_admin()`.

## План изменений
1. [x] Добавить регрессионный тест на `ChatMemberUpdated -> KICKED` от обычного админа чата в `tests/routers/test_welcome.py`.
2. [x] Обновить `routers/welcome.py`, чтобы уведомление о бане в `SpamGroup` отправлялось всегда для ручного `KICKED`.
3. [x] Обновить/добавить тесты.
4. [x] Docs не требуются: меняется только наблюдаемое поведение логирования.
5. [x] Проверка: `uv run pytest tests/routers/test_welcome.py -q`.

## Риски и открытые вопросы
- Ветка `left_chat_member` не должна получить дополнительные блокирующие действия.
- Нужно сохранить существующий формат ban-сообщения и `unban` callback.

## Верификация
- Воспроизвести `chat_member` update с `new_chat_member=ChatMemberBanned`.
- Проверить, что уходит `sendMessage` в `MTLChats.SpamGroup` с `Причина:` и fallback-текстом для ручного бана.
- Прогнать `uv run pytest tests/routers/test_welcome.py -q`.
