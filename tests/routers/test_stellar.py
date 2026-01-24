import pytest
import datetime
from aiogram import types

from routers.stellar import router as stellar_router
from tests.conftest import RouterTestMiddleware
from tests.fakes import FakeWebResponse
from other.global_data import global_data, MTLChats

@pytest.fixture(autouse=True)
async def cleanup_router():
    yield
    if stellar_router.parent_router:
         stellar_router._parent_router = None
    global_data.skynet_admins = []

@pytest.mark.asyncio
async def test_fee_command(mock_telegram, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(stellar_router)
    
    router_app_context.stellar_service.check_fee.return_value = "100-200 stroops"
    
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
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    requests = mock_telegram.get_requests()
    req = next((r for r in requests if r["method"] == "sendMessage"), None)
    assert req is not None
    assert "100-200 stroops" in req["data"]["text"]

@pytest.mark.asyncio
async def test_decode_command(mock_telegram, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(stellar_router)
    
    router_app_context.stellar_service.decode_xdr.return_value = ["Decoded", "XDR"]
    
    update = types.Update(
        update_id=2,
        message=types.Message(
            message_id=2,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='supergroup', title="Group"),
            from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
            text="/decode AAAA..."
        )
    )
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    requests = mock_telegram.get_requests()
    assert any("Decoded" in r["data"]["text"] for r in requests if r["method"] == "sendMessage")

@pytest.mark.asyncio
async def test_show_bim_command(mock_telegram, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(stellar_router)
    
    router_app_context.stellar_service.show_bim.return_value = "BIM Info"
    
    update = types.Update(
        update_id=3,
        message=types.Message(
            message_id=3,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='supergroup', title="Group"),
            from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
            text="/show_bim"
        )
    )
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    requests = mock_telegram.get_requests()
    req = next((r for r in requests if r["method"] == "sendMessage"), None)
    assert req is not None
    assert "BIM Info" in req["data"]["text"]

@pytest.mark.asyncio
async def test_do_council(mock_telegram, router_app_context):
    global_data.skynet_admins = ["@admin"]
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(stellar_router)
    
    router_app_context.stellar_service.get_balances.return_value = {'EURMTL': 100}
    router_app_context.web_service.get.return_value = FakeWebResponse({
        "distribution": {"GABC...": 10},
        "xdr": "AAAA..."
    })
    router_app_context.stellar_service.sign.return_value = "SIGNED_XDR"
    router_app_context.stellar_service.async_submit.return_value = None
    
    update = types.Update(
        update_id=4,
        message=types.Message(
            message_id=4,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='supergroup', title="Group"),
            from_user=types.User(id=MTLChats.ITolstov, is_bot=False, first_name="Admin", username="admin"),
            text="/do_council"
        )
    )
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    requests = mock_telegram.get_requests()
    # Check messages
    texts = [r["data"]["text"] for r in requests if r["method"] == "sendMessage"]
    assert any("Distribution" in t for t in texts)
    assert any("Work done" in t for t in texts)
    
    assert router_app_context.stellar_service.async_submit.called

@pytest.mark.asyncio
async def test_update_airdrops(mock_telegram, router_app_context):
    global_data.skynet_admins = ["@admin"]
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(stellar_router)
    
    router_app_context.report_service.update_airdrop.return_value = None
    
    update = types.Update(
        update_id=5,
        message=types.Message(
            message_id=5,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='supergroup', title="Group"),
            from_user=types.User(id=MTLChats.ITolstov, is_bot=False, first_name="Admin", username="admin"),
            text="/update_airdrops"
        )
    )
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    assert router_app_context.report_service.update_airdrop.called
    requests = mock_telegram.get_requests()
    texts = [r["data"]["text"] for r in requests if r["method"] == "sendMessage"]
    assert any("Обновление завершено" in t for t in texts)

@pytest.mark.asyncio
async def test_check_bim(mock_telegram, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(stellar_router)
    
    router_app_context.gspread_service.check_bim.return_value = "Check Result"
    
    update = types.Update(
        update_id=6,
        message=types.Message(
            message_id=6,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='supergroup', title="Group"),
            from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
            text="/check_bim"
        )
    )
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    requests = mock_telegram.get_requests()
    req = next((r for r in requests if r["method"] == "sendMessage"), None)
    assert req is not None
    assert "Check Result" in req["data"]["text"]

@pytest.mark.asyncio
async def test_check_mtlap(mock_telegram, router_app_context):
    global_data.skynet_admins = ["@admin"]
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(stellar_router)
    
    router_app_context.stellar_service.find_public_key.return_value = "GABC..."
    router_app_context.stellar_service.check_mtlap.return_value = "MTLAP Info"
    
    update = types.Update(
        update_id=7,
        message=types.Message(
            message_id=7,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='supergroup', title="Group"),
            from_user=types.User(id=MTLChats.ITolstov, is_bot=False, first_name="Admin", username="admin"),
            text="/check_mtlap GABC..."
        )
    )
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    requests = mock_telegram.get_requests()
    req = next((r for r in requests if r["method"] == "sendMessage"), None)
    assert req is not None
    assert "MTLAP Info" in req["data"]["text"]
