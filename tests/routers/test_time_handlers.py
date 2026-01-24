import pytest
from other.constants import MTLChats
from other.grist_tools import MTLGrist
import routers.time_handlers as time_handlers
from tests.fakes import FakeAsyncMethod, FakeSession, FakeSyncMethod


def make_session_pool(session):
    class Pool:
        def __call__(self):
            return self

        def __enter__(self):
            return session

        def __exit__(self, exc_type, exc, tb):
            return False

    return Pool()

@pytest.mark.asyncio
async def test_cmd_send_message_1m(mock_telegram, router_app_context, monkeypatch):
    bot = router_app_context.bot
    
    mock_session = FakeSession()
    mock_pool = make_session_pool(mock_session)
    
    class Record:
        update_id = 0
        text = "Scheduled msg"
        user_id = 123
        use_alarm = 1
        was_send = 0
        topic_id = 0
        button_json = "{}"

    mock_record = Record()
    
    class FakeMessageRepository:
        def __init__(self, session):
            self.session = session

        def load_new_messages(self):
            return [mock_record]

    monkeypatch.setattr(time_handlers, "MessageRepository", FakeMessageRepository)

    await time_handlers.cmd_send_message_1m(bot, mock_pool)

    requests = mock_telegram.get_requests()
    req = next((r for r in requests if r["method"] == "sendMessage" and r["data"]["text"] == "Scheduled msg"), None)
    assert req is not None
    assert str(req["data"]["chat_id"]) == "123"
    assert mock_record.was_send == 1
    assert mock_session.committed is True

@pytest.mark.asyncio
async def test_time_clear(mock_telegram, router_app_context, monkeypatch):
    bot = router_app_context.bot
    
    mock_chats = [{"chat_id": 12345}]
    
    mock_load = FakeAsyncMethod(return_value=mock_chats)
    mock_remove = FakeAsyncMethod(return_value=5)
    mock_sleep = FakeAsyncMethod()

    monkeypatch.setattr(time_handlers.grist_manager, "load_table_data", mock_load)
    monkeypatch.setattr(time_handlers, "remove_deleted_users", mock_remove)
    monkeypatch.setattr(time_handlers.asyncio, "sleep", mock_sleep)

    await time_handlers.time_clear(bot)

    mock_load.assert_awaited_once_with(
        MTLGrist.CONFIG_auto_clean,
        filter_dict={"enabled": [True]}
    )
    mock_remove.assert_awaited_once_with(12345)
    mock_sleep.assert_awaited_once()

    requests = mock_telegram.get_requests()
    req = next((r for r in requests if r["method"] == "sendMessage" and "Finished removing" in r["data"]["text"]), None)
    assert req is not None
    assert str(req["data"]["chat_id"]) == str(MTLChats.SpamGroup)


@pytest.mark.asyncio
async def test_time_usdm_daily_sends_summary(mock_telegram, router_app_context, monkeypatch):
    bot = router_app_context.bot

    mock_session = FakeSession()
    mock_pool = make_session_pool(mock_session)

    calc_result = [("addr1", "x", 10.0), ("addr2", "x", 30.0)]

    mock_create_list = FakeSyncMethod(return_value=452)
    mock_calc_daily = FakeAsyncMethod(return_value=calc_result)
    mock_gen_xdr = FakeSyncMethod(return_value=0)
    mock_send_by_list = FakeAsyncMethod(return_value=0)
    mock_get_balances = FakeAsyncMethod(return_value={"USDM": "626.57"})

    monkeypatch.setattr(time_handlers, "cmd_create_list", mock_create_list)
    monkeypatch.setattr(time_handlers, "cmd_calc_usdm_daily", mock_calc_daily)
    monkeypatch.setattr(time_handlers, "cmd_gen_xdr", mock_gen_xdr)
    monkeypatch.setattr(time_handlers, "cmd_send_by_list_id", mock_send_by_list)
    monkeypatch.setattr(time_handlers, "get_balances", mock_get_balances)

    await time_handlers.time_usdm_daily(mock_pool, bot)

    mock_send_by_list.assert_awaited_once()
    requests = mock_telegram.get_requests()
    msg_req = next((r for r in requests if r["method"] == "sendMessage" and str(r["data"]["chat_id"]) == str(MTLChats.USDMMGroup)), None)
    assert msg_req is not None
    text = msg_req["data"]["text"]
    assert "Start div pays №452." in text
    assert "Found 2 addresses." in text
    assert "Total payouts sum: 40.00." in text
    assert "Осталось 626.57 USDM" in text
    assert "All work done." in text


