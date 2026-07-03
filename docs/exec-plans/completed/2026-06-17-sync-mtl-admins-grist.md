# 2026-06-17-sync-mtl-admins-grist: синхронизация MTL админов в Grist

## Контекст
- Нужна команда `/sync_mtl_admins` для skynet admins.
- Команда должна заполнить Grist-документ `5cA6v1wpuVWtkBXXuXKZpb`, таблицу `MTL_Admins`, на основании Telegram-админов строк из таблицы `Media`.
- Read-only проверка доступа уже выполнена локально:
  - `MTL_Admins`: 87 строк.
  - `Media`: 147 строк.
- Целевые поля `MTL_Admins`: `Username`, `As_Owner`, `As_Admin`, `Up_to_Date`.
- В `Media` появилось поле `TgId`, его нужно использовать как основной надежный Telegram chat/channel id.
- `As_Owner` и `As_Admin` — Grist reference lists на `Media`; API возвращает и принимает формат `["L", <row_id>, ...]`.
- Для topic admins целевая запись идет через `MTLA_Agora_Team.Topics_From_SkyNet`.
- `MTLA_Agora_Topics.Topic_Id` — formula из последнего сегмента `Link`; для записи нужно искать строки topics по вычисленному `Topic_Id`/`Link`.

## Согласованный контракт
1. Команда: `/sync_mtl_admins`.
2. Доступ: только skynet admins.
3. Источник медиа: Grist table `Media` в doc `5cA6v1wpuVWtkBXXuXKZpb`.
4. Обрабатывать Telegram media:
   - строки с `Platform == "Telegram"`;
   - использовать только `Media.TgId` как Telegram target;
   - `Url` и `Invite` не использовать для Bot API, потому что это ненадежно и не будет работать для нужного сценария.
5. Для каждой пригодной Telegram media попытаться получить Telegram admins через Bot API.
6. Creator записывается в `As_Owner`.
7. Administrator записывается в `As_Admin`.
8. Если найденный admin/owner с username отсутствует в `MTL_Admins`, создать новую строку `Username="@username"`.
9. У найденных/созданных/обновленных админов поставить `Up_to_Date=True`.
10. Пользователей, которых команда не трогала, не менять.
11. Полная синхронизация для refs:
    - для найденных/обновленных админов `As_Owner` и `As_Admin` должны стать ровно актуальными media refs из Telegram;
    - старые refs, которых больше нет в Telegram, удалить.
12. Topic admins синхронизировать из SkyNet config в `MTLA_Agora_Team.Topics_From_SkyNet`.
13. Admins без username не создавать; включать в отчет.
14. Media, где бот не админ/не в чате/не смог получить admins/не смог резолвить chat, включать в отчет.
15. Topic admins, для которых нет `MTL_Admins` record или нет matching topic в `MTLA_Agora_Topics`, включать в отчет.
16. Отчет отправлять ответом в чат, где вызвали команду, кусками до 4000 символов.

## План изменений

### 1. Добавить Grist table configs
- Изменить: `other/grist_tools.py`.
- Добавить в `MTLGrist`:
  - `MTL_ADMINS = GristTableConfig("5cA6v1wpuVWtkBXXuXKZpb", "MTL_Admins")`
  - `MTL_ADMINS_MEDIA = GristTableConfig("5cA6v1wpuVWtkBXXuXKZpb", "Media")`
  - `MTL_ADMINS_AGORA_TEAM = GristTableConfig("5cA6v1wpuVWtkBXXuXKZpb", "MTLA_Agora_Team")`
  - `MTL_ADMINS_AGORA_TOPICS = GristTableConfig("5cA6v1wpuVWtkBXXuXKZpb", "MTLA_Agora_Topics")`
- Не менять существующие таблицы.

### 2. Создать сервис синхронизации
- Создать: `services/mtl_admins_sync_service.py`.
- Ответственность сервиса:
  - загрузить `Media` и `MTL_Admins`;
  - загрузить `MTLA_Agora_Team` и `MTLA_Agora_Topics` для topic admins;
  - нормализовать usernames (`@` + lowercase для lookup, исходное `@username` для записи);
  - отфильтровать Telegram media;
  - резолвить Telegram target только из `TgId`;
  - вызвать `bot.get_chat_administrators(...)`;
  - собрать owner/admin refs по `Media.id`;
  - собрать topic admin refs по `MTLA_Agora_Topics.id`;
  - создать отсутствующие `MTL_Admins` records;
  - patch существующих и новых `MTL_Admins` records;
  - patch/create `MTLA_Agora_Team` records для `Topics_From_SkyNet`;
  - вернуть structured result для отчета.
