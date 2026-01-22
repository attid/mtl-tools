
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from aiogram import Bot, types, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.fsm.storage.memory import MemoryStorage
import datetime
import hashlib
from io import BytesIO

from routers.admin_system import router as admin_router
from tests.conftest import TEST_BOT_TOKEN
from other.global_data import MTLChats, global_data

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
async def test_sha256_command(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(admin_router)
    
    test_str = "test_string"
    expected_hash = hashlib.sha256(test_str.encode()).hexdigest()
    
    update = types.Update(
        update_id=1,
        message=types.Message(
            message_id=1,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='private'),
            from_user=types.User(id=123, is_bot=False, first_name="User", username="user"),
            text=f"/sha256 {test_str}"
        )
    )
    
    await dp.feed_update(bot=bot, update=update)
    
    msg_req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
    assert msg_req is not None
    assert expected_hash in msg_req["data"]["text"]

    await bot.session.close()

@pytest.mark.asyncio
async def test_eurmtl_command(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(admin_router)
    
    update = types.Update(
        update_id=2,
        message=types.Message(
            message_id=2,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='private'),
            from_user=types.User(id=123, is_bot=False, first_name="User", username="user"),
            text="/eurmtl"
        )
    )
    
    await dp.feed_update(bot=bot, update=update)
    
    msg_req = next((r for r in mock_server if r["method"] == "sendMessage" and "Click the button below" in r["data"]["text"]), None)
    assert msg_req is not None
    assert "reply_markup" in msg_req["data"]

    await bot.session.close()

@pytest.mark.asyncio
async def test_log_command(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(admin_router)
    
    # Mock is_skynet_admin, os.path.isfile, os.path.getsize
    # Mock FSInputFile to return a string, so aiogram treats it as file_id and doesn't try to open file
    with patch("routers.admin_system.is_skynet_admin", return_value=True), \
         patch("routers.admin_system.os.path.isfile", return_value=True), \
         patch("routers.admin_system.os.path.getsize", return_value=100), \
         patch("routers.admin_system.FSInputFile", return_value="mock_file_id"):
        
        update = types.Update(
            update_id=3,
            message=types.Message(
                message_id=3,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='private'),
                from_user=types.User(id=999, is_bot=False, first_name="Admin", username="admin"),
                text="/log"
            )
        )
        
        await dp.feed_update(bot=bot, update=update)
        
        doc_req = next((r for r in mock_server if r["method"] == "sendDocument"), None)
        assert doc_req is not None
        # We can't verify the file content easily as it's mocked, but we verify method call

    await bot.session.close()

@pytest.mark.asyncio
async def test_exit_command_not_admin(mock_server):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(admin_router)

    with patch("routers.admin_system.is_skynet_admin", return_value=False):
        update = types.Update(
            update_id=4,
            message=types.Message(
                message_id=4,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='private'),
                from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                text="/exit"
            )
        )

        await dp.feed_update(bot=bot, update=update)

        msg_req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
        assert msg_req is not None
        assert "You are not my admin" in msg_req["data"]["text"]

    await bot.session.close()

@pytest.mark.asyncio
async def test_err_command_file_missing(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(admin_router)

    with patch("routers.admin_system.is_skynet_admin", return_value=True), \
         patch("routers.admin_system.os.path.isfile", return_value=False):
        update = types.Update(
            update_id=5,
            message=types.Message(
                message_id=5,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='private'),
                from_user=types.User(id=999, is_bot=False, first_name="Admin", username="admin"),
                text="/err"
            )
        )

        await dp.feed_update(bot=bot, update=update)

        msg_req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
        assert msg_req is not None
        assert "не найден" in msg_req["data"]["text"]

    await bot.session.close()

@pytest.mark.asyncio
async def test_ping_piro_not_admin(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(admin_router)

    with patch("routers.admin_system.is_skynet_admin", return_value=False):
        update = types.Update(
            update_id=6,
            message=types.Message(
                message_id=6,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='private'),
                from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                text="/ping_piro"
            )
        )

        await dp.feed_update(bot=bot, update=update)

        msg_req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
        assert msg_req is not None
        assert "You are not my admin" in msg_req["data"]["text"]

    await bot.session.close()

