import pytest
import datetime
from aiogram import types

from routers.airdrops import router as airdrop_router, AirdropConfigItem, AirdropCallbackData
from tests.conftest import RouterTestMiddleware

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
async def test_airdrop_request_flow(mock_telegram, router_app_context, airdrop_config_item):
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
    router_app_context.airdrop_service.log_payment.return_value = None
    
    # 2. Simulate User Message
    USER_ID = 111
    CHAT_ID = -1002294641071 # allow-listed chat from router filter
    STELLAR_ADDR = "GCQVCSHGR6446QVM3HUCLFFCUFEIK2ALTNMBAIXP57CVRNG5VL3RZJZ2"
    TEXT = f"Some text #ID{USER_ID} {STELLAR_ADDR}"
    
    # Mock getChatMember via mock_server (since check_membership uses bot.get_chat_member)
    mock_telegram.add_response("getChatMember", {
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
    requests = mock_telegram.get_requests()
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
    requests = mock_telegram.get_requests()
    # Logic: New requests are appended.
    # We look for sendMessage with "отправлен"
    req_sent = next((r for r in requests if r["method"] == "sendMessage" and "отправлен" in r["data"]["text"]), None)
    assert req_sent is not None
    assert "tx_hash_123" in req_sent["data"]["text"]


@pytest.mark.asyncio
async def test_airdrop_callback_remove_action(mock_telegram, router_app_context, airdrop_config_item):
    """
    Test that clicking "remove" button removes keyboard and clears request data.
    """
    from routers.airdrops import airdrop_requests

    # Setup
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.callback_query.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(airdrop_router)

    # Setup services
    router_app_context.stellar_service.get_balances.return_value = {"MTL": "100.0", "USDM": "50.0"}
    router_app_context.airdrop_service.check_records.return_value = ["Grist check passed"]
    router_app_context.airdrop_service.load_configs.return_value = [airdrop_config_item]

    # Setup mock for getChatMember
    mock_telegram.add_response("getChatMember", {
        "ok": True,
        "result": {
            "status": "member",
            "user": {"id": 111, "is_bot": False, "username": "user", "first_name": "User"}
        }
    })

    USER_ID = 111
    CHAT_ID = -1002294641071
    STELLAR_ADDR = "GCQVCSHGR6446QVM3HUCLFFCUFEIK2ALTNMBAIXP57CVRNG5VL3RZJZ2"
    TEXT = f"Some text #ID{USER_ID} {STELLAR_ADDR}"

    # First send a message to create the request
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

    # Verify request was stored
    assert len(airdrop_requests) == 1
    stored_msg_id = list(airdrop_requests.keys())[0]

    # Now simulate "remove" callback
    callback_data = AirdropCallbackData(
        action="remove",
        message_id=stored_msg_id,
        config_id=0
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

    # Verify request was removed from storage
    assert stored_msg_id not in airdrop_requests

    # Verify keyboard was removed (editMessageReplyMarkup was called)
    requests = mock_telegram.get_requests()
    edit_requests = [r for r in requests if r["method"] == "editMessageReplyMarkup"]
    assert len(edit_requests) > 0

    # Verify answerCallbackQuery was called
    answer_requests = [r for r in requests if r["method"] == "answerCallbackQuery"]
    assert len(answer_requests) > 0


@pytest.mark.asyncio
async def test_airdrop_callback_missing_request_data(mock_telegram, router_app_context):
    """
    Test that callback with unknown message_id returns error.
    """
    from routers.airdrops import airdrop_requests

    # Clear any leftover data
    airdrop_requests.clear()

    # Setup
    dp = router_app_context.dispatcher
    dp.callback_query.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(airdrop_router)

    CHAT_ID = -1002294641071
    UNKNOWN_MSG_ID = 99999

    # Simulate callback for non-existent request
    callback_data = AirdropCallbackData(
        action="send",
        message_id=UNKNOWN_MSG_ID,
        config_id=1
    ).pack()

    update_callback = types.Update(
        update_id=1,
        callback_query=types.CallbackQuery(
            id="cb1",
            from_user=types.User(id=999, is_bot=False, first_name="Admin", username="admin"),
            message=types.Message(
                message_id=UNKNOWN_MSG_ID,
                date=datetime.datetime.now(),
                chat=types.Chat(id=CHAT_ID, type='supergroup'),
                text="Some message"
            ),
            chat_instance="inst1",
            data=callback_data
        )
    )

    await dp.feed_update(bot=router_app_context.bot, update=update_callback)

    # Verify answerCallbackQuery was called with show_alert=True
    requests = mock_telegram.get_requests()
    answer_requests = [r for r in requests if r["method"] == "answerCallbackQuery"]
    assert len(answer_requests) > 0
    # The callback should answer with an alert (value is string "true" from HTTP form data)
    answer_req = answer_requests[0]
    assert answer_req["data"].get("show_alert") in ("True", "true", True)

    # Verify keyboard was removed
    edit_requests = [r for r in requests if r["method"] == "editMessageReplyMarkup"]
    assert len(edit_requests) > 0


@pytest.mark.asyncio
async def test_airdrop_callback_missing_config(mock_telegram, router_app_context, airdrop_config_item):
    """
    Test that callback with unknown config_id returns error.
    """
    from routers.airdrops import airdrop_requests

    # Clear any leftover data
    airdrop_requests.clear()

    # Setup
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.callback_query.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(airdrop_router)

    # Setup services
    router_app_context.stellar_service.get_balances.return_value = {"MTL": "100.0", "USDM": "50.0"}
    router_app_context.airdrop_service.check_records.return_value = ["Grist check passed"]
    router_app_context.airdrop_service.load_configs.return_value = [airdrop_config_item]

    # Setup mock for getChatMember
    mock_telegram.add_response("getChatMember", {
        "ok": True,
        "result": {
            "status": "member",
            "user": {"id": 111, "is_bot": False, "username": "user", "first_name": "User"}
        }
    })

    USER_ID = 111
    CHAT_ID = -1002294641071
    STELLAR_ADDR = "GCQVCSHGR6446QVM3HUCLFFCUFEIK2ALTNMBAIXP57CVRNG5VL3RZJZ2"
    TEXT = f"Some text #ID{USER_ID} {STELLAR_ADDR}"

    # First send a message to create the request
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

    # Verify request was stored
    assert len(airdrop_requests) == 1
    stored_msg_id = list(airdrop_requests.keys())[0]

    # Now simulate "send" callback with wrong config_id
    WRONG_CONFIG_ID = 9999
    callback_data = AirdropCallbackData(
        action="send",
        message_id=stored_msg_id,
        config_id=WRONG_CONFIG_ID
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

    # Verify payment was NOT executed
    assert not router_app_context.stellar_service.send_payment_async.called

    # Verify answerCallbackQuery was called with show_alert=True (config not found)
    requests = mock_telegram.get_requests()
    answer_requests = [r for r in requests if r["method"] == "answerCallbackQuery"]
    # First answerCallbackQuery is "ok выполняю", second should be the error
    assert len(answer_requests) >= 2
