
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from aiogram import Bot, types, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.dispatcher.middlewares.base import BaseMiddleware
import datetime

from routers.moderation import router as moderation_router
from tests.conftest import MOCK_SERVER_URL, TEST_BOT_TOKEN
from other.global_data import MTLChats

class MockDbMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        data["session"] = MagicMock()
        return await handler(event, data)

@pytest.fixture(autouse=True)
async def cleanup_router():
    yield
    if moderation_router.parent_router:
         moderation_router._parent_router = None

@pytest.mark.asyncio
async def test_ban_command_as_skynet_admin(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(MOCK_SERVER_URL)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(moderation_router)
    dp.message.middleware(MockDbMiddleware())

    # Mock is_skynet_admin to True
    with patch("routers.moderation.is_skynet_admin", return_value=True), \
         patch("routers.moderation.db_get_user_id", return_value=123456), \
         patch("routers.moderation.add_bot_users") as mock_add_users, \
         patch("routers.moderation.cmd_sleep_and_delete", new_callable=AsyncMock), \
         patch("routers.moderation.is_admin", return_value=False):
        
        # Test /ban 123456
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
        
        await dp.feed_update(bot=bot, update=update)
        
        # Verify banChatMember was called
        ban_req = next((r for r in mock_server if r["method"] == "banChatMember"), None)
        assert ban_req is not None
        assert int(ban_req["data"]["user_id"]) == 123456
        
        # Verify response message
        msg_req = next((r for r in mock_server if r["method"] == "sendMessage" and "User (ID: 123456) has been banned." in r["data"]["text"]), None)
        assert msg_req is not None

    await bot.session.close()

@pytest.mark.asyncio
async def test_unban_command_as_skynet_admin(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(MOCK_SERVER_URL)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(moderation_router)
    dp.message.middleware(MockDbMiddleware())

    with patch("routers.moderation.is_skynet_admin", return_value=True), \
         patch("routers.moderation.add_bot_users"):
        
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
        
        await dp.feed_update(bot=bot, update=update)
        
        unban_req = next((r for r in mock_server if r["method"] == "unbanChatMember"), None)
        assert unban_req is not None
        assert int(unban_req["data"]["user_id"]) == 123456

    await bot.session.close()
