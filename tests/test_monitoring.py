
import pytest
from aiogram import Bot, Dispatcher, types
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from unittest.mock import patch
import datetime

from routers.monitoring import router as monitoring_router
from other.global_data import global_data, MTLChats
from tests.conftest import TEST_BOT_TOKEN

@pytest.mark.asyncio
async def test_monitoring_pong_update(mock_server, dp):
    """
    Test that #skynet #mmwb command=pong updates the global_data.last_pong_response
    """
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(monitoring_router)
    
    # Reset last_pong_response
    global_data.last_pong_response = None
    
    # Simulate Pong Message from Bots Channel
    update = types.Update(
        update_id=1,
        channel_post=types.Message(
            message_id=1,
            date=datetime.datetime.now(),
            chat=types.Chat(id=MTLChats.BotsChanel, type='channel'),
            text="#skynet #mmwb command=pong status=ok"
        )
    )
    
    await dp.feed_update(bot=bot, update=update)
    
    assert global_data.last_pong_response is not None
    
    await bot.session.close()
