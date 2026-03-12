# 2026-03-12-show-topic-admin-access: доступ `/show_topic_admin` для topic-admin

## Контекст
- Команда `/show_topic_admin` сейчас не работает для topic-admin, потому что в `routers/multi_handler.py` универсальный permission-gate требует `skyuser.is_admin()`.
- По согласованной спецификации topic-admin должен иметь право только на просмотр списка админов своего топика; выдача и отзыв роли topic-admin остаются у chat-admin/skynet-admin.

## План изменений
1. [x] Добавить регрессионные тесты в `tests/routers/test_multi_handler.py` для `/show_topic_admin` и ограничений на `/add_topic_admin`/`/del_topic_admin`.
2. [x] Подтвердить RED-состояние запуском точечных `pytest`-сценариев.
3. [x] Внести минимальную правку в `routers/multi_handler.py`, разрешив `/show_topic_admin` для topic-admin текущего треда без расширения прав других команд.
4. [x] Прогнать целевые тесты и убедиться, что новая авторизация не ломает текущие ограничения.
5. [x] Перенести план в `docs/exec-plans/completed/` с отмеченными чекбоксами.

## Риски и открытые вопросы
- Специальный case в универсальном хендлере нельзя сделать слишком широким, иначе можно случайно открыть доступ к другим `admin`-командам.
- Проверка topic-admin зависит от `username`; пользователь без username не должен получить неявный доступ.

## Верификация
- Воспроизвести сценарий через router-тест: пользователь, указанный в topic admins текущего треда, вызывает `/show_topic_admin` и получает список.
- Проверить негативный сценарий: не-topic-admin получает отказ на `/show_topic_admin`.
- Проверить, что `/add_topic_admin` и `/del_topic_admin` по-прежнему недоступны topic-admin без chat-admin прав.
