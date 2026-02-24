import pytest
from aiogram import types
from datetime import datetime
from unittest.mock import AsyncMock

from routers import monitoring as monitoring_module
from routers.monitoring import HELPER_DEDUP_KEY, router as monitoring_router
from other.constants import MTLChats
from tests.conftest import RouterTestMiddleware

@pytest.fixture(autouse=True)
async def cleanup_router(router_app_context):
    yield
    if monitoring_router.parent_router:
         monitoring_router._parent_router = None
    # Reset the bot_state_service last_pong
    router_app_context.bot_state_service.set_last_pong(None)
    router_app_context.bot_state_service.clear_sync_state(HELPER_DEDUP_KEY)

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


@pytest.mark.asyncio
async def test_monitoring_helper_taken(mock_telegram, router_app_context, monkeypatch):
    dp = router_app_context.dispatcher
    dp.channel_post.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(monitoring_router)

    save_mock = AsyncMock()
    close_mock = AsyncMock()
    monkeypatch.setattr(monitoring_module, "gs_save_new_support", save_mock)
    monkeypatch.setattr(monitoring_module, "gs_close_support", close_mock)

    update = types.Update(
        update_id=2,
        channel_post=types.Message(
            message_id=2,
            date=datetime.now(),
            chat=types.Chat(id=MTLChats.BotsChanel, type='channel'),
            text=(
                "#skynet #helper command=taken user_id=123 username=client1 "
                "agent_username=agent1 url=https://t.me/c/2032873651/69621"
            ),
        ),
    )

    await dp.feed_update(bot=router_app_context.bot, update=update)

    save_mock.assert_awaited_once_with(
        user_id=123,
        username="client1",
        agent_username="agent1",
        url="https://t.me/c/2032873651/69621",
    )
    close_mock.assert_not_called()
    requests = mock_telegram.get_requests()
    ack = next((r for r in requests if r["method"] == "sendMessage" and "command=ack status=ok op=taken" in r["data"].get("text", "")), None)
    assert ack is not None


@pytest.mark.asyncio
async def test_monitoring_helper_closed(mock_telegram, router_app_context, monkeypatch):
    dp = router_app_context.dispatcher
    dp.channel_post.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(monitoring_router)

    save_mock = AsyncMock()
    close_mock = AsyncMock()
    monkeypatch.setattr(monitoring_module, "gs_save_new_support", save_mock)
    monkeypatch.setattr(monitoring_module, "gs_close_support", close_mock)

    update = types.Update(
        update_id=3,
        channel_post=types.Message(
            message_id=3,
            date=datetime.now(),
            chat=types.Chat(id=MTLChats.BotsChanel, type='channel'),
            text=(
                "#skynet #helper command=closed user_id=123 agent_username=agent1 "
                "url=https://t.me/c/2032873651/69621 closed=true"
            ),
        ),
    )

    await dp.feed_update(bot=router_app_context.bot, update=update)

    close_mock.assert_awaited_once_with(url="https://t.me/c/2032873651/69621")
    save_mock.assert_not_called()
    requests = mock_telegram.get_requests()
    ack = next((r for r in requests if r["method"] == "sendMessage" and "command=ack status=ok op=closed" in r["data"].get("text", "")), None)
    assert ack is not None


@pytest.mark.asyncio
async def test_monitoring_helper_dedup_by_url(mock_telegram, router_app_context, monkeypatch):
    dp = router_app_context.dispatcher
    dp.channel_post.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(monitoring_router)

    save_mock = AsyncMock()
    monkeypatch.setattr(monitoring_module, "gs_save_new_support", save_mock)
    monkeypatch.setattr(monitoring_module, "gs_close_support", AsyncMock())

    text = (
        "#skynet #helper command=taken user_id=123 username=client1 "
        "agent_username=agent1 url=https://t.me/c/2032873651/69621"
    )

    update1 = types.Update(
        update_id=4,
        channel_post=types.Message(
            message_id=4,
            date=datetime.now(),
            chat=types.Chat(id=MTLChats.BotsChanel, type='channel'),
            text=text,
        ),
    )
    update2 = types.Update(
        update_id=5,
        channel_post=types.Message(
            message_id=5,
            date=datetime.now(),
            chat=types.Chat(id=MTLChats.BotsChanel, type='channel'),
            text=text,
        ),
    )

    await dp.feed_update(bot=router_app_context.bot, update=update1)
    await dp.feed_update(bot=router_app_context.bot, update=update2)

    assert save_mock.await_count == 1
    requests = mock_telegram.get_requests()
    duplicate_ack = next((r for r in requests if r["method"] == "sendMessage" and "command=ack status=duplicate op=taken" in r["data"].get("text", "")), None)
    assert duplicate_ack is not None
