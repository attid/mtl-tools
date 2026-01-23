import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram import Bot, Dispatcher, types
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
import datetime

from routers.airdrops import router as airdrop_router, AirdropConfigItem, AirdropCallbackData
from tests.conftest import RouterTestMiddleware, TEST_BOT_TOKEN

@pytest.fixture
def airdrop_config_item():
    return AirdropConfigItem(
        record_id=1,
        asset_code="MTL",
        asset_issuer="GCQVCSHGR6446QVM3HUCLFFCUFEIK2ALTNMBAIXP57CVRNG5VL3RZJZ2",
        amount="10.0",
        priority=0
    )

@pytest.fixture(autouse=True)
async def cleanup_router():
    yield
    if airdrop_router.parent_router:
         airdrop_router._parent_router = None

@pytest.mark.asyncio
async def test_airdrop_request_flow(mock_server, router_app_context, airdrop_config_item):
    """
    Test flow:
    1. User sends message with #ID123 and Stellar Address
    2. Bot analyzes and replies with options
    3. User clicks "Send"
    4. Bot executes payment and replies
    """
    
    # 1. Setup
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.callback_query.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(airdrop_router)
    
    # Mocks for Services
    # Stellar Service
    router_app_context.stellar_service.get_balances.return_value = {"MTL": "100.0", "USDM": "50.0"}
    router_app_context.stellar_service.send_payment_async.return_value = {"hash": "tx_hash_123"}
    
    # Airdrop Service
    router_app_context.airdrop_service.check_records.return_value = ["Grist check passed"]
    router_app_context.airdrop_service.load_configs.return_value = [airdrop_config_item]
    router_app_context.airdrop_service.log_payment = AsyncMock() # check call later
    
    # 2. Simulate User Message
    USER_ID = 111
    CHAT_ID = -1002294641071 # allow-listed chat from router filter
    STELLAR_ADDR = "GCQVCSHGR6446QVM3HUCLFFCUFEIK2ALTNMBAIXP57CVRNG5VL3RZJZ2"
    TEXT = f"Some text #ID{USER_ID} {STELLAR_ADDR}"
    
    # Mock getChatMember via mock_server (since check_membership uses bot.get_chat_member)
    mock_server.add_response("getChatMember", {
        "ok": True,
        "result": {
            "status": "member",
            "user": {"id": USER_ID, "is_bot": False, "username": "user", "first_name": "User"}
        }
    })
    
    update_message = types.Update(
        update_id=1,
        message=types.Message(
            message_id=100,
            date=datetime.datetime.now(),
            chat=types.Chat(id=CHAT_ID, type='supergroup'),
            from_user=types.User(id=USER_ID, is_bot=False, first_name="User", username="user"),
            text=TEXT
        )
    )
    
    await dp.feed_update(bot=router_app_context.bot, update=update_message)
    
    # Verify Analysis Reply
    requests = mock_server.get_requests()
    req_analysis = next((r for r in requests if r["method"] == "sendMessage"), None)
    assert req_analysis is not None
    assert "Новый запрос!" in req_analysis["data"]["text"]
    assert STELLAR_ADDR in req_analysis["data"]["text"]
    
    # Clear requests for next step
    # mock_server doesn't support clear, but we can filter by index or count. 
    # Or just filtering by action name again if unique?
    # We look forNEW send message later.
    
    # 3. Simulate "Send" Callback
    # We need the correct callback data.
    # The message ID of the bot's reply is needed. Mock server returned dummy message object structure?
    # conftest.py returns message_id=random.
    # But callback data depends on what was in keyboard.
    # We constructed callback manually in test matching expected logic.
    
    # Mock server returns message_id in sendMessage response.
    # But we can assume message_id=12345 (random from mock server).
    # But AirdropCallbackData needs `message_id`.
    # Let's assume the router code extracts message_id from callback message?
    # `handle_airdrop_callback` uses `callback_data.message_id`.
    # `build_request_keyboard` puts `sent_message.message_id` into callback data.
    # We don't know what random ID `mock_server` returned.
    # We can inspect `req_analysis` response? 
    # `mock_server` returns the response to the bot. We don't see it in `requests` (requests are INPUT to server).
    # We simulate the USER clicking the button.
    # We can use ANY message_id as long as we put it in `airdrop_requests`?
    # `airdrops.py` stores `airdrop_requests[sent_message.message_id] = ...`.
    # AND `get_requests` shows what bot sent.
    # The bot RECIEVED the response from `mock_server`.
    # We can't see what message_id the BOT saw unless we spy on bot.
    # BUT `mock_server` implementation in `conftest.py` generates `message_id`.
    # `random.randint(1, 1000)`.
    # We can't know it.
    
    # Workaround: `airdrops.py` stores data in global `airdrop_requests`.
    # We can inspect this global dict!
    from routers.airdrops import airdrop_requests
    assert len(airdrop_requests) == 1
    stored_msg_id = list(airdrop_requests.keys())[0]
    
    callback_data = AirdropCallbackData(
        action="send",
        message_id=stored_msg_id, 
        config_id=airdrop_config_item.record_id
    ).pack()
    
    update_callback = types.Update(
        update_id=2,
        callback_query=types.CallbackQuery(
            id="cb1",
            from_user=types.User(id=999, is_bot=False, first_name="Admin", username="admin"),
            message=types.Message(
                message_id=stored_msg_id,
                date=datetime.datetime.now(),
                chat=types.Chat(id=CHAT_ID, type='supergroup'),
                text="Previous bot message"
            ),
            chat_instance="inst1",
            data=callback_data
        )
    )
    
    await dp.feed_update(bot=router_app_context.bot, update=update_callback)
    
    # Verify Payment Execution
    assert router_app_context.stellar_service.send_payment_async.called
    assert router_app_context.airdrop_service.log_payment.called
    
    # Verify "Sent" Reply
    requests = mock_server.get_requests()
    # Logic: New requests are appended.
    # We look for sendMessage with "отправлен"
    req_sent = next((r for r in requests if r["method"] == "sendMessage" and "отправлен" in r["data"]["text"]), None)
    assert req_sent is not None
    assert "tx_hash_123" in req_sent["data"]["text"]
