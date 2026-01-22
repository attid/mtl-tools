
import pytest
from aiogram import Bot, Dispatcher, types
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.filters import CommandStart
from unittest.mock import patch, AsyncMock, MagicMock
import datetime

from routers.start_router import router as start_router
from tests.conftest import TEST_BOT_TOKEN, MockDbMiddleware

@pytest.fixture(autouse=True)
async def cleanup_router():
    # Only if we need to detach manually. 
    # But easier is to reset _parent_router on the router object if accessible.
    yield
    if start_router.parent_router:
         start_router._parent_router = None

@pytest.mark.asyncio
async def test_start_command(mock_server, dp):
    """
    Test /start command.
    """
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    
    # Add Middleware
    dp.message.middleware(MockDbMiddleware())
    
    dp.include_router(start_router)
    
    # Mock db_save_bot_user
    with patch("routers.start_router.db_save_bot_user") as mock_save:
        
        # Simulate /start message
        update = types.Update(
            update_id=1,
            message=types.Message(
                message_id=1,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='private'),
                from_user=types.User(id=123, is_bot=False, first_name="Test", username="test"),
                text="/start"
            )
        )
        
        await dp.feed_update(bot=bot, update=update)
        
        # Verify
        req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
        assert req is not None
        assert "Привет, я бот из" in req["data"]["text"]
        
        mock_save.assert_called_once()

    await bot.session.close()

@pytest.mark.asyncio
async def test_links_command(mock_server, dp):
    """
    Test /links command.
    """
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    
    # Add Middleware
    dp.message.middleware(MockDbMiddleware())
    
    dp.include_router(start_router)
    
    update = types.Update(
        update_id=2,
        message=types.Message(
            message_id=2,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='private'),
            from_user=types.User(id=123, is_bot=False, first_name="Test", username="test"),
            text="/links"
        )
    )
    
    await dp.feed_update(bot=bot, update=update)
    
    req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
    assert req is not None
    assert "Полезные ссылки" in req["data"]["text"]

    await bot.session.close()

@pytest.mark.asyncio
async def test_emoji_command_no_args(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(start_router)
    dp.message.middleware(MockDbMiddleware())

    update = types.Update(
        update_id=3,
        message=types.Message(
            message_id=3,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='private'),
            from_user=types.User(id=123, is_bot=False, first_name="Test", username="test"),
            text="/emoji"
        )
    )

    await dp.feed_update(bot=bot, update=update)

    req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
    assert req is not None
    assert "Используйте: /emoji" in req["data"]["text"]

    await bot.session.close()

@pytest.mark.asyncio
async def test_emoji_command_all(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(start_router)
    dp.message.middleware(MockDbMiddleware())

    update = types.Update(
        update_id=4,
        message=types.Message(
            message_id=4,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='private'),
            from_user=types.User(id=123, is_bot=False, first_name="Test", username="test"),
            text="/emoji all"
        )
    )

    await dp.feed_update(bot=bot, update=update)

    req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
    assert req is not None
    assert "Доступные эмодзи" in req["data"]["text"]

    await bot.session.close()

@pytest.mark.asyncio
async def test_emoji_command_reaction(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(start_router)
    dp.message.middleware(MockDbMiddleware())

    update = types.Update(
        update_id=5,
        message=types.Message(
            message_id=5,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='private'),
            from_user=types.User(id=123, is_bot=False, first_name="Test", username="test"),
            text="/emoji https://t.me/123/456 👀"
        )
    )

    await dp.feed_update(bot=bot, update=update)

    req_reaction = next((r for r in mock_server if r["method"] == "setMessageReaction"), None)
    assert req_reaction is not None

    req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
    assert req is not None
    assert "Реакция 👀 добавлена" in req["data"]["text"]

    await bot.session.close()

@pytest.mark.asyncio
async def test_save_command_admin(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(start_router)

    update = types.Update(
        update_id=6,
        message=types.Message(
            message_id=6,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='private'),
            from_user=types.User(id=84131737, is_bot=False, first_name="Admin", username="admin"),
            text="/save"
        )
    )

    await dp.feed_update(bot=bot, update=update)

    req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
    assert req is not None
    assert req["data"]["text"] == "Готово"

    await bot.session.close()

@pytest.mark.asyncio
async def test_save_command_user(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(start_router)

    update = types.Update(
        update_id=7,
        message=types.Message(
            message_id=7,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='private'),
            from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
            text="/save"
        )
    )

    await dp.feed_update(bot=bot, update=update)

    req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
    assert req is not None
    assert req["data"]["text"] == "Saved"

    await bot.session.close()

@pytest.mark.asyncio
async def test_show_id_command(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(start_router)

    update = types.Update(
        update_id=8,
        message=types.Message(
            message_id=8,
            date=datetime.datetime.now(),
            chat=types.Chat(id=456, type='private'),
            from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
            text="/show_id"
        )
    )

    await dp.feed_update(bot=bot, update=update)

    req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
    assert req is not None
    assert "chat_id = 456" in req["data"]["text"]

    await bot.session.close()

@pytest.mark.asyncio
async def test_me_command(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(start_router)

    update = types.Update(
        update_id=9,
        message=types.Message(
            message_id=9,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='supergroup'),
            from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
            text="/me hello"
        )
    )

    await dp.feed_update(bot=bot, update=update)

    req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
    assert req is not None
    assert "user" in req["data"]["text"]
    assert "hello" in req["data"]["text"]

    req_delete = next((r for r in mock_server if r["method"] == "deleteMessage"), None)
    assert req_delete is not None

    await bot.session.close()

@pytest.mark.asyncio
async def test_link_command_requires_reply(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(start_router)

    update = types.Update(
        update_id=10,
        message=types.Message(
            message_id=10,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='supergroup'),
            from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
            text="/link"
        )
    )

    await dp.feed_update(bot=bot, update=update)

    req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
    assert req is not None
    assert "Эта команда должна быть использована" in req["data"]["text"]

    await bot.session.close()

@pytest.mark.asyncio
async def test_link_command_reply_with_addresses(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(start_router)

    addr1 = "G" + "A" * 55
    addr2 = "G" + "B" * 55
    reply_text = f"addr {addr1} other {addr2} {addr1}"

    update = types.Update(
        update_id=11,
        message=types.Message(
            message_id=11,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='supergroup'),
            from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
            text="/link",
            reply_to_message=types.Message(
                message_id=10,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup'),
                from_user=types.User(id=888, is_bot=False, first_name="User2", username="user2"),
                text=reply_text
            )
        )
    )

    await dp.feed_update(bot=bot, update=update)

    req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
    assert req is not None
    assert "viewer.eurmtl.me" in req["data"]["text"]
    assert "bsn.expert" in req["data"]["text"]

    await bot.session.close()
