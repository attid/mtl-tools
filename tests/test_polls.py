
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from aiogram import Bot, types, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.dispatcher.middlewares.base import BaseMiddleware
import datetime
import json

from routers.polls import router as polls_router, PollCallbackData
from tests.conftest import MOCK_SERVER_URL, TEST_BOT_TOKEN
from other.global_data import global_data, MTLChats

class MockDbMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        data["session"] = MagicMock()
        return await handler(event, data)

@pytest.fixture(autouse=True)
async def cleanup_router():
    yield
    if polls_router.parent_router:
         polls_router._parent_router = None

@pytest.mark.asyncio
async def test_poll_command(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(MOCK_SERVER_URL)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(polls_router)
    dp.message.middleware(MockDbMiddleware())
    
    # Mock save_bot_value
    global_data.mongo_config.save_bot_value = AsyncMock()
    
    # Create poll object
    poll = types.Poll(
        id="poll123",
        question="My Question",
        options=[types.PollOption(text="Opt1", voter_count=0), types.PollOption(text="Opt2", voter_count=0)],
        total_voter_count=0,
        is_closed=False,
        is_anonymous=False,
        type="regular",
        allows_multiple_answers=False
    )

    update = types.Update(
        update_id=1,
        message=types.Message(
            message_id=2,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='supergroup', title="Group"),
            from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
            text="/poll",
            reply_to_message=types.Message(
                message_id=1,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup', title="Group"),
                poll=poll
            )
        )
    )
    
    await dp.feed_update(bot=bot, update=update)
    
    # Verify sendMessage (bot recreates the poll with buttons)
    req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
    assert req is not None
    assert req["data"]["text"] == "My Question"
    assert "reply_markup" in req["data"]
    
    # Verify mongo save
    global_data.mongo_config.save_bot_value.assert_called_once()

    await bot.session.close()

