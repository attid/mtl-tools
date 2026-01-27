import json
import pytest
from aiogram import types

from routers.inline import router as inline_router
from tests.conftest import RouterTestMiddleware


@pytest.fixture(autouse=True)
async def cleanup_router():
    yield
    if inline_router.parent_router:
         inline_router._parent_router = None


@pytest.mark.asyncio
async def test_inline_query_returns_commands(mock_telegram, router_app_context):
    """Test that inline query returns registered commands."""
    dp = router_app_context.dispatcher
    dp.inline_query.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(inline_router)

    # Register commands via DI service (the way production code works)
    router_app_context.command_registry.register_command(
        name="/help",
        description="Show help",
        cmd_type=0,
        cmd_list=[]
    )
    router_app_context.command_registry.register_command(
        name="/start",
        description="Start bot",
        cmd_type=0,
        cmd_list=[]
    )

    update = types.Update(
        update_id=1,
        inline_query=types.InlineQuery(
            id="iq1",
            from_user=types.User(id=123, is_bot=False, first_name="Test", username="test"),
            query="help",
            offset=""
        )
    )

    await dp.feed_update(bot=router_app_context.bot, update=update)

    requests = mock_telegram.get_requests()
    ans_req = next((r for r in requests if r["method"] == "answerInlineQuery"), None)
    assert ans_req is not None, "answerInlineQuery should be called"
    results = json.loads(ans_req["data"]["results"])
    assert len(results) == 1, "Should find 1 command matching 'help'"
    assert results[0]["title"] == "Show help"


@pytest.mark.asyncio
async def test_inline_query_empty_when_no_commands(mock_telegram, router_app_context):
    """Test that inline query returns empty when no commands registered."""
    dp = router_app_context.dispatcher
    dp.inline_query.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(inline_router)

    # Don't register any commands - command_registry is empty

    update = types.Update(
        update_id=1,
        inline_query=types.InlineQuery(
            id="iq2",
            from_user=types.User(id=123, is_bot=False, first_name="Test", username="test"),
            query="anything",
            offset=""
        )
    )

    await dp.feed_update(bot=router_app_context.bot, update=update)

    requests = mock_telegram.get_requests()
    ans_req = next((r for r in requests if r["method"] == "answerInlineQuery"), None)
    assert ans_req is not None, "answerInlineQuery should be called even with empty results"
    results = json.loads(ans_req["data"]["results"])
    assert len(results) == 0, "Should return empty when no commands"


@pytest.mark.asyncio
async def test_inline_query_shows_feature_status(mock_telegram, router_app_context):
    """Test that inline query shows feature status icons for chat."""
    dp = router_app_context.dispatcher
    dp.inline_query.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(inline_router)

    chat_id = -1001234567890

    # Register command with cmd_type > 0 (shows status)
    router_app_context.command_registry.register_command(
        name="/set_captcha",
        description="Toggle captcha",
        cmd_type=1,
        cmd_list=["captcha"]
    )

    # Enable captcha for the chat
    router_app_context.feature_flags.enable(chat_id, "captcha")

    # Query with chat_id prefix
    update = types.Update(
        update_id=1,
        inline_query=types.InlineQuery(
            id="iq3",
            from_user=types.User(id=123, is_bot=False, first_name="Test", username="test"),
            query=f"{chat_id} captcha",
            offset=""
        )
    )

    await dp.feed_update(bot=router_app_context.bot, update=update)

    requests = mock_telegram.get_requests()
    ans_req = next((r for r in requests if r["method"] == "answerInlineQuery"), None)
    assert ans_req is not None
    results = json.loads(ans_req["data"]["results"])
    assert len(results) == 1
    # Should show green icon because captcha is enabled
    assert "🟢" in results[0]["title"]
