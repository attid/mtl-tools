import pytest
from aiogram import Dispatcher
from routers.start_router import router as start_router
from tests.conftest import RouterTestMiddleware, create_message_update

@pytest.fixture(autouse=True)
def cleanup_router():
    """Ensure router is detached after each test."""
    yield
    if start_router.parent_router:
        start_router._parent_router = None

@pytest.mark.asyncio
async def test_start_command(mock_server, router_app_context):
    """
    Test /start command.
    """
    # 1. Setup
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(start_router)
    
    # 2. Simulate Input
    # We rely on RouterTestMiddleware to inject a mock session, 
    # so db_save_bot_user will run against that mock.
    await dp.feed_update(
        router_app_context.bot, 
        create_message_update(123, "/start")
    )
    
    # 3. Verify Output
    # Check that the bot sent the correct message via mock_server
    req = next((r for r in mock_server.get_requests() if r["method"] == "sendMessage" and "/start" not in r["data"].get("text", "")), None)
    # Note: we filter out the command itself if it was somehow echoed, but mainly we look for the response
    
    # Actually, we should look for the last sendMessage
    # The /start handler replies with "Привет, я бот из"
    
    # Get all sendMessage requests
    messages = [r for r in mock_server.get_requests() if r["method"] == "sendMessage"]
    assert len(messages) > 0
    last_message = messages[-1]
    
    assert "Привет, я бот из" in last_message["data"]["text"]
    
    # Verify session usage if needed (optional, effectively white-box testing)
    # Since we can't easily access the middleware-created session from here unless we captured it,
    # we assume "no exception" means it worked. 
    # If we wanted to verify db_save_bot_user called commit, we'd need to capture the session in the middleware.

@pytest.mark.asyncio
async def test_links_command(mock_server, router_app_context):
    """
    Test /links command.
    """
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(start_router)
    
    await dp.feed_update(
        router_app_context.bot, 
        create_message_update(123, "/links")
    )
    
    messages = [r for r in mock_server.get_requests() if r["method"] == "sendMessage"]
    assert len(messages) > 0
    assert "Полезные ссылки" in messages[-1]["data"]["text"]

@pytest.mark.asyncio
async def test_emoji_command_no_args(mock_server, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(start_router)

    await dp.feed_update(
        router_app_context.bot, 
        create_message_update(123, "/emoji")
    )

    messages = [r for r in mock_server.get_requests() if r["method"] == "sendMessage"]
    assert len(messages) > 0
    assert "Используйте: /emoji" in messages[-1]["data"]["text"]

@pytest.mark.asyncio
async def test_emoji_command_reaction(mock_server, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(start_router)

    await dp.feed_update(
        router_app_context.bot, 
        create_message_update(123, "/emoji https://t.me/123/456 👀")
    )

    # Verify reaction was set
    reactions = [r for r in mock_server.get_requests() if r["method"] == "setMessageReaction"]
    assert len(reactions) > 0
    assert int(reactions[-1]["data"]["message_id"]) == 456
    
    # Verify confirmation message
    messages = [r for r in mock_server.get_requests() if r["method"] == "sendMessage"]
    assert len(messages) > 0
    assert "Реакция 👀 добавлена" in messages[-1]["data"]["text"]

@pytest.mark.asyncio
async def test_save_command_admin(mock_server, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(start_router)
    
    # Mock admin ID check. In start_router.py it checks MTLChats.ITolstov.
    # We can't easily patch the constant without patch(), but we can assume the code uses the constant.
    # MTLChats.ITolstov is imported.
    # We can try to match the ID if we know it (84131737 from previous test).
    
    await dp.feed_update(
        router_app_context.bot, 
        create_message_update(84131737, "/save")
    )

    messages = [r for r in mock_server.get_requests() if r["method"] == "sendMessage"]
    assert len(messages) > 0
    assert messages[-1]["data"]["text"] == "Готово"

@pytest.mark.asyncio
async def test_link_command_reply_with_addresses(mock_server, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(start_router)

    addr1 = "G" + "A" * 55
    addr2 = "G" + "B" * 55
    reply_text = f"addr {addr1} other {addr2} {addr1}"

    # Construct update manually to include reply_to_message
    from aiogram import types
    import datetime
    
    update = types.Update(
        update_id=11,
        message=types.Message(
            message_id=11,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='supergroup'),
            from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
            text="/link",
            reply_to_message=types.Message(
                message_id=10,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup'),
                from_user=types.User(id=888, is_bot=False, first_name="User2", username="user2"),
                text=reply_text
            )
        )
    )

    await dp.feed_update(router_app_context.bot, update)

    messages = [r for r in mock_server.get_requests() if r["method"] == "sendMessage"]
    assert len(messages) > 0
    assert "viewer.eurmtl.me" in messages[-1]["data"]["text"]
