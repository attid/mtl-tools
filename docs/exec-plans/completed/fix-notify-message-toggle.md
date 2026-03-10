# fix-notify-message-toggle: /notify_message не переключается (всегда Added)

## Контекст
- Команда `/notify_message` при повторном вызове всегда отвечает "Added" вместо "Removed".
- Причина: `notify_message` отсутствует в `ChatFeatures` dataclass и `FEATURE_TO_ENUM` в `services/feature_flags.py`.
- Из-за этого `is_enabled()` всегда возвращает `False`, и `handle_command` в `routers/multi_handler.py` всегда идёт в ветку "Added".
- Аналогичная проблема в `FakeFeatureFlagsService.FEATURE_KEYS` в `tests/fakes.py`.

## План изменений
1. [x] Добавить `notify_message: bool = False` в `ChatFeatures` dataclass (`services/feature_flags.py:31`)
2. [x] Добавить `"notify_message": BotValueTypes.NotifyMessage` в `FEATURE_TO_ENUM` (`services/feature_flags.py:50`)
3. [x] Добавить `"notify_message"` в `FakeFeatureFlagsService.FEATURE_KEYS` (`tests/fakes.py:878`)
4. [x] Написать тест `test_notify_message_toggle` в `tests/integration/test_clean_architecture.py`
5. [x] `just lint` + `just test` проходят (pyright ошибки в `routers/mic.py` pre-existing)

## Риски и открытые вопросы
- Минимальный риск: изменение затрагивает только добавление в два списка/словаря и один dataclass.
- Существующие тесты не должны сломаться — добавляется новый ключ, не меняется поведение старых.

## Верификация
- `just test` — все тесты зелёные, включая новый тест toggle.
- `just lint` + `just types` — чисто.
- Ручная проверка: `/notify_message` в чате — первый вызов "Added", второй "Removed".
