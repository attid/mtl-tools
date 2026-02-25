# Contract: SkyNet <-> MMWB ping/pong

## Direction
- **Request:** SkyNet -> channel (`#mmwb #skynet command=ping`).
- **Response:** MMWB -> channel (`#skynet #mmwb command=pong`).
- Обработка в SkyNet происходит только для входящего `pong` с правильным направлением.

## Pattern
- Для `pong` обязателен префикс `#skynet #mmwb` и `command=pong`.
- По реализации используется поиск `#skynet\s+#mmwb\s+command=pong` (case-insensitive).
- Любые другие комбинации тегов/команд не обновляют health state.

## Fields
- `command` (required):
  - `ping` для исходящего heartbeat от SkyNet.
  - `pong` для входящего heartbeat-ответа от MMWB.
- Дополнительные поля (например, `status=ok`) допускаются и игнорируются логикой health-check.

## Processing rules
- На валидный `pong` обновляется `bot_state_service.last_pong`.
- `ping` не считается ответом и не обновляет состояние.
- Сообщения с неверным направлением (например, `#mmwb #skynet command=pong`) игнорируются.

## Valid examples
```text
#skynet #mmwb command=pong
#skynet #mmwb command=pong status=ok
```

## Invalid examples
```text
#mmwb #skynet command=pong
#skynet #mmwb command=ping
```

## Verification
- Router behavior covered by `tests/routers/test_monitoring.py::test_monitoring_pong_update`.
