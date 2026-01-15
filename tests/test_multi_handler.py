
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from aiogram import Bot, types, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
import datetime
import json

from routers.multi_handler import router as multi_router
from tests.conftest import MOCK_SERVER_URL, TEST_BOT_TOKEN
from other.global_data import global_data, BotValueTypes

@pytest.fixture(autouse=True)
async def cleanup_router():
    yield
    if multi_router.parent_router:
         multi_router._parent_router = None

@pytest.mark.asyncio
async def test_config_toggle(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(MOCK_SERVER_URL)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(multi_router)
    
    # Mock admin check
    with patch("routers.multi_handler.is_admin", return_value=True):
        
        # Test /set_no_first_link
        # It toggles presence in global_data.no_first_link list
        chat_id = 123
        if chat_id in global_data.no_first_link:
            global_data.no_first_link.remove(chat_id)
            
        global_data.mongo_config.save_bot_value = AsyncMock()
        
        update = types.Update(
            update_id=1,
            message=types.Message(
                message_id=1,
                date=datetime.datetime.now(),
                chat=types.Chat(id=chat_id, type='supergroup', title="Group"),
                from_user=types.User(id=999, is_bot=False, first_name="Admin", username="admin"),
                text="/set_no_first_link"
            )
        )
        
        await dp.feed_update(bot=bot, update=update)
        
        # Verify added to list
        assert chat_id in global_data.no_first_link
        # Verify save called
        global_data.mongo_config.save_bot_value.assert_called_with(chat_id, BotValueTypes.NoFirstLink, '1')
        
        # Verify reply "Added"
        req = next((r for r in mock_server if r["method"] == "sendMessage" and "Added" in r["data"]["text"]), None)
        assert req is not None

    await bot.session.close()

@pytest.mark.asyncio
async def test_list_management(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(MOCK_SERVER_URL)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(multi_router)
    
    # Mock skynet admin
    with patch("routers.multi_handler.is_skynet_admin", return_value=True):
        
        # Test /add_skynet_admin
        # We must modify the existing list object because commands_info holds a reference to it
        global_data.skynet_admins.clear() 
        global_data.mongo_config.save_bot_value = AsyncMock()
        
        update = types.Update(
            update_id=2,
            message=types.Message(
                message_id=2,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup', title="Group"),
                from_user=types.User(id=999, is_bot=False, first_name="Admin", username="admin"),
                text="/add_skynet_admin @newadmin"
            )
        )
        
        await dp.feed_update(bot=bot, update=update)
        
        # Verify added
        assert "@newadmin" in global_data.skynet_admins
        # Verify save
        global_data.mongo_config.save_bot_value.assert_called()

    await bot.session.close()

@pytest.mark.asyncio
async def test_topic_admin_management(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(MOCK_SERVER_URL)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(multi_router)
    
    with patch("routers.multi_handler.is_admin", return_value=True):
        
        # Test /add_topic_admin in a topic
        chat_id = 123
        thread_id = 5
        chat_thread_key = f"{chat_id}-{thread_id}"
        
        # Reset global data
        if chat_thread_key in global_data.topic_admins:
            del global_data.topic_admins[chat_thread_key]
            
        global_data.mongo_config.save_bot_value = AsyncMock()
        
        update = types.Update(
            update_id=3,
            message=types.Message(
                message_id=3,
                date=datetime.datetime.now(),
                chat=types.Chat(id=chat_id, type='supergroup', title="Group"),
                message_thread_id=thread_id,
                from_user=types.User(id=999, is_bot=False, first_name="Admin", username="admin"),
                text="/add_topic_admin @topicadmin"
            )
        )
        
        await dp.feed_update(bot=bot, update=update)
        
        # Verify added
        assert chat_thread_key in global_data.topic_admins
        assert "@topicadmin" in global_data.topic_admins[chat_thread_key]
        
        # Verify reply
        req = next((r for r in mock_server if r["method"] == "sendMessage" and "Added at this thread" in r["data"]["text"]), None)
        assert req is not None

    await bot.session.close()