- Предложенные dataclasses:
  - `MediaRecord(id: int, name: str, tg_id: int | None, url: str | None, invite: str | None, platform: str | None, type: str | None, status: str | None)`
  - `AdminRefs(username: str, owner_media_ids: set[int], admin_media_ids: set[int])`
  - `TopicAdminRefs(username: str, topic_ids: set[int])`
  - `SyncIssue(kind: str, media_id: int | None, media_name: str | None, detail: str)`
  - `MtlAdminsSyncResult(created: int, updated: int, team_created: int, team_updated: int, media_checked: int, media_skipped: int, topics_checked: int, issues: list[SyncIssue])`

### 3. Резолвинг Telegram media
- В сервисе сделать pure helper:
  - numeric `Media.TgId` -> `int(chat_id)`.
- `Url` и `Invite` не читать для резолвинга Telegram target.
- Для нерезолвимых invite/private строк добавить issue:
  - `kind="missing_tgid"`
  - detail: нужен `Media.TgId`.

### 4. Telegram admins collection
- Для каждого resolved target вызвать `await bot.get_chat_administrators(target)`.
- Обработать:
  - `TelegramForbiddenError`: bot not in chat / no access.
  - `TelegramBadRequest`: invalid target, private invite, chat not found, not enough rights.
  - generic exception: issue с типом ошибки, но команда не должна падать целиком.
- Если target был взят из `Media.TgId` и Telegram API не дал получить admins, issue должен быть человекочитаемым:
  - `чат <TgId> недоступен`
  - пример: `чат 3256 недоступен`.
- Для каждого `ChatMemberAdministrator`/`ChatMemberOwner`:
  - если `admin.user.username` пустой: добавить issue `admin_without_username`, не создавать record.
  - status `creator` -> owner ref.
  - status `administrator` -> admin ref.
- Если один username и owner, и admin в разных media, обе ref lists заполняются независимо.

### 4.1. Topic admins collection
- Источник SkyNet topic admins:
  - `app_context.admin_service.get_all_topic_admins()`;
  - формат ключей: `"chat_id-thread_id"` -> list usernames.
- Для текущей реализации синхронизировать только topics, которые можно сопоставить с `MTLA_Agora_Topics`:
  - `thread_id` из SkyNet key должен совпасть с `MTLA_Agora_Topics.Topic_Id`;
  - если `Topic_Id` не приходит из API как formula field, вычислить из `Link.rsplit("/", 1)[-1]`.
- Для username topic admin:
  - нормализовать username;
  - найти/создать `MTL_Admins` record так же, как для обычных admins;
  - найти или создать `MTLA_Agora_Team` row, где `Username` reference указывает на `MTL_Admins.id`;
  - выставить `Topics_From_SkyNet` как полный актуальный ref list topics для этого username.
- Не трогать `Agreed_Topics`, `Asked`, `Confirms`, `Role`, `Changes`.
- Если username отсутствует, topic не найден, или есть дубли `MTLA_Agora_Team` для одного `Username`, добавить issue и пропустить опасный patch.

### 5. Полная синхронизация refs для затронутых админов
- Сформировать множество `touched_usernames` из собранных Telegram admins.
- Загрузить существующие `MTL_Admins`.
- Для каждого `touched_username`:
  - найти существующую строку по lowercase username без `@`;
  - если нет — `POST` новую строку с `Username="@username"`, `Up_to_Date=True`;
  - если есть — подготовить patch.
- Поля patch:
  - `As_Owner`: `["L", *sorted(owner_media_ids)]`, либо `["L"]` если owner refs нет.
  - `As_Admin`: `["L", *sorted(admin_media_ids)]`, либо `["L"]` если admin refs нет.
  - `Up_to_Date`: `True`.
- Не трогать записи вне `touched_usernames`.
- Важный edge case: если username есть в Grist дублем (`Lowercase_Username` не уникален), не patchить молча; добавить issue `duplicate_admin_record` и пропустить username, чтобы не записать не туда.

### 5.1. Полная синхронизация `Topics_From_SkyNet`
- Сформировать `topic_touched_usernames` из SkyNet topic admins.
- Для каждого такого username подготовить полный список topic record ids.
- Если у username нет `MTLA_Agora_Team` row:
  - создать row с `Username=<MTL_Admins.id>` и `Topics_From_SkyNet=["L", ...]`.
- Если row есть:
  - patch только `Topics_From_SkyNet`.
- Если username был найден в `MTLA_Agora_Team`, но теперь для него нет SkyNet topic topics, и он входит в `topic_touched_usernames`, выставить `Topics_From_SkyNet=["L"]`.
- Не менять `MTLA_Agora_Team` rows для usernames, которых текущая команда не трогала.

### 6. Grist writes
- Использовать существующий `grist_manager.post_data(...)` и `grist_manager.patch_data(...)`.
- Для создания новых records payload:
  ```json
  {
    "records": [
      {"fields": {"Username": "@username", "Up_to_Date": true}}
    ]
  }
  ```
