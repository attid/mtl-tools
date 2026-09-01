# 2026-08-31-grist-cutover: audited Grist cutover

## Контекст
- Перевести активные и dormant Montelibero bindings на audited документы и новый API root `https://grist.eurmtl.me/api/docs`.
- Сохранить RELY на отдельном host `https://mtl-rely.getgrist.com`, документе `kceNjvoEEihSsc8dQ5vZVB` и отдельном credential path.
- Добавить HTTP mock coverage для активного `chats_info` PUT пути.

## План изменений
1. [x] Обновить Montelibero document IDs и общий Grist API root в `other/grist_tools.py`.
2. [x] Добавить отдельную конфигурацию RELY credential и использовать её только для RELY в `routers/rely_router.py`.
3. [x] Обновить пример runtime-конфигурации в `.env.example` и настройки в `other/config_reader.py`.
4. [x] Обновить mock-сервер и сфокусированные тесты для новых bindings, раздельного RELY пути и `chats_info` PUT.
5. [x] Проверить тесты, lint, types и форматирование.
6. [x] Добавить недостающие Codespaces-generated paths в `.gitignore`, сохранив существующие правила.

## Риски и открытые вопросы
- Новые документы требуют runtime secrets/credentials, которых нет в репозитории.
- RELY credential нельзя молча брать из Montelibero credential, поскольку host и доступ независимы.
- Webhook registrations на стороне внешнего Grist не изменяются этой локальной правкой.
- Binding для `ShareHolders` (`cqmjqbs4e97hbKHyRADQ9N`) в этом репозитории не найден; mapping не добавлялся без соответствующего runtime consumer.

## Верификация
- Проверить все `MTLGrist` configs на audited document IDs и новый API root.
- Проверить HTTP method/path/authorization через `mock_grist` для чтения и PUT.
- Запустить focused pytest, затем `ruff format --check`, `ruff check` и `pyright` для затронутых файлов.
- Результат: focused pytest `24 passed`; full pytest `854 passed`; static checks passed.
