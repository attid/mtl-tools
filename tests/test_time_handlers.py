
import pytest
from unittest.mock import MagicMock, patch, AsyncMock, Mock
from aiogram import Bot, types
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
import datetime
import json

from routers.time_handlers import cmd_send_message_1m, time_clear
from tests.conftest import MOCK_SERVER_URL, TEST_BOT_TOKEN
from other.global_data import MTLChats

@pytest.mark.asyncio
async def test_cmd_send_message_1m(mock_server):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(MOCK_SERVER_URL)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    
    # Mock DB session and records
    mock_session = MagicMock()
    mock_pool = MagicMock()
    mock_pool.return_value.__enter__.return_value = mock_session
    
    # Create a mock record
    mock_record = Mock()
    mock_record.update_id = 0 # triggers send_message path
    mock_record.text = "Scheduled msg"
    mock_record.user_id = 123
    mock_record.use_alarm = 1
    mock_record.was_send = 0
    mock_record.topic_id = 0
    
    # Mock db_load_new_message
    with patch("routers.time_handlers.db_load_new_message", return_value=[mock_record]):
        
        await cmd_send_message_1m(bot, mock_pool)
        
        # Verify message sent via mock server check
        req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
        assert req is not None
        assert req["data"]["text"] == "Scheduled msg"
        assert str(req["data"]["chat_id"]) == "123"
        
        # Verify db update
        assert mock_record.was_send == 1
        mock_session.commit.assert_called_once()

    await bot.session.close()

@pytest.mark.asyncio
async def test_time_clear(mock_server):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(MOCK_SERVER_URL)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    
    # Mock grist data
    mock_chats = [{"chat_id": 12345}]
    
    # Mock bot.get_chat explicitly to avoid Pydantic validation errors from mock server response
    bot.get_chat = AsyncMock(return_value=Mock(full_name="Test Chat"))
    
    with patch("routers.time_handlers.grist_manager.load_table_data", new_callable=AsyncMock) as mock_load, \
         patch("routers.time_handlers.remove_deleted_users", new_callable=AsyncMock) as mock_remove, \
         patch("routers.time_handlers.asyncio.sleep", new_callable=AsyncMock):
        
        mock_load.return_value = mock_chats
        mock_remove.return_value = 5 # 5 users removed
        
        # We also need to let bot.get_chat work. The mock server handles getChat.
        
        # Override MTLChats.SpamGroup to match a chat ID expected by mock server or generic
        # However mock server accepts any chat_id for sendMessage.
        # But time_clear sends to MTLChats.SpamGroup.
        # Let's verify it sends to that ID.
        
        await time_clear(bot)
        
        # Verify remove called
        mock_remove.assert_called_with(12345)
        
        # Verify report sent
        # It sends to MTLChats.SpamGroup
        req = next((r for r in mock_server if r["method"] == "sendMessage" and "Finished removing" in r["data"]["text"]), None)
        assert req is not None
        assert str(req["data"]["chat_id"]) == str(MTLChats.SpamGroup)

    await bot.session.close()
