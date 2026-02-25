# Contract: SkyNet helper events taken/closed

## Direction
- Принимаются только channel-сообщения с направлением `#skynet #helper`.
- Сообщения с обратным направлением (`#helper #skynet`) игнорируются.

## Pattern
- Базовый формат: `#skynet #helper command=<taken|closed> ...`.
- Payload парсится как `key=value` пары, разделенные пробелами.
- Обязательное поле для обеих команд: `url`.

## Fields
### command=taken
- Required: `user_id` (int), `username` (str), `agent_username` (str), `url` (str, может быть percent-encoded).
- Side-effect: вызов `gs_save_new_support(...)`.

### command=closed
- Required: `user_id` (int), `agent_username` (str), `url` (str), `closed=true`.
- Side-effect: вызов `gs_close_support(url=...)`.

## ACK and dedup
- После успешной обработки отправляется ACK:
  - `#helper #skynet command=ack status=ok op=<taken|closed> url=<percent-encoded-url>`
- Дедупликация по ключу `<command>:<decoded_url>`:
  - повторный event -> `status=duplicate` и без повторного side-effect.

## Error/ignore behavior
- Неизвестный `command` -> ignore + warning log.
- Нет `url` -> ignore + warning log.
- Для `closed` без `closed=true` -> ignore + warning log.
- Ошибки парсинга (`KeyError`, `ValueError`) -> ignore + warning log.

## Valid examples
```text
#skynet #helper command=taken user_id=123 username=client1 agent_username=agent1 url=https://t.me/c/2032873651/69621
#skynet #helper command=closed user_id=123 agent_username=agent1 url=https://t.me/c/2032873651/69621 closed=true
```

```text
#skynet #helper command=taken user_id=84131737 username=itolstov agent_username=itolstov url=https%3A%2F%2Ft.me%2Fc%2F1466779498%2F25527
```

## Invalid examples
```text
#helper #skynet command=taken user_id=123 username=client1 agent_username=agent1 url=https%3A%2F%2Ft.me%2Fc%2F1466779498%2F25527
#skynet #helper command=closed user_id=123 agent_username=agent1 url=https://t.me/c/2032873651/69621
```

```text
#skynet #helper command=unknown user_id=1 url=https://t.me/c/1/2
#skynet #helper command=taken user_id=abc username=client1 agent_username=agent1 url=https://t.me/c/2032873651/69621
```

## Verification
- Router behavior covered by:
  - `tests/routers/test_monitoring.py::test_monitoring_helper_taken`
  - `tests/routers/test_monitoring.py::test_monitoring_helper_closed`
  - `tests/routers/test_monitoring.py::test_monitoring_helper_dedup_by_url`
  - `tests/routers/test_monitoring.py::test_monitoring_helper_decodes_url_before_save`
  - `tests/routers/test_monitoring.py::test_monitoring_helper_wrong_direction_ignored`
