
import pytest
from aiogram import Bot, Dispatcher, types
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.filters import CommandStart
from unittest.mock import patch, AsyncMock, MagicMock
import datetime

from routers.start_router import router as start_router
from tests.conftest import MOCK_SERVER_URL, TEST_BOT_TOKEN

from aiogram.dispatcher.middlewares.base import BaseMiddleware

class MockDbMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        data["session"] = MagicMock()
        return await handler(event, data)

@pytest.fixture(autouse=True)
async def cleanup_router():
    # Only if we need to detach manually. 
    # But easier is to reset _parent_router on the router object if accessible.
    yield
    if start_router.parent_router:
         start_router._parent_router = None

@pytest.mark.asyncio
async def test_start_command(mock_server, dp):
    """
    Test /start command.
    """
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(MOCK_SERVER_URL)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    
    # Add Middleware
    dp.message.middleware(MockDbMiddleware())
    
    dp.include_router(start_router)
    
    # Mock db_save_bot_user
    with patch("routers.start_router.db_save_bot_user") as mock_save:
        
        # Simulate /start message
        update = types.Update(
            update_id=1,
            message=types.Message(
                message_id=1,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='private'),
                from_user=types.User(id=123, is_bot=False, first_name="Test", username="test"),
                text="/start"
            )
        )
        
        await dp.feed_update(bot=bot, update=update)
        
        # Verify
        req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
        assert req is not None
        assert "Привет, я бот из" in req["data"]["text"]
        
        mock_save.assert_called_once()

    await bot.session.close()

@pytest.mark.asyncio
async def test_links_command(mock_server, dp):
    """
    Test /links command.
    """
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(MOCK_SERVER_URL)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    
    # Add Middleware
    dp.message.middleware(MockDbMiddleware())
    
    dp.include_router(start_router)
    
    update = types.Update(
        update_id=2,
        message=types.Message(
            message_id=2,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='private'),
            from_user=types.User(id=123, is_bot=False, first_name="Test", username="test"),
            text="/links"
        )
    )
    
    await dp.feed_update(bot=bot, update=update)
    
    req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
    assert req is not None
    assert "Полезные ссылки" in req["data"]["text"]

    await bot.session.close()
