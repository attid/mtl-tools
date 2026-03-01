# mute-mention-unmute: Support @username in /mute and add /unmute

## Контекст
- Пользователь просит поддержку `/mute @username 1d` (по mention), а не только через reply.
- Сейчас `/mute @sadekovtimur 1d` фейлит — парсер duration пытается распарсить `@sadekovtimur` как timedelta.
- `/unmute` не существует — мьюты только истекают по времени.
- При конфликте reply + mention — приоритет mention (явный @username).

## План изменений
1. [x] `other/timedelta.py` — `parse_timedelta_from_message` должна пропускать аргументы начинающиеся с `@` при поиске duration.
2. [x] `routers/admin_core.py` — `cmd_mute`: извлечь @username из entities или аргументов, резолвить через `ChatsRepository.get_user_id()`. Приоритет: mention > reply. Reply остаётся fallback.
3. [x] `routers/admin_core.py` — новый хендлер `/unmute` (тоже поддержка mention + reply).
4. [x] Тесты в `tests/routers/test_admin_core.py` — покрыть сценарии: mute по reply, mute по mention, mute mention+reply (mention wins), unmute по reply, unmute по mention.
5. [x] Проверка: `just lint && just types && just test`.

## Риски и открытые вопросы
- `ChatsRepository.get_user_id("@username")` требует что пользователь уже есть в `bot_users`. Если нет — вернём ошибку "User not found".
- `parse_timedelta_from_message` используется ещё в `!ro` и emoji-reaction — изменение должно быть обратно совместимым.

## Верификация
- `/mute @username 1d` (без reply) → мьютит пользователя.
- `/mute 1d` (reply) → мьютит как раньше.
- `/mute @username 1d` (reply на другого) → мьютит @username (mention wins).
- `/mute 1d` (без reply, без mention) → ошибка "Specify user by reply or @username".
- `/unmute @username` → снимает мьют.
- `/unmute` (reply) → снимает мьют.
- unit-тесты проходят.
