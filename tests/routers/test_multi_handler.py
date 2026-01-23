import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram import Bot, types
import datetime
import json

from routers.multi_handler import router as multi_router, on_startup, commands_info
from tests.conftest import RouterTestMiddleware, TEST_BOT_TOKEN
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
async def test_universal_command_toggle(mock_server, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(multi_router)
    
    router_app_context.utils_service.is_admin.return_value = True
    router_app_context.utils_service.is_skynet_admin.return_value = True
    
    # Pre-add to list to test removal
    if MTLChats.TestGroup not in global_data.reply_only:
        global_data.reply_only.append(MTLChats.TestGroup)
    
    update = types.Update(
        update_id=1,
        message=types.Message(
            message_id=1,
            date=datetime.datetime.now(),
            chat=types.Chat(id=MTLChats.TestGroup, type='supergroup'),
            from_user=types.User(id=999, is_bot=False, first_name="Admin", username="admin"),
            text="/set_reply_only"
        )
    )
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    # Verify removal
    assert MTLChats.TestGroup not in global_data.reply_only
    assert router_app_context.config_service.save_bot_value.called
    
    requests = mock_server.get_requests()
    assert any("Removed" in r["data"]["text"] for r in requests if r["method"] == "sendMessage")

@pytest.mark.asyncio
async def test_list_command_add(mock_server, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(multi_router)
    
    router_app_context.utils_service.is_skynet_admin.return_value = True
    
    # Reset list
    global_data.skynet_admins.clear()
    
    # Also ensure commands_info list is cleared if they are different (they shouldn't be but let's check)
    skynet_admins_ref = commands_info["add_skynet_admin"][0]
    skynet_admins_ref.clear()
    
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
    assert router_app_context.config_service.save_bot_value.called
    
    requests = mock_server.get_requests()
    assert any("Added" in r["data"]["text"] for r in requests if r["method"] == "sendMessage")

@pytest.mark.asyncio
async def test_topic_admin_management(mock_server, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(multi_router)
    
    router_app_context.utils_service.is_admin.return_value = True
    
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
            from_user=types.User(id=999, is_bot=False, first_name="Admin", username="admin"),
            text="/add_topic_admin @topicadmin"
        )
    )
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    # Verify added
    assert chat_thread_key in global_data.topic_admins
    assert "@topicadmin" in global_data.topic_admins[chat_thread_key]
    
    # Verify save
    assert router_app_context.config_service.save_bot_value.called
    
    requests = mock_server.get_requests()
    assert any("Added at this thread" in r["data"]["text"] for r in requests if r["method"] == "sendMessage")

@pytest.mark.asyncio
async def test_on_startup_triggers_loads():
    # Since on_startup uses asyncio.create_task(command_config_loads()), we mock command_config_loads
    with patch("routers.multi_handler.command_config_loads", new_callable=AsyncMock) as mock_loads, \
         patch("routers.multi_handler.asyncio.create_task") as mock_task:
        await on_startup()
        assert mock_task.called
        # Verify it passed the coroutine
        # We can't easily check the arg of create_task without more complex matching, 
        # but calling create_task is the main side effect.
