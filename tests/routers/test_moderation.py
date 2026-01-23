import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram import Bot, types
import datetime

from routers.moderation import router as moderation_router, UnbanCallbackData
from tests.conftest import RouterTestMiddleware, TEST_BOT_TOKEN
from other.global_data import MTLChats, global_data

@pytest.fixture(autouse=True)
async def cleanup_router():
    yield
    if moderation_router.parent_router:
         moderation_router._parent_router = None

@pytest.mark.asyncio
async def test_ban_command(mock_server, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(moderation_router)
    
    # Mock skynet admin check (manual patch for now as it uses event.from_user directly)
    with patch("routers.moderation.is_skynet_admin", return_value=True):
        router_app_context.utils_service.is_admin.return_value = True
        router_app_context.moderation_service.get_user_id.return_value = 123456
        
        update = types.Update(
            update_id=1,
            message=types.Message(
                message_id=1,
                date=datetime.datetime.now(),
                chat=types.Chat(id=MTLChats.TestGroup, type='supergroup', title="Test Chat"),
                from_user=types.User(id=999, is_bot=False, first_name="Admin", username="admin"),
                text="/ban 123456"
            )
        )
        
        await dp.feed_update(bot=router_app_context.bot, update=update)
        
        assert router_app_context.moderation_service.ban_user.called
        requests = mock_server.get_requests()
        assert any("banned" in r["data"]["text"] for r in requests if r["method"] == "sendMessage")

@pytest.mark.asyncio
async def test_unban_command(mock_server, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(moderation_router)
    
    with patch("routers.moderation.is_skynet_admin", return_value=True):
        update = types.Update(
            update_id=2,
            message=types.Message(
                message_id=2,
                date=datetime.datetime.now(),
                chat=types.Chat(id=MTLChats.TestGroup, type='supergroup', title="Test Chat"),
                from_user=types.User(id=999, is_bot=False, first_name="Admin", username="admin"),
                text="/unban 123456"
            )
        )
        
        await dp.feed_update(bot=router_app_context.bot, update=update)
        
        assert router_app_context.moderation_service.unban_user.called
        requests = mock_server.get_requests()
        assert any("unbanned" in r["data"]["text"] for r in requests if r["method"] == "sendMessage")

@pytest.mark.asyncio
async def test_unban_callback(mock_server, router_app_context):
    dp = router_app_context.dispatcher
    dp.callback_query.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(moderation_router)
    
    cb_data = UnbanCallbackData(user_id=123, chat_id=MTLChats.TestGroup).pack()
    with patch("routers.moderation.is_skynet_admin", return_value=True):
        update = types.Update(
            update_id=3,
            callback_query=types.CallbackQuery(
                id="cb1",
                chat_instance="ci1",
                from_user=types.User(id=999, is_bot=False, first_name="Admin", username="admin"),
                message=types.Message(message_id=10, date=datetime.datetime.now(), chat=types.Chat(id=MTLChats.TestGroup, type='supergroup'), text="Unban"),
                data=cb_data
            )
        )
        
        await dp.feed_update(bot=router_app_context.bot, update=update)
        
        assert router_app_context.moderation_service.unban_user.called
        requests = mock_server.get_requests()
        assert any(r["method"] == "answerCallbackQuery" for r in requests)

@pytest.mark.asyncio
async def test_test_id_command(mock_server, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(moderation_router)
    
    router_app_context.moderation_service.check_user_status.return_value = 1 # Good User
    
    update = types.Update(
        update_id=4,
        message=types.Message(
            message_id=4,
            date=datetime.datetime.now(),
            chat=types.Chat(id=MTLChats.TestGroup, type='supergroup', title="Test Chat"),
            from_user=types.User(id=111, is_bot=False, first_name="User", username="user"),
            text="/test_id"
        )
    )
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    requests = mock_server.get_requests()
    assert any("Good User" in r["data"]["text"] for r in requests if r["method"] == "sendMessage")