- Для patch payload:
  ```json
  {
    "records": [
      {
        "id": 123,
        "fields": {
          "As_Owner": ["L", 1, 2],
          "As_Admin": ["L", 3],
          "Up_to_Date": true
        }
      }
    ]
  }
  ```
- Если Grist API не возвращает created IDs из `post_data`, после создания перезагрузить `MTL_Admins` и резолвить новые IDs повторно перед patch refs.
- Для `MTLA_Agora_Team` create payload:
  ```json
  {
    "records": [
      {
        "fields": {
          "Username": 123,
          "Topics_From_SkyNet": ["L", 10, 11]
        }
      }
    ]
  }
  ```
- Для `MTLA_Agora_Team` patch payload:
  ```json
  {
    "records": [
      {
        "id": 456,
        "fields": {
          "Topics_From_SkyNet": ["L", 10, 11]
        }
      }
    ]
  }
  ```
- Не использовать `PUT` для всей таблицы, чтобы не потерять поля, которые команда не должна менять.

### 7. Команда `/sync_mtl_admins`
- Рекомендуемый файл: новый router `routers/mtl_admins_sync.py`, чтобы не раздувать `routers/admin_system.py`.
- Добавить `register_handlers(dp, bot)` в новом router; dynamic loader в `start.py` подхватит файл автоматически.
- Handler:
  - проверяет `skyuser.is_skynet_admin()`;
  - отвечает “Синхронизация началась...”;
  - создает/получает `MtlAdminsSyncService`;
  - вызывает sync;
  - форматирует отчет;
  - отправляет отчет chunks до 4000 символов через `message.reply`/`message.answer`.
- Не запускать команду автоматически по расписанию.

### 8. Формат отчета
- Пример:
  ```text
  MTL admins sync completed.
  Media checked: 47
  Media skipped: 65
  Admin records created: 3
  Admin records updated: 24
  Agora team records created: 1
  Agora team records updated: 4

  Problems:
  - Media #16 MTL - shareholders: missing TgId.
  - Media #13 EURMTL ...: admin id=123456 has no username.
  - Media #71 MTL admins: bot has no access.
  - Topic 59558: no matching MTLA_Agora_Topics row.
  ```
- Если проблем нет, явно написать `Problems: none`.
- Для HTML parse mode экранировать user-provided text через `html.escape`.

### 9. Тесты сервиса
- Создать: `tests/services/test_mtl_admins_sync_service.py`.
- Использовать общие mock servers из `tests/conftest.py`: `mock_telegram`, `mock_grist`, реальный `GristAPI`, реальный aiogram `Bot`.
- Не добавлять локальные `FakeBot`/`FakeGristManager` для внешних boundaries.
- Тесты:
  1. `test_uses_media_tgid_as_only_telegram_target`
  2. `test_url_and_invite_are_ignored_for_telegram_target`
  3. `test_missing_tgid_is_reported`
  4. `test_collects_owner_and_admin_refs_by_username`
  5. `test_skips_admin_without_username_and_reports_issue`
  6. `test_creates_missing_admin_records`
  7. `test_patches_full_owner_and_admin_reference_lists_for_touched_users`
  8. `test_duplicate_admin_records_are_reported_and_not_patched`
  9. `test_forbidden_media_is_reported_without_failing_sync`
  10. `test_collects_topic_admins_into_agora_team_topics_from_skynet`
  11. `test_missing_agora_topic_is_reported`
  12. `test_duplicate_agora_team_rows_are_reported_and_not_patched`
- TDD requirement:
  - сначала написать failing test;
  - запустить targeted pytest и увидеть RED;
  - затем минимальная реализация;
  - снова targeted pytest GREEN.

### 10. Тесты router/command
- Создать или изменить: `tests/routers/test_mtl_admins_sync.py`.
- Проверить:
  1. non-skynet admin получает отказ.
  2. skynet admin запускает сервис.
  3. длинный отчет режется на несколько сообщений <= 4000 символов.
  4. отчет экранирует HTML из Grist media names/usernames.
- Для Grist boundaries следовать `docs/conventions.md#tests`: если тест реально проверяет Grist HTTP boundary, использовать `mock_grist`; для чистого command test лучше подменить сервис fake-объектом.

### 11. Возможное подключение через DI
- Если сервис без состояния, можно создавать его в handler-е:
  ```python
  service = MtlAdminsSyncService(grist_manager=grist_manager)
  ```
- Если нужен DI:
  - изменить `services/app_context.py`;
  - добавить поле `mtl_admins_sync_service`;
  - инициализировать в `create_app_context`.
- Рекомендация на первую реализацию: не расширять DI без необходимости; сервис stateless, проще передавать зависимости напрямую в router.

