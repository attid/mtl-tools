import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram import Bot, types
from aiogram.enums import ChatMemberStatus
import datetime
import json

from routers.welcome import router as welcome_router, CaptchaCallbackData, JoinCallbackData, emoji_pairs
from tests.conftest import RouterTestMiddleware, TEST_BOT_TOKEN
from other.global_data import global_data, MTLChats, BotValueTypes

@pytest.fixture(autouse=True)
async def cleanup_router():
    yield
    if welcome_router.parent_router:
         welcome_router._parent_router = None
    # Reset global data if needed, though mocks should handle most
    global_data.welcome_messages = {}
    global_data.welcome_button = {}

@pytest.mark.asyncio
async def test_set_welcome_command(mock_server, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(welcome_router)
    
    router_app_context.utils_service.is_admin.return_value = True
    router_app_context.utils_service.sleep_and_delete = AsyncMock()
    
    update = types.Update(
        update_id=1,
        message=types.Message(
            message_id=1,
            date=datetime.datetime.now(),
            chat=types.Chat(id=MTLChats.TestGroup, type='supergroup', title="Test Chat"),
            from_user=types.User(id=999, is_bot=False, first_name="Admin", username="admin"),
            text="/set_welcome Hello $$USER$$"
        )
    )
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    # Verify DB save
    assert router_app_context.config_service.save_bot_value.called
    args = router_app_context.config_service.save_bot_value.call_args[0]
    assert args[0] == MTLChats.TestGroup
    assert args[1] == BotValueTypes.WelcomeMessage
    assert args[2] == "Hello $$USER$$"
    
    # Verify reply
    requests = mock_server.get_requests()
    assert any("Added" in r["data"]["text"] for r in requests if r["method"] == "sendMessage")

@pytest.mark.asyncio
async def test_new_chat_member_welcome(mock_server, router_app_context):
    dp = router_app_context.dispatcher
    dp.chat_member.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(welcome_router)
    
    # Setup global data via direct assignment as router reads it directly in some places or mocks
    # Actually router now uses global_data.welcome_messages directly?
    # Let's check router code.
    # It reads `global_data.welcome_messages`.
    global_data.welcome_messages[MTLChats.TestGroup] = "Welcome $$USER$$!"
    
    # Mocks
    router_app_context.antispam_service.combo_check_spammer.return_value = False
    router_app_context.antispam_service.lols_check_spammer.return_value = False
    router_app_context.group_service.enforce_entry_channel.return_value = (True, None) # membership_ok=True
    router_app_context.config_service.check_user.return_value = 0 # New user
    
    user = types.User(id=123, is_bot=False, first_name="Joiner", username="joiner")
    event = types.ChatMemberUpdated(
        chat=types.Chat(id=MTLChats.TestGroup, type='supergroup', title="Test Chat"),
        from_user=user,
        date=datetime.datetime.now(),
        old_chat_member=types.ChatMemberLeft(user=user),
        new_chat_member=types.ChatMemberMember(user=user)
    )
    
    update = types.Update(update_id=2, chat_member=event)
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    # Verify add user
    assert router_app_context.config_service.add_user_to_chat.called
    
    # Verify welcome message
    requests = mock_server.get_requests()
    assert any("Welcome" in r["data"]["text"] for r in requests if r["method"] == "sendMessage")

@pytest.mark.asyncio
async def test_stop_exchange_command(mock_server, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(welcome_router)
    
    # Mock skynet admin check?
    # is_skynet_admin accesses global_data.
    # We can probably rely on it or mock it if we could.
    # Or just use the global_data patch indirectly or ensure user is skynet admin.
    global_data.skynet_admins = ["@admin"]
    
    router_app_context.stellar_service.stop_all_exchange = MagicMock()
    
    update = types.Update(
        update_id=3,
        message=types.Message(
            message_id=3,
            date=datetime.datetime.now(),
            chat=types.Chat(id=MTLChats.TestGroup, type='supergroup', title="Test Chat"),
            from_user=types.User(id=999, is_bot=False, first_name="Admin", username="admin"),
            text="/stop_exchange"
        )
    )
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    assert router_app_context.stellar_service.stop_all_exchange.called
    requests = mock_server.get_requests()
    assert any("Was stop" in r["data"]["text"] for r in requests if r["method"] == "sendMessage")

@pytest.mark.asyncio
async def test_join_request(mock_server, router_app_context):
    dp = router_app_context.dispatcher
    dp.include_router(welcome_router)
    
    global_data.notify_join[MTLChats.TestGroup] = "123456"
    
    update = types.Update(
        update_id=4,
        chat_join_request=types.ChatJoinRequest(
            chat=types.Chat(id=MTLChats.TestGroup, type='supergroup', title="Test Chat"),
            from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
            user_chat_id=999,
            date=datetime.datetime.now()
        )
    )
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    requests = mock_server.get_requests()
    assert any("Новый участник" in r["data"]["text"] for r in requests if r["method"] == "sendMessage")

@pytest.mark.asyncio
async def test_cq_join(mock_server, router_app_context):
    dp = router_app_context.dispatcher
    dp.callback_query.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(welcome_router)
    
    router_app_context.utils_service.is_admin.return_value = True
    
    cb_data = JoinCallbackData(user_id=1, chat_id=MTLChats.TestGroup, can_join=True).pack()
    
    update = types.Update(
        update_id=5,
        callback_query=types.CallbackQuery(
            id="cb1",
            chat_instance="ci1",
            from_user=types.User(id=999, is_bot=False, first_name="Admin", username="admin"),
            message=types.Message(message_id=10, date=datetime.datetime.now(), chat=types.Chat(id=123, type='supergroup'), text="Join req"),
            data=cb_data
        )
    )
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    requests = mock_server.get_requests()
    assert any(r["method"] == "approveChatJoinRequest" for r in requests)
    assert any("✅" in r["data"]["text"] for r in requests if r["method"] == "answerCallbackQuery")
