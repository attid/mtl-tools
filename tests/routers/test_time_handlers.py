import pytest
from unittest.mock import MagicMock, patch, AsyncMock, Mock
from routers.time_handlers import cmd_send_message_1m, time_clear
from other.constants import MTLChats

@pytest.mark.asyncio
async def test_cmd_send_message_1m(mock_server, router_app_context):
    bot = router_app_context.bot
    
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
    mock_record.button_json = "{}"
    
    # Mock MessageRepository
    with patch("routers.time_handlers.MessageRepository") as MockRepo:
        mock_repo_instance = MockRepo.return_value
        mock_repo_instance.load_new_messages.return_value = [mock_record]
        
        await cmd_send_message_1m(bot, mock_pool)
        
        # Verify message sent via mock server check
        requests = mock_server.get_requests()
        req = next((r for r in requests if r["method"] == "sendMessage" and r["data"]["text"] == "Scheduled msg"), None)
        assert req is not None
        assert str(req["data"]["chat_id"]) == "123"
        
        # Verify db update
        assert mock_record.was_send == 1
        mock_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_time_clear(mock_server, router_app_context):
    bot = router_app_context.bot
    
    # Mock grist data
    mock_chats = [{"chat_id": 12345}]
    
    # Mock bot.get_chat 
    bot.get_chat = AsyncMock(return_value=Mock(full_name="Test Chat"))
    
    with patch("routers.time_handlers.grist_manager.load_table_data", new_callable=AsyncMock) as mock_load, \
         patch("routers.time_handlers.remove_deleted_users", new_callable=AsyncMock) as mock_remove, \
         patch("routers.time_handlers.asyncio.sleep", new_callable=AsyncMock):
        
        mock_load.return_value = mock_chats
        mock_remove.return_value = 5 # 5 users removed
        
        await time_clear(bot)
        
        # Verify remove called
        mock_remove.assert_called_with(12345)
        
        # Verify report sent
        requests = mock_server.get_requests()
        req = next((r for r in requests if r["method"] == "sendMessage" and "Finished removing" in r["data"]["text"]), None)
        assert req is not None
        assert str(req["data"]["chat_id"]) == str(MTLChats.SpamGroup)
