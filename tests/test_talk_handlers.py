
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from aiogram import Bot, types, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.dispatcher.middlewares.base import BaseMiddleware
import datetime

from routers.talk_handlers import router as talk_router
from tests.conftest import MOCK_SERVER_URL, TEST_BOT_TOKEN
from other.global_data import global_data, MTLChats

class MockDbMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        data["session"] = MagicMock()
        return await handler(event, data)

@pytest.fixture(autouse=True)
async def cleanup_router():
    yield
    if talk_router.parent_router:
         talk_router._parent_router = None

@pytest.mark.asyncio
async def test_skynet_command(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(MOCK_SERVER_URL)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(talk_router)
    dp.message.middleware(MockDbMiddleware()) # Session required for log middleware often attached

    # Mock talk function
    with patch("routers.talk_handlers.talk", new_callable=AsyncMock) as mock_talk:
        mock_talk.return_value = "I am Skynet"
        
        update = types.Update(
            update_id=1,
            message=types.Message(
                message_id=1,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='private'),
                from_user=types.User(id=123, is_bot=False, first_name="User", username="user"),
                text="/skynet hello"
            )
        )
        
        await dp.feed_update(bot=bot, update=update)
        
        # Verify talk called
        mock_talk.assert_called_once()
        
        # Verify response
        msg_req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
        assert msg_req is not None
        assert "I am Skynet" in msg_req["data"]["text"]

    await bot.session.close()

@pytest.mark.asyncio
async def test_img_command(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(MOCK_SERVER_URL)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(talk_router)
    dp.message.middleware(MockDbMiddleware())

    # Add user to skynet_img allowed list
    global_data.skynet_img.append("@user")

    t_user = types.User(id=123, is_bot=False, first_name="User", username="user")

    with patch("routers.talk_handlers.generate_image", new_callable=AsyncMock) as mock_gen, \
         patch("routers.talk_handlers.URLInputFile", side_effect=lambda url, filename=None: url): # Mock input file wrapper
        
        mock_gen.return_value = ["http://example.com/image.png"]
        
        update = types.Update(
            update_id=2,
            message=types.Message(
                message_id=2,
                date=datetime.datetime.now(),
                chat=types.Chat(id=456, type='supergroup', title="Group"),
                from_user=t_user,
                text="/img cat"
            )
        )
        
        await dp.feed_update(bot=bot, update=update)
        
        # Verify generate_image called
        mock_gen.assert_called_once()
        
        # Verify sendPhoto
        photo_req = next((r for r in mock_server if r["method"] == "sendPhoto"), None)
        assert photo_req is not None
        # In mock server sendPhoto adds data['photo'] = [], but input was url string
        # aiogram might send it as string in 'photo' field of multipart or json
        # Our mock server implementation of sendPhoto puts incoming data into 'data' key of request log
        # key 'photo' in 'data' dictionary should correspond to the url if json, or field if multipart
        # aiogram uses multipart for files usually. 
        # But wait, URLInputFile might trigger a logic that sends it as URL string if detected?
        # Actually URLInputFile is strictly for wrapping. 
        # If we passed just string "http://..." it would be string. 
        # Let's verify that request reached server.
        
    await bot.session.close()

@pytest.mark.asyncio
async def test_comment_command(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(MOCK_SERVER_URL)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(talk_router)
    dp.message.middleware(MockDbMiddleware())

    with patch("routers.talk_handlers.talk_get_comment", new_callable=AsyncMock) as mock_comment:
        mock_comment.return_value = "Nice photo!"
        
        # Original message to reply to
        reply_msg = types.Message(
            message_id=5,
            date=datetime.datetime.now(),
            chat=types.Chat(id=456, type='supergroup', title="Group"),
            from_user=types.User(id=789, is_bot=False, first_name="Other", username="other"),
            text="Check this out"
        )
        
        update = types.Update(
            update_id=3,
            message=types.Message(
                message_id=6,
                date=datetime.datetime.now(),
                chat=types.Chat(id=456, type='supergroup', title="Group"),
                from_user=types.User(id=123, is_bot=False, first_name="User", username="user"),
                text="/comment",
                reply_to_message=reply_msg
            )
        )
        
        await dp.feed_update(bot=bot, update=update)
        
        # Verify comment generation called
        mock_comment.assert_called_once()
        
        # Verify reply
        msg_req = next((r for r in mock_server if r["method"] == "sendMessage" and "Nice photo!" in r["data"]["text"]), None)
        assert msg_req is not None
        # Check reply parameters string for message_id: 5
        assert '"message_id": 5' in msg_req["data"].get("reply_parameters", "")

    await bot.session.close()

