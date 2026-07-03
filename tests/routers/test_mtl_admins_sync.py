import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram import types

from routers import mtl_admins_sync as mtl_admins_sync_module
from routers.mtl_admins_sync import router as mtl_admins_sync_router
from services.mtl_admins_sync_service import MtlAdminsSyncResult
from tests.conftest import RouterTestMiddleware


@pytest.fixture(autouse=True)
async def cleanup_router():
    yield
    if mtl_admins_sync_router.parent_router:
        mtl_admins_sync_router._parent_router = None


def sync_update(username: str = "admin") -> types.Update:
    return types.Update(
        update_id=1,
        message=types.Message(
            message_id=1,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type="supergroup", title="Group"),
            from_user=types.User(id=999, is_bot=False, first_name="Admin", username=username),
            text="/sync_mtl_admins",
        ),
    )


@pytest.mark.asyncio
async def test_sync_mtl_admins_denies_non_skynet_admin(mock_telegram, router_app_context, monkeypatch):
    service = SimpleNamespace(sync=AsyncMock(return_value=MtlAdminsSyncResult()))
    monkeypatch.setattr(mtl_admins_sync_module, "MtlAdminsSyncService", lambda: service)

    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(mtl_admins_sync_router)

    await dp.feed_update(bot=router_app_context.bot, update=sync_update("user"))

    service.sync.assert_not_called()
    requests = mock_telegram.get_requests()
    assert any("not" in r["data"]["text"].lower() for r in requests if r["method"] == "sendMessage")


@pytest.mark.asyncio
async def test_sync_mtl_admins_runs_service_for_skynet_admin(mock_telegram, router_app_context, monkeypatch):
    service = SimpleNamespace(sync=AsyncMock(return_value=MtlAdminsSyncResult(media_checked=2, created=1)))
    monkeypatch.setattr(mtl_admins_sync_module, "MtlAdminsSyncService", lambda: service)

    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(mtl_admins_sync_router)
    router_app_context.admin_service.set_skynet_admins(["@admin"])

    await dp.feed_update(bot=router_app_context.bot, update=sync_update())

    service.sync.assert_awaited_once_with(router_app_context.bot, admin_service=router_app_context.admin_service)
    texts = [r["data"]["text"] for r in mock_telegram.get_requests() if r["method"] == "sendMessage"]
    assert any("Синхронизация MTL admins началась" in text for text in texts)
    assert any("Media checked: 2" in text for text in texts)


@pytest.mark.asyncio
async def test_sync_mtl_admins_splits_long_report(mock_telegram, router_app_context, monkeypatch):
    service = SimpleNamespace(sync=AsyncMock(return_value=MtlAdminsSyncResult()))
    monkeypatch.setattr(mtl_admins_sync_module, "MtlAdminsSyncService", lambda: service)
    monkeypatch.setattr(mtl_admins_sync_module, "format_sync_report", lambda result: "x" * 4050)

    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(mtl_admins_sync_router)
    router_app_context.admin_service.set_skynet_admins(["@admin"])

    await dp.feed_update(bot=router_app_context.bot, update=sync_update())

    texts = [r["data"]["text"] for r in mock_telegram.get_requests() if r["method"] == "sendMessage"]
    report_chunks = [text for text in texts if text.startswith("x")]
    assert len(report_chunks) == 2
    assert all(len(text) <= 4000 for text in report_chunks)
