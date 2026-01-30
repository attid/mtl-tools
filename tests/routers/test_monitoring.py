import pytest
from aiogram import types
from datetime import datetime

from routers.monitoring import router as monitoring_router
from other.constants import MTLChats
from tests.conftest import RouterTestMiddleware

@pytest.fixture(autouse=True)
async def cleanup_router(router_app_context):
    yield
    if monitoring_router.parent_router:
         monitoring_router._parent_router = None
    # Reset the bot_state_service last_pong
    router_app_context.bot_state_service.set_last_pong(None)

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

    # Pre-state - ensure no previous pong
    router_app_context.bot_state_service.set_last_pong(None)

    await dp.feed_update(bot=router_app_context.bot, update=update)

    # Verify state update via bot_state_service
    last_pong = router_app_context.bot_state_service.get_last_pong()
    assert last_pong is not None
    assert isinstance(last_pong, datetime)
