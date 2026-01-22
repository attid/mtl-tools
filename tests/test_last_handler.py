
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from aiogram import Bot, types, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.dispatcher.middlewares.base import BaseMiddleware
import datetime

from routers.last_handler import router as last_router, SpamCheckCallbackData, ReplyCallbackData, FirstMessageCallbackData
from tests.conftest import TEST_BOT_TOKEN
from other.global_data import global_data, BotValueTypes, MTLChats

class MockDbMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        data["session"] = MagicMock()
        return await handler(event, data)

@pytest.fixture(autouse=True)
async def cleanup_router():
    yield
    if last_router.parent_router:
         last_router._parent_router = None

@pytest.mark.asyncio
async def test_spam_detection(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(last_router)
    dp.message.middleware(MockDbMiddleware()) # Needs db session for logging

    # Mock check_spam to return True
    # Implementation detail: cmd_last_check calls check_spam
    # check_spam calls delete_and_log_spam if true
    
    # We need to simulate a chat in global_data.no_first_link to trigger spam check
    chat_id = 999
    if chat_id not in global_data.no_first_link:
        global_data.no_first_link.append(chat_id)
    
    with patch("routers.last_handler.check_spam", return_value=True) as mock_check:
        
        update = types.Update(
            update_id=1,
            message=types.Message(
                message_id=1,
                date=datetime.datetime.now(),
                chat=types.Chat(id=chat_id, type='supergroup', title="Group"),
                from_user=types.User(id=123, is_bot=False, first_name="Spammer", username="spammer"),
                text="Spam message"
            )
        )
        
        await dp.feed_update(bot=bot, update=update)
        
        # Verify check_spam called
        mock_check.assert_called_once()
        
    await bot.session.close()

@pytest.mark.asyncio
async def test_real_spam_flow(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(last_router)
    dp.message.middleware(MockDbMiddleware())

    chat_id = 999
    if chat_id not in global_data.no_first_link:
        global_data.no_first_link.append(chat_id)
    MTLChats.SpamGroup = 888 # Set spam group ID
    
    # Mock spam checker to return True
    with patch("routers.last_handler.combo_check_spammer", return_value=True):
        
        update = types.Update(
            update_id=2,
            message=types.Message(
                message_id=2,
                date=datetime.datetime.now(),
                chat=types.Chat(id=chat_id, type='supergroup', title="Group"),
                from_user=types.User(id=123, is_bot=False, first_name="Spammer", username="spammer"),
                text="Spam message"
            )
        )
        
        await dp.feed_update(bot=bot, update=update)
        
        # Verify forward to spam group
        # forwardMessage to 888
        req = next((r for r in mock_server if r["method"] == "forwardMessage" and int(r["data"]["chat_id"]) == 888), None)
        assert req is not None
        
        # Verify restrict call
        res_req = next((r for r in mock_server if r["method"] == "restrictChatMember"), None)
        assert res_req is not None
        assert int(res_req["data"]["user_id"]) == 123
        
        # Verify notification in spam group
        msg_req = next((r for r in mock_server if r["method"] == "sendMessage" and int(r["data"]["chat_id"]) == 888), None)
        assert msg_req is not None
        assert "CAS ban" in msg_req["data"]["text"]

    await bot.session.close()

@pytest.mark.asyncio
async def test_spam_callback(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(last_router)
    dp.callback_query.middleware(MockDbMiddleware()) # Needs db session for callback logic


    # Mock is_admin
    with patch("routers.last_handler.is_admin", new_callable=AsyncMock, return_value=True):
        
        cb_data = SpamCheckCallbackData(
            message_id=10,
            chat_id=123,
            user_id=456,
            good=False,
            new_message_id=20,
            message_thread_id=0
        ).pack()
        
        update = types.Update(
            update_id=3,
            callback_query=types.CallbackQuery(
                id="cb1",
                chat_instance="ci1",
                from_user=types.User(id=999, is_bot=False, first_name="Admin", username="admin"),
                message=types.Message(
                    message_id=30,
                    date=datetime.datetime.now(),
                    chat=types.Chat(id=888, type='supergroup', title="SpamGroup"), # Spam group
                    text="Spam report"
                ),
                data=cb_data
            )
        )
        
        await dp.feed_update(bot=bot, update=update)
        
        # Verify answerCallbackQuery
        ans_req = next((r for r in mock_server if r["method"] == "answerCallbackQuery"), None)
        assert ans_req is not None
        
        # Verify ban using banChatMember
        ban_req = next((r for r in mock_server if r["method"] == "banChatMember"), None)
        assert ban_req is not None
        assert int(ban_req["data"]["user_id"]) == 456
        assert int(ban_req["data"]["chat_id"]) == 123
        
        # Verify editMessageReplyMarkup
        edit_req = next((r for r in mock_server if r["method"] == "editMessageReplyMarkup"), None)
        assert edit_req is not None

    await bot.session.close()

@pytest.mark.asyncio
async def test_last_check_other_non_text(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(last_router)
    dp.message.middleware(MockDbMiddleware())

    chat_id = 777
    if chat_id not in global_data.no_first_link:
        global_data.no_first_link.append(chat_id)

    with patch("routers.last_handler.global_data.check_user", return_value=0), \
         patch("routers.last_handler.delete_and_log_spam", new_callable=AsyncMock) as mock_delete:
        update = types.Update(
            update_id=5,
            message=types.Message(
                message_id=50,
                date=datetime.datetime.now(),
                chat=types.Chat(id=chat_id, type='supergroup', title="Group"),
                from_user=types.User(id=123, is_bot=False, first_name="User", username="user"),
                photo=[types.PhotoSize(file_id="1", file_unique_id="1", width=1, height=1)]
            )
        )

        await dp.feed_update(bot=bot, update=update)

        mock_delete.assert_called()

    await bot.session.close()

@pytest.mark.asyncio
async def test_reply_ban_callback(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(last_router)
    dp.callback_query.middleware(MockDbMiddleware())

    cb_data = ReplyCallbackData(user_id=456, chat_id=123, message_id=10).pack()
    with patch("routers.last_handler.is_admin", new_callable=AsyncMock, return_value=True):
        update = types.Update(
            update_id=6,
            callback_query=types.CallbackQuery(
                id="cb2",
                chat_instance="ci2",
                from_user=types.User(id=999, is_bot=False, first_name="Admin", username="admin"),
                message=types.Message(
                    message_id=60,
                    date=datetime.datetime.now(),
                    chat=types.Chat(id=888, type='supergroup', title="SpamGroup"),
                    text="Spam report"
                ),
                data=cb_data
            )
        )

        await dp.feed_update(bot=bot, update=update)

        ban_req = next((r for r in mock_server if r["method"] == "banChatMember"), None)
        assert ban_req is not None
        del_req = next((r for r in mock_server if r["method"] == "deleteMessage"), None)
        assert del_req is not None
        ans_req = next((r for r in mock_server if r["method"] == "answerCallbackQuery"), None)
        assert ans_req is not None

    await bot.session.close()

@pytest.mark.asyncio
async def test_cq_look_callback(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(last_router)

    update = types.Update(
        update_id=7,
        callback_query=types.CallbackQuery(
            id="cb3",
            chat_instance="ci3",
            from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
            message=types.Message(
                message_id=61,
                date=datetime.datetime.now(),
                chat=types.Chat(id=888, type='supergroup', title="SpamGroup"),
                text="Look"
            ),
            data="👀"
        )
    )

    await dp.feed_update(bot=bot, update=update)

    ans_req = next((r for r in mock_server if r["method"] == "answerCallbackQuery"), None)
    assert ans_req is not None

    await bot.session.close()

@pytest.mark.asyncio
async def test_first_vote_callback(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(last_router)
    dp.callback_query.middleware(MockDbMiddleware())

    global_data.first_vote_data = {}
    cb_data = FirstMessageCallbackData(spam=False, message_id=70, user_id=555).pack()

    with patch("routers.last_handler.is_admin", new_callable=AsyncMock, return_value=False):
        update = types.Update(
            update_id=8,
            callback_query=types.CallbackQuery(
                id="cb4",
                chat_instance="ci4",
                from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                message=types.Message(
                    message_id=71,
                    date=datetime.datetime.now(),
                    chat=types.Chat(id=888, type='supergroup', title="SpamGroup"),
                    text="Vote"
                ),
                data=cb_data
            )
        )

        await dp.feed_update(bot=bot, update=update)

        edit_req = next((r for r in mock_server if r["method"] == "editMessageText"), None)
        assert edit_req is not None

    await bot.session.close()

@pytest.mark.asyncio
async def test_check_mute_enforcement_channel(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(last_router)
    dp.message.middleware(MockDbMiddleware())

    chat_id = 999
    thread_id = 7
    chat_thread_key = f"{chat_id}-{thread_id}"
    channel_id = -100999999

    # Setup global data with muted channel
    if chat_id not in global_data.moderate:
        global_data.moderate.append(chat_id)
        
    global_data.topic_mute[chat_thread_key] = {
        channel_id: {
            "end_time": (datetime.datetime.now() + datetime.timedelta(hours=1)).isoformat(),
            "user": "Channel SpamChannel"
        }
    }
    
    # Mock message from muted channel
    update = types.Update(
        update_id=4,
        message=types.Message(
            message_id=40,
            date=datetime.datetime.now(),
            chat=types.Chat(id=chat_id, type='supergroup', is_forum=True),
            message_thread_id=thread_id,
            from_user=types.User(id=136817688, is_bot=True, first_name="Channel Bot", username="Channel_Bot"),
            sender_chat=types.Chat(id=channel_id, type='channel', title="SpamChannel"),
            text="I should be deleted"
        )
    )
    
    await dp.feed_update(bot=bot, update=update)
    
    # Verify deleteMessage called
    del_req = next((r for r in mock_server if r["method"] == "deleteMessage"), None)
    assert del_req is not None
    assert int(del_req["data"]["chat_id"]) == chat_id
    assert int(del_req["data"]["message_id"]) == 40
    
    await bot.session.close()