@pytest.mark.asyncio
async def test_apoll_command(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(MOCK_SERVER_URL)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(polls_router)
    dp.message.middleware(MockDbMiddleware())
    
    # Mock external tools
    with patch("routers.polls.gs_copy_a_table", return_value=("http://google.com", "sheet_id")), \
         patch("routers.polls.gs_update_a_table_first", return_value=True), \
         patch("routers.polls.get_mtlap_votes", return_value=[]):
        
        poll = types.Poll(
            id="999",
            question="Assoc Poll",
            options=[types.PollOption(text="Yes", voter_count=0)],
            total_voter_count=0,
            is_closed=False,
            is_anonymous=False,
            type="regular",
            allows_multiple_answers=False
        )

        update = types.Update(
            update_id=2,
            message=types.Message(
                message_id=4,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup', title="Group"),
                from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                text="/apoll",
                reply_to_message=types.Message(
                    message_id=3,
                    date=datetime.datetime.now(),
                    chat=types.Chat(id=123, type='supergroup', title="Group"),
                    poll=poll
                )
            )
        )
        
        # /apoll sends a reaction (need mock reaction handler? No, ignored by mock server usually or returns true)
        # It calls sendPoll
        
        await dp.feed_update(bot=bot, update=update)
        
        # Verify sendPoll
        req = next((r for r in mock_server if r["method"] == "sendPoll"), None)
        assert req is not None
        assert req["data"]["question"] == "Assoc Poll"

    await bot.session.close()

@pytest.mark.asyncio
async def test_poll_callback(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(MOCK_SERVER_URL)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(polls_router)
    dp.callback_query.middleware(MockDbMiddleware())

    # We need to setup global_data.votes and chat_to_address mapping (routers.polls.chat_to_address)
    # The routers.polls module has chat_to_address. We can patch it or set it up if accessible.
    # It accesses global_data.votes
    
    test_chat_id = 123
    test_address = "ADDR1"
    
    # Patch chat_to_address in routers.polls
    with patch.dict("routers.polls.chat_to_address", {test_chat_id: test_address}, clear=False):
        
        # Setup global_data.votes
        global_data.votes = {
            test_address: {
                "@user": 10,
                "NEED": {"50": 5, "75": 8, "100": 10}
            }
        }
        
        # Setup mongo load for poll state
        my_poll = {
            "question": "Q?",
            "closed": False, 
            "message_id": 99,
            "buttons": [["Opt1", 0, []]]
        }
        global_data.mongo_config.load_bot_value = AsyncMock(return_value=json.dumps(my_poll))
        global_data.mongo_config.save_bot_value = AsyncMock()

        cb_data = PollCallbackData(answer=0).pack()
        
        update = types.Update(
            update_id=3,
            callback_query=types.CallbackQuery(
                id="cb1",
                chat_instance="ci1",
                from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                message=types.Message(
                    message_id=99,
                    date=datetime.datetime.now(),
                    chat=types.Chat(id=test_chat_id, type='supergroup', title="Group"),
                    text="Poll Msg"
                ),
                data=cb_data
            )
        )
        
        await dp.feed_update(bot=bot, update=update)
        
        # Verify editMessageText (updating vote counts)
        # Note: logic truncates option text to 3 chars: button[0][:3]
        req = next((r for r in mock_server if r["method"] == "editMessageText"), None)
        assert req is not None
        assert "Opt (10)" in req["data"]["text"]
        
        # Verify save new state
        global_data.mongo_config.save_bot_value.assert_called()

    await bot.session.close()

@pytest.mark.asyncio
async def test_channel_post_creates_poll(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(MOCK_SERVER_URL)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(polls_router)
    dp.channel_post.middleware(MockDbMiddleware())

    global_data.mongo_config.save_bot_value = AsyncMock()

    poll = types.Poll(
        id="poll123",
        question="Channel Question",
        options=[types.PollOption(text="Opt1", voter_count=0)],
        total_voter_count=0,
        is_closed=False,
        is_anonymous=False,
        type="regular",
        allows_multiple_answers=False
    )

    update = types.Update(
        update_id=4,
        channel_post=types.Message(
            message_id=5,
            date=datetime.datetime.now(),
            chat=types.Chat(id=-1001649743884, type='channel', title="Channel"),
            from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
            poll=poll
        )
    )

    await dp.feed_update(bot=bot, update=update)

    req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
    assert req is not None
    global_data.mongo_config.save_bot_value.assert_called()

    await bot.session.close()

@pytest.mark.asyncio
async def test_poll_replace_text(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(MOCK_SERVER_URL)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(polls_router)
    dp.message.middleware(MockDbMiddleware())

    my_poll = {
        "question": "Old",
        "closed": False,
        "message_id": 11,
        "buttons": [["A", 0, []]]
    }
    global_data.mongo_config.load_bot_value = AsyncMock(return_value=json.dumps(my_poll))
    global_data.mongo_config.save_bot_value = AsyncMock()

    update = types.Update(
        update_id=5,
        message=types.Message(
            message_id=12,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='supergroup', title="Group"),
            from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
            text="/poll_replace_text New Question",
            reply_to_message=types.Message(
                message_id=11,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup', title="Group"),
                text="Poll"
            )
        )
    )

    await dp.feed_update(bot=bot, update=update)

    global_data.mongo_config.save_bot_value.assert_called()

    await bot.session.close()

@pytest.mark.asyncio
async def test_poll_close_with_poll(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(MOCK_SERVER_URL)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(polls_router)
    dp.message.middleware(MockDbMiddleware())

    with patch.object(bot, "stop_poll", new_callable=AsyncMock) as mock_stop:
        poll = types.Poll(
            id="poll_close",
            question="Q",
            options=[types.PollOption(text="Opt1", voter_count=0)],
            total_voter_count=0,
            is_closed=False,
            is_anonymous=False,
            type="regular",
            allows_multiple_answers=False
        )
        update = types.Update(
            update_id=6,
            message=types.Message(
                message_id=13,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup', title="Group"),
                from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                text="/poll_close",
                reply_to_message=types.Message(
                    message_id=12,
                    date=datetime.datetime.now(),
                    chat=types.Chat(id=123, type='supergroup', title="Group"),
                    poll=poll
                )
            )
        )

        await dp.feed_update(bot=bot, update=update)

        mock_stop.assert_called_once()

    await bot.session.close()

@pytest.mark.asyncio
async def test_poll_close_requires_reply(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(MOCK_SERVER_URL)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(polls_router)
    dp.message.middleware(MockDbMiddleware())

    update = types.Update(
        update_id=7,
        message=types.Message(
            message_id=14,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='supergroup', title="Group"),
            from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
            text="/poll_close"
        )
    )

    await dp.feed_update(bot=bot, update=update)

    req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
    assert req is not None
    assert "Требуется в ответ" in req["data"]["text"]

    await bot.session.close()

@pytest.mark.asyncio
async def test_poll_check_remaining_voters(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(MOCK_SERVER_URL)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(polls_router)
    dp.message.middleware(MockDbMiddleware())

    test_chat_id = 123
    test_address = "ADDR1"
    with patch.dict("routers.polls.chat_to_address", {test_chat_id: test_address}, clear=False):
        global_data.votes = {
            test_address: {
                "@user": 10,
                "@other": 5,
                "NEED": {"50": 5, "75": 8, "100": 10}
            }
        }
        my_poll = {
            "question": "Q?",
            "closed": False,
            "message_id": 99,
            "buttons": [["Opt1", 10, ["@user"]]]
        }
        global_data.mongo_config.load_bot_value = AsyncMock(return_value=json.dumps(my_poll))

        update = types.Update(
            update_id=8,
            message=types.Message(
                message_id=15,
                date=datetime.datetime.now(),
                chat=types.Chat(id=test_chat_id, type='supergroup', title="Group"),
                from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                text="/poll_check",
                reply_to_message=types.Message(
                    message_id=99,
                    date=datetime.datetime.now(),
                    chat=types.Chat(id=test_chat_id, type='supergroup', title="Group"),
                    text="Poll Msg"
                )
            )
        )

        await dp.feed_update(bot=bot, update=update)

        req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
        assert req is not None
        assert "Смотрите голосование" in req["data"]["text"]

    await bot.session.close()

@pytest.mark.asyncio
async def test_poll_reload_vote_admin(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(MOCK_SERVER_URL)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(polls_router)
    dp.message.middleware(MockDbMiddleware())

    vote_list = {"ADDR": {"..user": 1, "NEED": {"50": 1, "75": 1, "100": 1}}}
    with patch("routers.polls.is_skynet_admin", return_value=True), \
         patch("routers.polls.cmd_save_votes", new_callable=AsyncMock, return_value=vote_list):
        update = types.Update(
            update_id=9,
            message=types.Message(
                message_id=16,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup', title="Group"),
                from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                text="/poll_reload_vote"
            )
        )

        await dp.feed_update(bot=bot, update=update)

        texts = [r["data"]["text"] for r in mock_server if r["method"] == "sendMessage"]
        assert any("Список пользовател" in t for t in texts)
        assert any("reload complete" in t for t in texts)

    await bot.session.close()

@pytest.mark.asyncio
async def test_poll_answer_user_not_found(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(MOCK_SERVER_URL)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(polls_router)
    dp.poll_answer.middleware(MockDbMiddleware())

    my_poll = {
        "info_chat_id": 123,
        "info_message_id": 77,
        "google_id": "gid",
        "google_url": "http://google"
    }
    global_data.mongo_config.load_bot_value = AsyncMock(return_value=json.dumps(my_poll))

    with patch("routers.polls.grist_manager.load_table_data", new_callable=AsyncMock, return_value=[]):
        poll_answer = types.PollAnswer(
            poll_id="123",
            user=types.User(id=999, is_bot=False, first_name="User", username="user"),
            option_ids=[0]
        )
        update = types.Update(
            update_id=10,
            poll_answer=poll_answer
        )

        await dp.feed_update(bot=bot, update=update)

        req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
        assert req is not None
        assert "not found" in req["data"]["text"]

    await bot.session.close()

@pytest.mark.asyncio
async def test_apoll_check_reply(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(MOCK_SERVER_URL)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(polls_router)
    dp.message.middleware(MockDbMiddleware())

    my_poll = {"google_id": "gid"}
    global_data.mongo_config.load_bot_value = AsyncMock(return_value=json.dumps(my_poll))

    with patch("routers.polls.gs_check_vote_table", new_callable=AsyncMock, return_value=(["ok"], ["d1"])):
        poll = types.Poll(
            id="321",
            question="Assoc Poll",
            options=[types.PollOption(text="Yes", voter_count=0)],
            total_voter_count=0,
            is_closed=False,
            is_anonymous=False,
            type="regular",
            allows_multiple_answers=False
        )
        update = types.Update(
            update_id=11,
            message=types.Message(
                message_id=17,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup', title="Group"),
                from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                text="/apoll_check",
                reply_to_message=types.Message(
                    message_id=16,
                    date=datetime.datetime.now(),
                    chat=types.Chat(id=123, type='supergroup', title="Group"),
                    poll=poll
                )
            )
        )

        await dp.feed_update(bot=bot, update=update)

        req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
        assert req is not None
        assert "delegates" in req["data"]["text"]

    await bot.session.close()
