# AI-FIRST-IT04: Тесты как спецификация контрактов

## Контекст
- В `docs/exec-plans/active/ai-first-100pct-program.md` для Итерации 04 требуется выделить parser/validator и закрепить контрактное поведение тестами.
- Сейчас парсинг payload встроен в `routers/monitoring.py`, что усложняет изолированную проверку граничных случаев.

## План изменений
1. [x] Вынести parser/validator channel contracts в отдельный модуль `other/monitoring_contracts.py`.
2. [x] Подключить новый модуль в `routers/monitoring.py` без изменения публичного поведения.
3. [x] Добавить table-driven unit-тесты parser/validator в `tests/other/test_monitoring_contracts.py`.
4. [x] Добавить/уточнить router-тесты для ACK и error-path веток в `tests/routers/test_monitoring.py`.
5. [x] Запустить профильные тесты и отметить пункты 16-20 в `ai-first-100pct-program.md`.

## Риски и открытые вопросы
- Риск непреднамеренно изменить текущую обработку helper-команд при рефакторинге.
- Риск, что error-path окажутся неявными (игнор без ACK), если не закрепить это тестами.

## Верификация
- Проходит `uv run pytest -q tests/other/test_monitoring_contracts.py tests/routers/test_monitoring.py`.
- Новые unit-тесты покрывают valid/invalid payload и декодирование URL.
- В router-тестах подтверждены ACK для success/duplicate и отсутствие ACK в error-path.
- В `docs/exec-plans/active/ai-first-100pct-program.md` пункты 16-20 отмечены выполненными.
