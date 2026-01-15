
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from aiogram import Bot, types, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.dispatcher.middlewares.base import BaseMiddleware
import datetime

from routers.stellar import router as stellar_router
from tests.conftest import MOCK_SERVER_URL, TEST_BOT_TOKEN
from other.global_data import global_data

class MockDbMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        data["session"] = MagicMock()
        return await handler(event, data)

@pytest.fixture(autouse=True)
async def cleanup_router():
    yield
    if stellar_router.parent_router:
         stellar_router._parent_router = None

@pytest.mark.asyncio
async def test_fee_command(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(MOCK_SERVER_URL)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(stellar_router)
    
    with patch("routers.stellar.cmd_check_fee", return_value="100-200 stroops"):
        
        update = types.Update(
            update_id=1,
            message=types.Message(
                message_id=1,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup', title="Group"),
                from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                text="/fee"
            )
        )
        
        await dp.feed_update(bot=bot, update=update)
        
        req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
        assert req is not None
        assert "Комиссия" in req["data"]["text"]
        assert "100-200 stroops" in req["data"]["text"]

    await bot.session.close()

@pytest.mark.asyncio
async def test_balance_command(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(MOCK_SERVER_URL)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(stellar_router)
    
    # Mock image generation and FSInputFile
    with patch("routers.stellar.get_cash_balance", return_value="Balance info"), \
         patch("routers.stellar.create_image_with_text"), \
         patch("routers.stellar.FSInputFile") as MockFSFile:
        
        MockFSFile.return_value = "mock_file_id"
        
        update = types.Update(
            update_id=2,
            message=types.Message(
                message_id=2,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup', title="Group"),
                from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                text="/balance"
            )
        )
        
        await dp.feed_update(bot=bot, update=update)
        
        req = next((r for r in mock_server if r["method"] == "sendPhoto"), None)
        assert req is not None
        assert req["data"]["photo"] == "mock_file_id"

    await bot.session.close()

@pytest.mark.asyncio
async def test_decode_command(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(MOCK_SERVER_URL)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(stellar_router)
    
    with patch("routers.stellar.decode_xdr", return_value=["Decoded", "XDR"]), \
         patch("routers.stellar.check_url_xdr", return_value=["Url", "XDR"]):
        
        # Test normal decode
        update = types.Update(
            update_id=3,
            message=types.Message(
                message_id=3,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup', title="Group"),
                from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                text="/decode AAAA..."
            )
        )
        
        await dp.feed_update(bot=bot, update=update)
        
        req = next((r for r in mock_server if r["method"] == "sendMessage" and "Decoded" in r["data"]["text"]), None)
        assert req is not None
        
        # Test url decode
        update_url = types.Update(
            update_id=4,
            message=types.Message(
                message_id=4,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup', title="Group"),
                from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                text="/decode https://eurmtl.me/tools?xdr=AAAA..."
            )
        )
        
        await dp.feed_update(bot=bot, update=update_url)
        
        req_url = next((r for r in mock_server if r["method"] == "sendMessage" and "Url" in r["data"]["text"]), None)
        assert req_url is not None

    await bot.session.close()
