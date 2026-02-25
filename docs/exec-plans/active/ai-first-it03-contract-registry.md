# AI-FIRST-IT03: Реестр контрактов channel monitoring

## Контекст
- В `docs/exec-plans/active/ai-first-100pct-program.md` Итерация 03 требует формализовать контракты событий.
- Фактическая логика уже реализована в `routers/monitoring.py` и покрыта тестами в `tests/routers/test_monitoring.py`, но спецификация пока не вынесена в `docs/contracts/`.

## План изменений
1. [x] Создать `docs/contracts/README.md` с правилами хранения и версионирования контрактов.
2. [x] Описать контракт `#skynet #mmwb command=ping/pong` в `docs/contracts/skynet-mmwb-ping-pong.md`.
3. [x] Описать контракт `#skynet #helper command=taken/closed` в `docs/contracts/skynet-helper-taken-closed.md`.
4. [x] Добавить в оба контракта примеры valid/invalid payload.
5. [x] Подтвердить верификацию контрактов запуском профильных тестов и отметить пункты 11-15 в основной программе.

## Риски и открытые вопросы
- Риск дрейфа: документация устареет, если изменится regex/валидация в `routers/monitoring.py`.
- Риск неполной спецификации: неочевидные edge-cases (например, percent-encoded URL) могут быть потеряны без явных примеров.

## Верификация
- Существуют файлы `docs/contracts/README.md`, `docs/contracts/skynet-mmwb-ping-pong.md`, `docs/contracts/skynet-helper-taken-closed.md`.
- В контрактах есть разделы с valid/invalid примерами.
- `uv run pytest -q tests/routers/test_monitoring.py` проходит успешно.
- В `docs/exec-plans/active/ai-first-100pct-program.md` пункты 11-15 отмечены как выполненные после проверки.
