
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from aiogram import Bot, types, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.enums import ChatMemberStatus
import datetime

from routers.welcome import router as welcome_router
from tests.conftest import MOCK_SERVER_URL, TEST_BOT_TOKEN
from other.global_data import global_data, MTLChats

class MockDbMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        data["session"] = MagicMock()
        return await handler(event, data)

@pytest.fixture(autouse=True)
async def cleanup_router():
    yield
    if welcome_router.parent_router:
         welcome_router._parent_router = None

@pytest.mark.asyncio
async def test_set_welcome_command(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(MOCK_SERVER_URL)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(welcome_router)
    dp.message.middleware(MockDbMiddleware())

    # Mock is_admin
    with patch("routers.welcome.is_admin", return_value=True), \
         patch("other.global_data.global_data.mongo_config.save_bot_value", new_callable=AsyncMock), \
         patch("routers.welcome.cmd_sleep_and_delete", new_callable=AsyncMock):
        
        # Test /set_welcome
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
        
        await dp.feed_update(bot=bot, update=update)
        
        # Verify changes in global_data
        assert global_data.welcome_messages.get(MTLChats.TestGroup) == "Hello $$USER$$"
        
        # Verify confirmation message
        msg_req = next((r for r in mock_server if r["method"] == "sendMessage" and "Added" in r["data"]["text"]), None)
        assert msg_req is not None

    await bot.session.close()

@pytest.mark.asyncio
async def test_new_chat_member_welcome(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(MOCK_SERVER_URL)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(welcome_router)
    dp.chat_member.middleware(MockDbMiddleware())

    # Setup global data for welcome message
    global_data.welcome_messages[MTLChats.TestGroup] = "Welcome $$USER$$!"
    
    # Mock mocks
    with patch("routers.welcome.combo_check_spammer", return_value=False), \
         patch("routers.welcome.lols_check_spammer", return_value=False), \
         patch("routers.welcome.enforce_entry_channel", return_value=(True, None)), \
         patch("other.global_data.global_data.mongo_config.add_user_to_chat", new_callable=AsyncMock), \
         patch("routers.welcome.global_data.check_user", return_value=0): # 0 = New User

        # Simulate ChatMemberUpdated (Join)
        user = types.User(id=123, is_bot=False, first_name="Joiner", username="joiner")
        date = datetime.datetime.now()
        chat = types.Chat(id=MTLChats.TestGroup, type='supergroup', title="Test Chat")
        
        event = types.ChatMemberUpdated(
            chat=chat,
            from_user=user,
            date=date,
            old_chat_member=types.ChatMemberLeft(user=user),
            new_chat_member=types.ChatMemberMember(user=user)
        )
        
        update = types.Update(
            update_id=2,
            chat_member=event
        )
        
        # We need to manually register the update type if it's not default?
        # chat_member updates are allowed by default if we use polling or feed_update but we need to verify.
        
        await dp.feed_update(bot=bot, update=update)
        
        # Verify welcome message
        msg_req = next((r for r in mock_server if r["method"] == "sendMessage" and "Welcome" in r["data"]["text"]), None)
        assert msg_req is not None
        assert "joiner" in msg_req["data"]["text"] # $$USER$$ replaced

    await bot.session.close()