### 12. Коммит-стратегия
- Коммит 1: `feat(grist): add mtl admins sync service`
  - `other/grist_tools.py`
  - `services/mtl_admins_sync_service.py`
  - `tests/services/test_mtl_admins_sync_service.py`
- Коммит 2: `feat(admins): add mtl admins sync command`
  - `routers/mtl_admins_sync.py`
  - `tests/routers/test_mtl_admins_sync.py`
  - completed execution plan.

## Риски и открытые вопросы
- Telegram URL/invite links не использовать для Bot API target; такие Media попадут в отчет, пока в Grist нет `TgId`.
- У многих Telegram rows в `Media` может быть пустой `TgId`; их нужно явно репортить.
- `Media.TgId` numeric в Grist может прийти как `float`; при чтении нужно безопасно приводить к `int`, но только если значение целое.
- Если бот не состоит в чате или не имеет доступа к admins, Telegram вернет Forbidden/BadRequest; это должно быть отчетом, не падением команды.
- Если `MTL_Admins` содержит дубликаты username, автоматический patch опасен. Нужно репортить и пропускать.
- Если `MTLA_Agora_Team` содержит несколько rows для одного `Username`, автоматический patch `Topics_From_SkyNet` опасен. Нужно репортить и пропускать.
- `MTLA_Agora_Topics.Topic_Id` — formula; если Grist API не вернет это поле, придется вычислять topic id из `Link`.
- `As_Owner`/`As_Admin` reverse fields в Grist могут пересчитываться с обеих сторон. План патчит `MTL_Admins` напрямую, потому что пользователь явно просит заполнять именно `MTL_Admins`.
- Большой отчет может превысить лимит Telegram; обязательно chunking <= 4000 символов.
- Команда может занять заметное время из-за десятков Telegram API calls; при реализации стоит рассмотреть короткий progress message и последовательный сбор без агрессивного parallelism, чтобы не удариться в rate limits.

## Верификация
- Unit:
  - `uv run pytest tests/services/test_mtl_admins_sync_service.py -q`
  - `uv run pytest tests/routers/test_mtl_admins_sync.py -q`
- Existing relevant tests:
  - `uv run pytest tests/routers/test_admin_system.py tests/routers/test_multi_handler.py -q`
- Quality:
  - `uv run ruff format --check .`
  - `just lint`
  - `just types`
  - `just test`
- Manual dry-run before production write:
  - добавить в сервис временный/test-only dry-run режим или CLI/debug entrypoint, который строит отчет без `post_data/patch_data`;
  - проверить количество resolvable/unresolvable Media;
  - только после этого разрешать write path.
- Manual production check:
  - вызвать `/sync_mtl_admins` skynet admin-ом;
  - убедиться, что команда отвечает отчетом;
  - открыть Grist `MTL_Admins`;
  - проверить, что найденные admins получили актуальные `As_Owner`, `As_Admin`, `Up_to_Date=True`;
  - проверить, что admins без username и недоступные media перечислены в отчете.

## Выполнение
- [x] Добавлены Grist configs для `MTL_Admins`, `Media`, `MTLA_Agora_Team`, `MTLA_Agora_Topics`.
- [x] Добавлен `MtlAdminsSyncService`.
- [x] Реализован резолвинг Telegram target только через `Media.TgId`; `Url`/`Invite` не используются.
- [x] Реализована полная синхронизация `As_Owner`, `As_Admin`, `Up_to_Date` для затронутых admins.
- [x] Реализована синхронизация topic admins в `MTLA_Agora_Team.Topics_From_SkyNet` по `Topic_Id`.
- [x] Добавлена команда `/sync_mtl_admins` только для skynet admins.
- [x] Отчет режется на части до 4000 символов.
- [x] Сервисные тесты переведены на `mock_telegram`/`mock_grist`, без локальных fake-классов для Telegram/Grist boundaries.
- [x] В `mock_grist` добавлен PATCH records endpoint.
- [x] Duplicate `MTL_Admins.Username` и duplicate `MTLA_Agora_Team.Username` репортятся без опасного create/patch.

## Проверка
- `uv run pytest tests/services/test_mtl_admins_sync_service.py tests/routers/test_mtl_admins_sync.py -q` -> 12 passed.
- `uv run pyright services/mtl_admins_sync_service.py routers/mtl_admins_sync.py` -> 0 errors.
- `uv run ruff format --check other/grist_tools.py services/mtl_admins_sync_service.py routers/mtl_admins_sync.py tests/services/test_mtl_admins_sync_service.py tests/routers/test_mtl_admins_sync.py tests/conftest.py` -> formatted.
- `uv run ruff check other/grist_tools.py services/mtl_admins_sync_service.py routers/mtl_admins_sync.py tests/services/test_mtl_admins_sync_service.py tests/routers/test_mtl_admins_sync.py tests/conftest.py` -> all checks passed.
- `uv run pytest -q` -> 823 passed.
