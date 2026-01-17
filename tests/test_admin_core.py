
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from aiogram import Bot, types, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.dispatcher.middlewares.base import BaseMiddleware
import datetime
import json

from routers.admin_core import router as admin_router
from tests.conftest import MOCK_SERVER_URL, TEST_BOT_TOKEN
from other.global_data import global_data, BotValueTypes

class MockDbMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        data["session"] = MagicMock()
        return await handler(event, data)

@pytest.fixture(autouse=True)
async def cleanup_router():
    yield
    if admin_router.parent_router:
         admin_router._parent_router = None

@pytest.mark.asyncio
async def test_ro_command(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(MOCK_SERVER_URL)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(admin_router)
    
    # Mock is_admin
    with patch("routers.admin_core.is_admin", return_value=True):
        
        reply_msg = types.Message(
            message_id=5,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='supergroup', title="Group"),
            from_user=types.User(id=789, is_bot=False, first_name="BadUser", username="baduser"),
            text="Spam"
        )
        
        update = types.Update(
            update_id=1,
            message=types.Message(
                message_id=6,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup', title="Group"),
                from_user=types.User(id=999, is_bot=False, first_name="Admin", username="admin"),
                text="!ro 10m",
                reply_to_message=reply_msg
            )
        )
        
        await dp.feed_update(bot=bot, update=update)
        
        # Verify restrict called
        req = next((r for r in mock_server if r["method"] == "restrictChatMember"), None)
        assert req is not None
        assert int(req["data"]["user_id"]) == 789

    await bot.session.close()

@pytest.mark.asyncio
async def test_topic_command(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(MOCK_SERVER_URL)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(admin_router)
    
    with patch("routers.admin_core.is_admin", return_value=True):
        
        update = types.Update(
            update_id=2,
            message=types.Message(
                message_id=7,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup', title="Forum", is_forum=True),
                from_user=types.User(id=999, is_bot=False, first_name="Admin", username="admin"),
                text="/topic 🔵 NewTopic"
            )
        )
        
        await dp.feed_update(bot=bot, update=update)
        
        # Verify createForumTopic called
        req = next((r for r in mock_server if r["method"] == "createForumTopic"), None)
        assert req is not None
        assert req["data"]["name"] == "NewTopic"
        assert req["data"]["icon_custom_emoji_id"] == "🔵"

    await bot.session.close()

@pytest.mark.asyncio
async def test_mute_command(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(MOCK_SERVER_URL)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(admin_router)
    
    # Mock global data and is_topic_admin
    # Ensure chat and thread are in topic_admins
    chat_id = 123
    thread_id = 5
    chat_thread_key = f"{chat_id}-{thread_id}"
    
    global_data.topic_admins[chat_thread_key] = {"@admin"} # Admin ID username lower match
    if chat_id not in global_data.moderate:
        global_data.moderate.append(chat_id)

    # Mock mongo config save
    global_data.mongo_config.save_bot_value = AsyncMock()

    with patch("routers.admin_core.is_topic_admin", return_value=True):
        
        reply_msg = types.Message(
            message_id=10,
            date=datetime.datetime.now(),
            chat=types.Chat(id=chat_id, type='supergroup', is_forum=True),
            message_thread_id=thread_id,
            from_user=types.User(id=789, is_bot=False, first_name="BadUser", username="baduser"),
            text="Bad msg"
        )

        update = types.Update(
            update_id=3,
            message=types.Message(
                message_id=11,
                date=datetime.datetime.now(),
                chat=types.Chat(id=chat_id, type='supergroup', is_forum=True),
                message_thread_id=thread_id,
                from_user=types.User(id=999, is_bot=False, first_name="Admin", username="admin"),
                text="/mute 1h",
                reply_to_message=reply_msg
            )
        )
        
        await dp.feed_update(bot=bot, update=update)
        
        # Verify mute logic: Persistent save called
        # Check global_data.topic_mute updated
        assert chat_thread_key in global_data.topic_mute
        assert 789 in global_data.topic_mute[chat_thread_key]
        
        # Verify save_bot_value called
        global_data.mongo_config.save_bot_value.assert_called()

    await bot.session.close()

@pytest.mark.asyncio
async def test_mute_command_channel(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(MOCK_SERVER_URL)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(admin_router)
    
    # Mock global data and is_topic_admin
    chat_id = 123
    thread_id = 5
    chat_thread_key = f"{chat_id}-{thread_id}"
    
    global_data.topic_admins[chat_thread_key] = {"@admin"}
    if chat_id not in global_data.moderate:
        global_data.moderate.append(chat_id)

    # Mock mongo config save
    global_data.mongo_config.save_bot_value = AsyncMock()

    with patch("routers.admin_core.is_topic_admin", return_value=True):
        
        # Message from a channel (has sender_chat)
        reply_msg = types.Message(
            message_id=20,
            date=datetime.datetime.now(),
            chat=types.Chat(id=chat_id, type='supergroup', is_forum=True),
            message_thread_id=thread_id,
            from_user=types.User(id=136817688, is_bot=True, first_name="Channel Bot", username="Channel_Bot"), # Generic bot ID
            sender_chat=types.Chat(id=-100999999, type='channel', title="SpamChannel"), # Specific channel
            text="Channel spam"
        )

        update = types.Update(
            update_id=4,
            message=types.Message(
                message_id=21,
                date=datetime.datetime.now(),
                chat=types.Chat(id=chat_id, type='supergroup', is_forum=True),
                message_thread_id=thread_id,
                from_user=types.User(id=999, is_bot=False, first_name="Admin", username="admin"),
                text="/mute 1h",
                reply_to_message=reply_msg
            )
        )
        
        await dp.feed_update(bot=bot, update=update)
        
        # Verify mute logic: Persistent save called for CHANNEL ID
        assert chat_thread_key in global_data.topic_mute
        # Should NOT mute the generic bot user ID
        assert 136817688 not in global_data.topic_mute[chat_thread_key]
        # Should mute the specific channel ID
        assert -100999999 in global_data.topic_mute[chat_thread_key]
        
        # Verify saved name
        assert global_data.topic_mute[chat_thread_key][-100999999]["user"] == "Channel SpamChannel"
        
        # Verify save_bot_value called
        global_data.mongo_config.save_bot_value.assert_called()

    await bot.session.close()
