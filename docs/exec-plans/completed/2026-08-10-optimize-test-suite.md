# optimize-test-suite: ускорить тесты и удалить доказанные дубли

## Контекст
- Полный набор содержит 855 тестов и выполняется примерно за 107 секунд.
- 406 тестов вне `tests/routers/` выполняются за 3.27 секунды; основная задержка находится в router-тестах.
- `aiogram.client.session.aiohttp.AiohttpSession.close()` всегда ждёт 0.25 секунды для graceful shutdown SSL, хотя тестовый Telegram API работает по обычному локальному HTTP.
- `router_bot` создаётся и закрывается для каждого теста, поэтому техническая пауза повторяется сотни раз и почти полностью объясняет длительность прогона.
- В `tests/integration/test_clean_architecture.py` найдены четыре теста `FakeStellarSDK`, размещённые вне канонического файла контрактов, и два малоценных композиционных теста без дополнительного поведения. Независимое ревью подтвердило, что сценарий накопления нескольких XDR уникален; его покрытие перенесено в канонический тест `tests/test_protocol_fakes.py`.

## План изменений
1. [x] В `tests/test_protocol_fakes.py` добавить RED-тест helper-функции быстрого закрытия тестовой Aiogram HTTP-сессии: реальный underlying `aiohttp.ClientSession` должен закрываться без вызова `AiohttpSession.close()` и его SSL-паузы.
2. [x] Запустить целевой тест и подтвердить ожидаемое падение из-за отсутствующего helper.
3. [x] В `tests/conftest.py` добавить test-only helper для закрытия underlying HTTP client session и использовать его в teardown `router_bot`; mock Telegram server и реальный `AiohttpSession` оставить без подмены внешней границы.
4. [x] Запустить целевой router-тест с `--durations` и подтвердить исчезновение teardown-задержки 0.25 секунды.
5. [x] Запустить полный pytest, сравнить время с baseline 107 секунд и проверить отсутствие утечек состояния/незакрытых сессий.
6. [x] В `justfile` добавить:
   - `test-fast` для `tests --ignore=tests/routers`;
   - `test-router` для `tests/routers`;
   - существующий `test` оставить полным и обязательным для CI/push.
7. [x] Проверить обе новые Just-команды и зафиксировать количество прошедших тестов: `test-fast` — 401 за 2.59s, `test-router` — 449 за 16.00s.
8. [x] В `tests/integration/test_clean_architecture.py` удалить дублированное размещение тестов `FakeStellarSDK` и два тривиальных `TestServiceInteraction`; сохранить уникальные тесты production-сервисов и перенести проверку накопления нескольких XDR в канонический контрактный тест.
9. [x] В `tests/test_protocol_fakes.py` оставить каноническое покрытие fake-контрактов и новый тест инфраструктурного helper.
10. [x] Запустить `uv run ruff format --check .`, `just lint`, `just types`, `just test` и `just secrets`.
11. [x] Перенести план в `docs/exec-plans/completed/` и отметить выполненные пункты.

## Риски и открытые вопросы
- Helper использует внутреннюю client session Aiogram, потому что публичный `close()` намеренно содержит SSL-паузу. Доступ к private-атрибуту должен быть локализован в одном test-only helper и проверен тестом.
- Быстрое закрытие допустимо только для локального HTTP mock server; production-код и HTTPS-сессии не затрагиваются.
- Нельзя заменять Telegram/Stellar/Grist локальными fake-клиентами: внешние вызовы по-прежнему должны идти через mock servers из `tests/conftest.py`.
- Удаление тестов ограничено подтверждёнными дублями. Большие router-наборы и отрицательные проверки прав доступа не удаляются ради уменьшения счётчика.
- Разделение команд предназначено для локальной обратной связи; CI продолжает запускать полный `just test`/`pytest`.

## Верификация
- Baseline: `uv run pytest -q --durations=50` → 855 passed примерно за 107 секунд, teardown router-тестов по 0.25 секунды.
- Целевой teardown: `uv run pytest -q tests/routers/test_stellar.py::test_fee_command --durations=10` — в списке durations не должно быть паузы 0.25 секунды.
- Быстрый набор: `just test-fast` — ожидается около 400 тестов за несколько секунд.
- Router-набор: `just test-router` — все router-тесты проходят без повторяющейся teardown-паузы.
- Полная регрессия: `uv run ruff format --check . && just lint && just types && just test && just secrets`.
- Проверить отсутствие `Unclosed client session`, `Unclosed connector` и утечки записей `mock_telegram` между тестами.