@pytest.mark.asyncio
async def test_summary_not_admin(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(admin_router)
    dp.message.middleware(MockDbMiddleware())

    with patch("routers.admin_system.is_skynet_admin", return_value=False):
        update = types.Update(
            update_id=7,
            message=types.Message(
                message_id=7,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup', title="Group"),
                from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                text="/summary"
            )
        )

        await dp.feed_update(bot=bot, update=update)

        msg_req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
        assert msg_req is not None
        assert "You are not my admin" in msg_req["data"]["text"]

    await bot.session.close()

@pytest.mark.asyncio
async def test_sha1_command(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(admin_router)

    file_bytes = b"test"
    with patch.object(bot, "download", new_callable=AsyncMock, return_value=BytesIO(file_bytes)):
        update = types.Update(
            update_id=8,
            message=types.Message(
                message_id=8,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='private'),
                from_user=types.User(id=123, is_bot=False, first_name="User", username="user"),
                document=types.Document(
                    file_id="1",
                    file_unique_id="1",
                    file_name="test.txt",
                    file_size=len(file_bytes)
                )
            )
        )

        await dp.feed_update(bot=bot, update=update)

        msg_req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
        assert msg_req is not None
        assert "SHA-1" in msg_req["data"]["text"]

    await bot.session.close()

@pytest.mark.asyncio
async def test_sync_post_not_admin(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(admin_router)

    with patch("routers.admin_system.is_admin", new_callable=AsyncMock, return_value=False):
        update = types.Update(
            update_id=9,
            message=types.Message(
                message_id=9,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup', title="Group"),
                from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                text="/sync"
            )
        )

        await dp.feed_update(bot=bot, update=update)

        msg_req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
        assert msg_req is not None
        assert "You are not admin" in msg_req["data"]["text"]

    await bot.session.close()

@pytest.mark.asyncio
async def test_resync_post_not_admin(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(admin_router)
    dp.message.middleware(MockDbMiddleware())

    with patch("routers.admin_system.is_admin", new_callable=AsyncMock, return_value=False):
        update = types.Update(
            update_id=10,
            message=types.Message(
                message_id=10,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup', title="Group"),
                from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                text="/resync"
            )
        )

        await dp.feed_update(bot=bot, update=update)

        msg_req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
        assert msg_req is not None
        assert "You are not admin" in msg_req["data"]["text"]

    await bot.session.close()

@pytest.mark.asyncio
async def test_edited_channel_post_sync(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(admin_router)

    global_data.sync = {123: {"10": [{"chat_id": 456, "message_id": 99, "url": "https://t.me/c/123/10"}]}}

    update = types.Update(
        update_id=11,
        edited_channel_post=types.Message(
            message_id=10,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='channel', title="Channel"),
            from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
            text="Edited*"
        )
    )

    await dp.feed_update(bot=bot, update=update)

    req = next((r for r in mock_server if r["method"] == "editMessageText"), None)
    assert req is not None

    await bot.session.close()

@pytest.mark.asyncio
async def test_grist_command_no_access(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(admin_router)

    with patch("routers.admin_system.grist_manager.load_table_data", new_callable=AsyncMock, return_value=[]):
        update = types.Update(
            update_id=12,
            message=types.Message(
                message_id=12,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='private'),
                from_user=types.User(id=123, is_bot=False, first_name="User", username="user"),
                text="/grist"
            )
        )

        await dp.feed_update(bot=bot, update=update)

        msg_req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
        assert msg_req is not None
        assert "нет доступа" in msg_req["data"]["text"].lower()

    await bot.session.close()

@pytest.mark.asyncio
async def test_update_mtlap_not_admin(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(admin_router)

    with patch("routers.admin_system.is_skynet_admin", return_value=False):
        update = types.Update(
            update_id=13,
            message=types.Message(
                message_id=13,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='private'),
                from_user=types.User(id=123, is_bot=False, first_name="User", username="user"),
                text="/update_mtlap"
            )
        )

        await dp.feed_update(bot=bot, update=update)

        msg_req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
        assert msg_req is not None
        assert "You are not my admin" in msg_req["data"]["text"]

    await bot.session.close()

@pytest.mark.asyncio
async def test_update_chats_info_not_admin(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(admin_router)

    with patch("routers.admin_system.is_skynet_admin", return_value=False):
        update = types.Update(
            update_id=14,
            message=types.Message(
                message_id=14,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='private'),
                from_user=types.User(id=123, is_bot=False, first_name="User", username="user"),
                text="/update_chats_info"
            )
        )

        await dp.feed_update(bot=bot, update=update)

        msg_req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
        assert msg_req is not None
        assert "You are not my admin" in msg_req["data"]["text"]

    await bot.session.close()

@pytest.mark.asyncio
async def test_push_requires_reply(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(admin_router)

    with patch("routers.admin_system.is_skynet_admin", return_value=True):
        update = types.Update(
            update_id=15,
            message=types.Message(
                message_id=15,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='private'),
                from_user=types.User(id=123, is_bot=False, first_name="User", username="user"),
                text="/push"
            )
        )

        await dp.feed_update(bot=bot, update=update)

        msg_req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
        assert msg_req is not None
        assert "Команду надо посылать" in msg_req["data"]["text"]

    await bot.session.close()

@pytest.mark.asyncio
async def test_get_info_not_admin(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(admin_router)

    with patch("routers.admin_system.is_skynet_admin", return_value=False):
        update = types.Update(
            update_id=16,
            message=types.Message(
                message_id=16,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='private'),
                from_user=types.User(id=123, is_bot=False, first_name="User", username="user"),
                text="/get_info 123"
            )
        )

        await dp.feed_update(bot=bot, update=update)

        msg_req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
        assert msg_req is not None
        assert "You are not my admin" in msg_req["data"]["text"]

    await bot.session.close()
