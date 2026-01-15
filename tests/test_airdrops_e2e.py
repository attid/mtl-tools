
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram import Bot, Dispatcher, types
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
import datetime

from routers.airdrops import router as airdrop_router, AirdropConfigItem, AirdropCallbackData
from tests.conftest import MOCK_SERVER_URL, TEST_BOT_TOKEN

@pytest.fixture
def airdrop_config_item():
    item = AirdropConfigItem(
        record_id=1,
        asset_code="MTL",
        asset_issuer="GCQVCSHGR6446QVM3HUCLFFCUFEIK2ALTNMBAIXP57CVRNG5VL3RZJZ2",
        amount="10.0",
        priority=0
    )
    return item

@pytest.mark.asyncio
async def test_airdrop_request_flow(mock_server, airdrop_config_item):
    """
    Test flow:
    1. User sends message with #ID123 and Stellar Address
    2. Bot analyzes and replies with options
    3. User clicks "Send"
    4. Bot executes payment and replies
    """
    
    # 1. Setup
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(MOCK_SERVER_URL)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp = Dispatcher()
    dp.include_router(airdrop_router)
    
    # Mocks
    with patch("routers.airdrops.get_balances", new_callable=AsyncMock) as mock_balances, \
         patch("routers.airdrops.grist_check_airdrop_records", new_callable=AsyncMock) as mock_grist_check, \
         patch("routers.airdrops.grist_load_airdrop_configs", new_callable=AsyncMock) as mock_grist_configs, \
         patch("routers.airdrops.send_payment_async", new_callable=AsyncMock) as mock_send_payment, \
         patch("routers.airdrops.grist_log_airdrop_payment", new_callable=AsyncMock) as mock_grist_log:
        
        # Setup Mock Returns
        mock_balances.return_value = {"MTL": "100.0", "USDM": "50.0"} # For both user and source
        mock_grist_check.return_value = ["Grist check passed"]
        mock_grist_configs.return_value = [airdrop_config_item]
        mock_send_payment.return_value = {"hash": "tx_hash_123"}
        
        # 2. Simulate User Message
        USER_ID = 111
        CHAT_ID = -1002294641071 # allow-listed chat from router filter
        STELLAR_ADDR = "GCQVCSHGR6446QVM3HUCLFFCUFEIK2ALTNMBAIXP57CVRNG5VL3RZJZ2"
        TEXT = f"Some text #ID{USER_ID} {STELLAR_ADDR}"
        
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
        
        await dp.feed_update(bot=bot, update=update_message)
        
        # Verify Analysis Reply
        req_analysis = next((r for r in mock_server if r["method"] == "sendMessage"), None)
        assert req_analysis is not None
        assert "Новый запрос!" in req_analysis["data"]["text"]
        assert STELLAR_ADDR in req_analysis["data"]["text"]
        
        mock_server.clear()
        
        # 3. Simulate "Send" Callback
        # We need the correct callback data. The code uses AirdropCallbackData
        callback_data = AirdropCallbackData(
            action="send",
            message_id=1, # Mock server returns message_id=1 for the sent message
            config_id=airdrop_config_item.record_id
        ).pack()
        
        update_callback = types.Update(
            update_id=2,
            callback_query=types.CallbackQuery(
                id="cb1",
                from_user=types.User(id=999, is_bot=False, first_name="Admin", username="admin"),
                message=types.Message(
                    message_id=1,
                    date=datetime.datetime.now(),
                    chat=types.Chat(id=CHAT_ID, type='supergroup'),
                    text="Previous bot message" # Dummy
                ),
                chat_instance="inst1",
                data=callback_data
            )
        )
        
        await dp.feed_update(bot=bot, update=update_callback)
        
        # Verify Payment Execution
        mock_send_payment.assert_called_once()
        mock_grist_log.assert_called_once()
        
        # Verify "Sent" Reply
        req_sent = next((r for r in mock_server if r["method"] == "sendMessage" and "отправлен" in r["data"]["text"]), None)
        assert req_sent is not None
        assert "tx_hash_123" in req_sent["data"]["text"]
        
        # Verify Buttons Removed (editMessageReplyMarkup)
        # Note: In the code, it calls edit_reply_markup on the ORIGINAL message (the analysis one)
        # The mock server might capture this as editMessageReplyMarkup
        # TODO check if mock server handles this passed-through method. 
        # The provided mock server only had sendMessage/deleteWebhook/setMyCommands/getMe/sendPhoto/getChatMember
        # We might need to add editMessageReplyMarkup to conftest or just verify the call flow didn't crash
        # For now, we assume if no crash, it worked, as aiogram would error if method not found (404 from mock)
    
    await bot.session.close()
