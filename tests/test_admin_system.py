
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from aiogram import Bot, types, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.fsm.storage.memory import MemoryStorage
import datetime
import hashlib

from routers.admin_system import router as admin_router
from tests.conftest import MOCK_SERVER_URL, TEST_BOT_TOKEN
from other.global_data import MTLChats

class MockDbMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        data["session"] = MagicMock()
        return await handler(event, data)

@pytest.fixture(autouse=True)
async def cleanup_router():
    yield
    if admin_router.parent_router:
         admin_router._parent_router = None

@pytest.mark.asyncio
async def test_sha256_command(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(MOCK_SERVER_URL)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(admin_router)
    
    test_str = "test_string"
    expected_hash = hashlib.sha256(test_str.encode()).hexdigest()
    
    update = types.Update(
        update_id=1,
        message=types.Message(
            message_id=1,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='private'),
            from_user=types.User(id=123, is_bot=False, first_name="User", username="user"),
            text=f"/sha256 {test_str}"
        )
    )
    
    await dp.feed_update(bot=bot, update=update)
    
    msg_req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
    assert msg_req is not None
    assert expected_hash in msg_req["data"]["text"]

    await bot.session.close()

@pytest.mark.asyncio
async def test_eurmtl_command(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(MOCK_SERVER_URL)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(admin_router)
    
    update = types.Update(
        update_id=2,
        message=types.Message(
            message_id=2,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='private'),
            from_user=types.User(id=123, is_bot=False, first_name="User", username="user"),
            text="/eurmtl"
        )
    )
    
    await dp.feed_update(bot=bot, update=update)
    
    msg_req = next((r for r in mock_server if r["method"] == "sendMessage" and "Click the button below" in r["data"]["text"]), None)
    assert msg_req is not None
    assert "reply_markup" in msg_req["data"]

    await bot.session.close()

@pytest.mark.asyncio
async def test_log_command(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(MOCK_SERVER_URL)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(admin_router)
    
    # Mock is_skynet_admin, os.path.isfile, os.path.getsize
    # Mock FSInputFile to return a string, so aiogram treats it as file_id and doesn't try to open file
    with patch("routers.admin_system.is_skynet_admin", return_value=True), \
         patch("routers.admin_system.os.path.isfile", return_value=True), \
         patch("routers.admin_system.os.path.getsize", return_value=100), \
         patch("routers.admin_system.FSInputFile", return_value="mock_file_id"):
        
        update = types.Update(
            update_id=3,
            message=types.Message(
                message_id=3,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='private'),
                from_user=types.User(id=999, is_bot=False, first_name="Admin", username="admin"),
                text="/log"
            )
        )
        
        await dp.feed_update(bot=bot, update=update)
        
        doc_req = next((r for r in mock_server if r["method"] == "sendDocument"), None)
        assert doc_req is not None
        # We can't verify the file content easily as it's mocked, but we verify method call

    await bot.session.close()
