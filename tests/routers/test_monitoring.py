import pytest
from aiogram import types
from datetime import datetime
import re

from routers.monitoring import router as monitoring_router
from other.global_data import global_data, MTLChats
from tests.conftest import RouterTestMiddleware

@pytest.fixture(autouse=True)
async def cleanup_router():
    yield
    if monitoring_router.parent_router:
         monitoring_router._parent_router = None
    global_data.last_pong_response = None

@pytest.mark.asyncio
async def test_monitoring_pong_update(mock_telegram, router_app_context):
    dp = router_app_context.dispatcher
    dp.channel_post.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(monitoring_router)
    
    # Ensure update comes from BotsChanel
    chat_id = MTLChats.BotsChanel
    
    update = types.Update(
        update_id=1,
        channel_post=types.Message(
            message_id=1,
            date=datetime.now(),
            chat=types.Chat(id=chat_id, type='channel'),
            text="#skynet #mmwb command=pong status=ok"
        )
    )
    
    # Pre-state
    global_data.last_pong_response = None
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    # Verify state update
    assert global_data.last_pong_response is not None
    assert isinstance(global_data.last_pong_response, datetime)
