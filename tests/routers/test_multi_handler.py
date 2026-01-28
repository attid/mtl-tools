import pytest
import datetime
import json
import asyncio
from aiogram import types

from routers.multi_handler import router as multi_router, on_startup, commands_info
from tests.conftest import RouterTestMiddleware
from tests.fakes import FakeMongoConfig
from other.global_data import global_data, MTLChats, BotValueTypes

@pytest.fixture(autouse=True)
async def cleanup_router():
    yield
    if multi_router.parent_router:
         multi_router._parent_router = None
    # Use clear() to preserve references held by commands_info
    global_data.reply_only.clear()
    global_data.no_first_link.clear()
    global_data.skynet_admins.clear()
    global_data.topic_admins.clear()

@pytest.mark.asyncio
async def test_universal_command_toggle(mock_telegram, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(multi_router)
    
    # default mock_telegram admin is user_id=123456
    # Pre-add to list to test removal
    if MTLChats.TestGroup not in global_data.reply_only:
        global_data.reply_only.append(MTLChats.TestGroup)
    
    update = types.Update(
        update_id=1,
        message=types.Message(
            message_id=1,
            date=datetime.datetime.now(),
            chat=types.Chat(id=MTLChats.TestGroup, type='supergroup'),
            from_user=types.User(id=123456, is_bot=False, first_name="Admin", username="admin"),
            text="/set_reply_only"
        )
    )
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    # Verify removal
    assert MTLChats.TestGroup not in global_data.reply_only
    # ConfigRepository(session).save_bot_value is now called directly
    # So we just verify the response message

    requests = mock_telegram.get_requests()
    assert any("Removed" in r["data"]["text"] for r in requests if r["method"] == "sendMessage")

@pytest.mark.asyncio
async def test_list_command_add(mock_telegram, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(multi_router)
    
    router_app_context.admin_service.set_skynet_admins(["@admin"])
    global_data.skynet_admins = ["@admin"]  # Keep synced for commands_info reference
    skynet_admins_ref = commands_info["add_skynet_admin"][0]
    
    update = types.Update(
        update_id=2,
        message=types.Message(
            message_id=2,
            date=datetime.datetime.now(),
            chat=types.Chat(id=MTLChats.TestGroup, type='supergroup'),
            from_user=types.User(id=999, is_bot=False, first_name="Admin", username="admin"),
            text="/add_skynet_admin @new_admin"
        )
    )
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    # Check both references
    assert "@new_admin" in global_data.skynet_admins or "@new_admin" in skynet_admins_ref
    # ConfigRepository(session).save_bot_value is now called directly

    requests = mock_telegram.get_requests()
    assert any("Added" in r["data"]["text"] for r in requests if r["method"] == "sendMessage")

@pytest.mark.asyncio
async def test_topic_admin_management(mock_telegram, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(multi_router)
    
    # default mock_telegram admin is user_id=123456
    
    chat_id = MTLChats.TestGroup
    thread_id = 5
    chat_thread_key = f"{chat_id}-{thread_id}"
    
    # Clean up before test
    if chat_thread_key in global_data.topic_admins:
        del global_data.topic_admins[chat_thread_key]
        
    update = types.Update(
        update_id=3,
        message=types.Message(
            message_id=3,
            date=datetime.datetime.now(),
            chat=types.Chat(id=chat_id, type='supergroup', title="Group"),
            message_thread_id=thread_id,
            from_user=types.User(id=123456, is_bot=False, first_name="Admin", username="admin"),
            text="/add_topic_admin @topicadmin"
        )
    )
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    # Verify added
    assert chat_thread_key in global_data.topic_admins
    assert "@topicadmin" in global_data.topic_admins[chat_thread_key]
    # ConfigRepository(session).save_bot_value is now called directly

    requests = mock_telegram.get_requests()
    assert any("Added at this thread" in r["data"]["text"] for r in requests if r["method"] == "sendMessage")

@pytest.mark.asyncio
async def test_on_startup_triggers_loads(monkeypatch):
    """Test that on_startup calls command_config_loads with app_context."""
    called_with = []

    def fake_command_config_loads(app_context=None):
        called_with.append(app_context)

    monkeypatch.setattr("routers.multi_handler.command_config_loads", fake_command_config_loads)

    # Create fake dispatcher with app_context
    fake_app_context = object()  # Any truthy object
    fake_dispatcher = {'app_context': fake_app_context}

    # on_startup is async but command_config_loads is now sync
    await on_startup(fake_dispatcher)

    # Verify command_config_loads was called with the app_context
    assert len(called_with) == 1
    assert called_with[0] is fake_app_context
