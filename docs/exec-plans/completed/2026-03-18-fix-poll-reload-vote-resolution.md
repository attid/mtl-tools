# 2026-03-18-fix-poll-reload-vote-resolution: Fix address resolution in poll_reload_vote

## Контекст
- Команда `/poll_reload_vote` возвращает сокращенные адреса с пометкой "НЕ НАЙДЕН, ВОЗМОЖНО СКАМ" вместо имен из реестров Grist.
- Проблема вызвана тем, что при вызове `address_id_to_username` не передается `grist_manager`, из-за чего поиск в Grist пропускается.

## План изменений
1. [x] Проанализировать `other/stellar/address_utils.py`.
2. [x] Добавить в `address_id_to_username` автоматическое использование глобального `grist_manager`, если он не передан явно.
3. [x] Проверить `services/external_services.py` и при необходимости обновить обертки `address_id_to_username` и `decode_xdr` для поддержки передачи `grist_manager`.
4. [x] Проверить `routers/polls.py` на предмет необходимости явной передачи `grist_manager` (хотя после п.2 это не обязательно, но желательно для явности).
5. [x] Проверка: `just check` (lint, format, types, test).

## Риски и открытые вопросы
- Циклические зависимости при импорте `grist_manager` в `address_utils.py`. (Решено импортом внутри функции).

## Верификация
- Команда `/poll_reload_vote` должна корректно резолвить известные адреса в имена.
- Проверить тесты, связанные с резолвингом адресов.
