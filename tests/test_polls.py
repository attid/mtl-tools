
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
