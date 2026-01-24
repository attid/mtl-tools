import pytest
from unittest.mock import MagicMock, patch, AsyncMock, Mock
from routers.time_handlers import cmd_send_message_1m, time_clear, time_usdm_daily
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


@pytest.mark.asyncio
async def test_time_usdm_daily_sends_summary(router_app_context):
    bot = router_app_context.bot

    mock_session = MagicMock()
    mock_pool = MagicMock()
    mock_pool.return_value.__enter__.return_value = mock_session

    calc_result = [("addr1", "x", 10.0), ("addr2", "x", 30.0)]

    with patch("routers.time_handlers.cmd_create_list", return_value=452), \
         patch("routers.time_handlers.cmd_calc_usdm_daily", return_value=calc_result), \
         patch("routers.time_handlers.cmd_gen_xdr", return_value=0), \
         patch("routers.time_handlers.cmd_send_by_list_id", new_callable=AsyncMock, return_value=0), \
         patch("routers.time_handlers.get_balances", new_callable=AsyncMock, return_value={"USDM": "626.57"}), \
         patch.object(bot, "send_message", new_callable=AsyncMock) as mock_send_message:

        await time_usdm_daily(mock_pool, bot)

        mock_send_message.assert_awaited_once()
        chat_id, text = mock_send_message.call_args.args[:2]
        assert chat_id == MTLChats.USDMMGroup
        assert "Start div pays №452." in text
        assert "Found 2 addresses." in text
        assert "Total payouts sum: 40.00." in text
        assert "Осталось 626.57 USDM" in text
        assert "All work done." in text


@pytest.mark.asyncio
async def test_time_usdm_daily_retries_send_on_error(router_app_context):
    bot = router_app_context.bot

    mock_session = MagicMock()
    mock_pool = MagicMock()
    mock_pool.return_value.__enter__.return_value = mock_session

    calc_result = [("addr1", "x", 1.0)]
    send_side_effect = [Exception("fail"), Exception("fail"), 0]

    with patch("routers.time_handlers.cmd_create_list", return_value=1), \
         patch("routers.time_handlers.cmd_calc_usdm_daily", return_value=calc_result), \
         patch("routers.time_handlers.cmd_gen_xdr", return_value=0), \
         patch("routers.time_handlers.cmd_send_by_list_id", new_callable=AsyncMock, side_effect=send_side_effect) as mock_send_by_list, \
         patch("routers.time_handlers.get_balances", new_callable=AsyncMock, return_value={"USDM": "1.00"}), \
         patch("routers.time_handlers.asyncio.sleep", new_callable=AsyncMock) as mock_sleep, \
         patch.object(bot, "send_message", new_callable=AsyncMock) as mock_send_message:

        await time_usdm_daily(mock_pool, bot)

        assert mock_send_by_list.await_count == 3
        assert mock_sleep.await_count == 2
        mock_send_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_time_usdm_daily_gives_up_after_many_errors(router_app_context):
    bot = router_app_context.bot

    mock_session = MagicMock()
    mock_pool = MagicMock()
    mock_pool.return_value.__enter__.return_value = mock_session

    calc_result = [("addr1", "x", 1.0)]
    send_side_effect = [Exception("fail")] * 20

    with patch("routers.time_handlers.cmd_create_list", return_value=1), \
         patch("routers.time_handlers.cmd_calc_usdm_daily", return_value=calc_result), \
         patch("routers.time_handlers.cmd_gen_xdr", return_value=0), \
         patch("routers.time_handlers.cmd_send_by_list_id", new_callable=AsyncMock, side_effect=send_side_effect) as mock_send_by_list, \
         patch("routers.time_handlers.get_balances", new_callable=AsyncMock, return_value={"USDM": "1.00"}), \
         patch("routers.time_handlers.asyncio.sleep", new_callable=AsyncMock), \
         patch.object(bot, "send_message", new_callable=AsyncMock) as mock_send_message:

        await time_usdm_daily(mock_pool, bot)

        assert mock_send_by_list.await_count == 20
        mock_send_message.assert_not_awaited()
