# investigate-stellar-guarantor-notification: странное уведомление в GuarantorGroup

## Контекст
- В чат `-1001169382324` пришло уведомление о транзакции с memo `Revert`, содержащее `Payment` и `Clawback` для `25 MP1`.
- В Grist для этого чата настроены две asset-подписки: `EURMTL-GACK...` с порогом `900` и `EURDEBT-GACK...` с порогом `0`.
- Нужно определить, ошибается ли `operations-notifier`, маршрутизация/форматирование в боте или сама конфигурация; если имеющихся данных недостаточно — определить точные точки логирования.

## План изменений
1. [x] Проследить загрузку Grist-конфигурации и построение/синхронизацию подписок в `services/stellar_notification_service.py`.
2. [x] Проследить обработку webhook payload, выбор назначения, дедупликацию и форматирование транзакции.
3. [x] Сопоставить поведение с тестами в `tests/services/test_stellar_notification_service.py` и историей изменений.
4. [x] Проверить доступные факты по указанной Stellar-транзакции и определить, какая операция вызвала подписку.
5. [x] Зафиксировать корневую причину: min-фильтр применяется к XDR после дедупликации; `Clawback` другого актива обходит порог и делает результат непустым.
6. [x] Добавить регрессионный тест и минимальное исправление в разрешённых файлах.
7. [x] Проверка: Ruff format/check, Pyright и 32 релевантных теста успешно пройдены.

## Риски и открытые вопросы
- Текст уведомления показывает всю транзакцию, но сам по себе не показывает операцию, по которой сработала подписка.
- Текущие production-логи и исходный webhook payload могут быть недоступны локально.
- Одна транзакция может затрагивать подписанный аккаунт неочевидно: как source account транзакции, source операции, from/to либо clawback target.
- Подтверждено: webhook пришёл по `Payment 25 EURMTL`, а `Clawback 25 MP1` был добавлен локальным XDR-декодером; notifier не является источником ложного `Clawback`-события.

## Верификация
- Воспроизвести маршрутизацию на payload с несколькими операциями, где подписке соответствует только одна операция.
- Проверить соответствие `subscription_id` записи в `subscriptions_map`, chat/topic и параметрам подписки notifier.
- В логах должны однозначно связываться: `subscription_id`, chat/topic, tx hash, triggering operation id/type и настроенный account/token.
- Регрессионный сценарий: при `min=900`, triggering payment `25 EURMTL` и наличии XDR обработка завершается до дедупликации и `_process_with_xdr`.
- Команды проверки: `uv run ruff format --check ...`, `uv run ruff check ...`, `uv run pyright ...`, `uv run pytest -q tests/services/test_stellar_notification_service.py tests/other/stellar/test_xdr_utils.py`, `git diff --check`.
