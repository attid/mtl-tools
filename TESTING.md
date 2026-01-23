# Testing Guidelines

This project enforces strict testing standards to ensure maintainability, reliability, and ease of debugging.

## Core Principles

1.  **1:1 Router-Test Mapping**: Every router file in `routers/` must have a corresponding test file in `tests/routers/`. For example, `routers/start.py` -> `tests/routers/test_start.py`.
2.  **No Patches**: The use of `unittest.mock.patch` (including `@patch`, `with patch`, etc.) is **strictly prohibited**. All dependencies must be injectable.
3.  **Dependency Injection (DI)**: Use the `app_context` to inject dependencies (services, repositories, bots) into handlers and routers. Tests should configure mocks on the `app_context`.
4.  **End-to-End Flow**: Tests should simulate the full flow of handling an update, from the `Dispatcher` down to the handler, without mocking internal calls within the flows (unless absolutely necessary for external boundaries).
5.  **Full Coverage**: Every handler in a router must have at least one positive test case.

## Mocking Strategy

### External Services
-   **Telegram**: Use `aiogram.client.telegram.TelegramAPIServer` and `MockBot`/`MockDispatcher` infrastructure (provided in `conftest.py`) to simulate Telegram interactions. verify outgoing requests by inspecting the `mock_server` request log.
-   **Horizon (Stellar)**: Use `MockHorizon` (provided in `conftest.py`) to simulate the Stellar network. Configure account states, offers, and transaction responses directly on the mock before running the test. **Do not mock `StellarService` methods unless testing the service itself.**
-   **Grist**: Use `MockGrist` (provided in `conftest.py`) to simulate Grist database interactions.

### Internal Components
-   **Repositories**: Mock repositories at the `IRepositoryFactory` level. Create mock repository objects with `AsyncMock`/`MagicMock` methods and assign them to `app_context.repository_factory.get_X_repository`.
-   **Services**: Mock internal services (e.g., `LocalizationService`, `EncryptionService`) at the `app_context` level.

## Test Structure

### Fixtures
-   `router_app_context`: The primary fixture for router tests. It provides a fully configured `AppContext` with a real `StellarService` connected to `MockHorizon`, a real `Bot` connected to `MockTelegram`, and mocked repositories/internal services.
-   `mock_horizon`: Use this to configure Stellar network state (balances, accounts, etc.).
-   `mock_telegram`: Use this to inspect messages sent by the bot.

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

We have migrated from a monolithic `db/requests.py` to a Repository Pattern in `db/repositories/`. 
Tests have been added to verify the new architecture without requiring a live Postgres connection (using in-memory SQLite).

### Running Tests

To run the database unit tests:

```bash
uv run pytest tests/db/
```

### Test Coverage

1.  **Repositories (`tests/db/test_repositories.py`)**:
    *   **ConfigRepository**:
        *   Saving/loading bot values (handling Strings, JSON objects, legacy formats).
        *   Updating dictionary values.
        *   KVStore operations.
    *   **ChatsRepository**:
        *   Creating and updating Chat info.
        *   Managing Chat Members (add/remove).
        *   Tracking joined/left users (filtering by date).

2.  **Service Layer (`tests/db/test_database_service.py`)**:
    *   Verifies that `DatabaseService` correctly delegates calls to repositories.
    *   Ensures sessions are committed.
    *   Mocks `SessionPool` and Repositories to isolate logic.