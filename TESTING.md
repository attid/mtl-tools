# Testing Guidelines

This project enforces testing standards to ensure maintainability, reliability, and ease of debugging.

## Core Principles

1.  **Router coverage**: Для ключевых роутеров добавлять тесты в `tests/routers/` (минимум позитивный сценарий на хендлер).
2.  **DI first**: Зависимости передаются через `app_context`, моки настраиваются через `tests/fakes.py` и fixtures.
3.  **External boundaries**: Внешние вызовы (Telegram/HTTP) мокать; внутреннюю бизнес‑логику тестировать через сервисы.
4.  **Тонкие хендлеры**: Сложную логику выносить в `services/` или `other/` и тестировать там.

## Mocking Strategy

### External Services
-   **Telegram**: Use mock bot/dispatcher helpers from tests (see `tests/` fixtures). Проверяйте исходящие запросы через лог/коллекцию моков.
-   **Stellar/Horizon**: Мокать сетевые вызовы и состояния (если тестируется Stellar‑часть).
-   **HTTP/внешние API**: Использовать `AsyncMock` и явные фикстуры.

### Internal Components
-   **Repositories**: Использовать fake‑реализации или моки через `app_context`/service adapters.
-   **Services**: Мокать на уровне `app_context` или через `tests/fakes.py`.

## Test Structure

### Fixtures
-   `router_app_context`: основной фикстурный `AppContext` для роутеров.
-   `mock_telegram`: проверка исходящих сообщений/запросов.
-   `tests/fakes.py`: базовые фейки сервисов/контекста.

### Example Test Pattern

```python
async def test_cmd_balance(mock_telegram, mock_horizon, router_app_context):
    # 1. Configure External State (Horizon)
    mock_horizon.set_account(
        "GUSER", 
        balances=[{"asset_type": "native", "balance": "100.0"}]
    )

    # 2. Configure Internal State (Repositories/Context)
    # (Assuming helper setup_user exists)
    setup_user(router_app_context, user_id=123, wallet="GUSER")

    # 3. Simulate Input (Telegram Update)
    dp = router_app_context.dispatcher
    dp.include_router(my_router)
    await dp.feed_update(router_app_context.bot, create_message_update(123, "/balance"))

    # 4. Verify Output (Telegram Messages)
    # Check that the bot sent the correct message
    requests = mock_horizon.get_requests() # Optional: verify Horizon calls
    messages = [r for r in mock_telegram if r['method'] == 'sendMessage']
    assert "100.0 XLM" in messages[-1]['data']['text']
```

## Database Tests

We use `db/repositories/` + `DatabaseService` with SQLite for unit tests.

### Running Tests

To run the database unit tests:

```bash
uv run pytest tests/db/
```

### Test Coverage

1.  **Repositories (`tests/db/`)**: Config/Chats repository сценарии.
2.  **Service Layer (`tests/db/test_database_service.py`)**: делегирование и коммиты.