@pytest.mark.asyncio
async def test_time_usdm_daily_retries_send_on_error(mock_telegram, router_app_context, monkeypatch):
    bot = router_app_context.bot

    mock_session = FakeSession()
    mock_pool = make_session_pool(mock_session)

    calc_result = [("addr1", "x", 1.0)]
    send_results = [Exception("fail"), Exception("fail"), 0]

    async def send_side_effect(*args, **kwargs):
        result = send_results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    mock_create_list = FakeSyncMethod(return_value=1)
    mock_calc_daily = FakeAsyncMethod(return_value=calc_result)
    mock_gen_xdr = FakeSyncMethod(return_value=0)
    mock_send_by_list = FakeAsyncMethod(side_effect=send_side_effect)
    mock_get_balances = FakeAsyncMethod(return_value={"USDM": "1.00"})
    mock_sleep = FakeAsyncMethod()

    monkeypatch.setattr(time_handlers, "cmd_create_list", mock_create_list)
    monkeypatch.setattr(time_handlers, "cmd_calc_usdm_daily", mock_calc_daily)
    monkeypatch.setattr(time_handlers, "cmd_gen_xdr", mock_gen_xdr)
    monkeypatch.setattr(time_handlers, "cmd_send_by_list_id", mock_send_by_list)
    monkeypatch.setattr(time_handlers, "get_balances", mock_get_balances)
    monkeypatch.setattr(time_handlers.asyncio, "sleep", mock_sleep)

    await time_handlers.time_usdm_daily(mock_pool, bot)

    assert mock_send_by_list.call_count == 3
    assert mock_sleep.call_count == 2
    requests = mock_telegram.get_requests()
    assert any(r["method"] == "sendMessage" and str(r["data"]["chat_id"]) == str(MTLChats.USDMMGroup) for r in requests)


@pytest.mark.asyncio
async def test_time_usdm_daily_gives_up_after_many_errors(mock_telegram, router_app_context, monkeypatch):
    bot = router_app_context.bot

    mock_session = FakeSession()
    mock_pool = make_session_pool(mock_session)

    calc_result = [("addr1", "x", 1.0)]
    send_results = [Exception("fail")] * 20

    async def send_side_effect(*args, **kwargs):
        result = send_results.pop(0)
        raise result

    mock_create_list = FakeSyncMethod(return_value=1)
    mock_calc_daily = FakeAsyncMethod(return_value=calc_result)
    mock_gen_xdr = FakeSyncMethod(return_value=0)
    mock_send_by_list = FakeAsyncMethod(side_effect=send_side_effect)
    mock_get_balances = FakeAsyncMethod(return_value={"USDM": "1.00"})
    mock_sleep = FakeAsyncMethod()

    monkeypatch.setattr(time_handlers, "cmd_create_list", mock_create_list)
    monkeypatch.setattr(time_handlers, "cmd_calc_usdm_daily", mock_calc_daily)
    monkeypatch.setattr(time_handlers, "cmd_gen_xdr", mock_gen_xdr)
    monkeypatch.setattr(time_handlers, "cmd_send_by_list_id", mock_send_by_list)
    monkeypatch.setattr(time_handlers, "get_balances", mock_get_balances)
    monkeypatch.setattr(time_handlers.asyncio, "sleep", mock_sleep)

    await time_handlers.time_usdm_daily(mock_pool, bot)

    assert mock_send_by_list.call_count == 20
    assert mock_sleep.call_count == 20
    requests = mock_telegram.get_requests()
    assert not any(r["method"] == "sendMessage" and str(r["data"]["chat_id"]) == str(MTLChats.USDMMGroup) for r in requests)
