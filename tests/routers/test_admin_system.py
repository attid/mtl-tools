import pytest
import os
import hashlib
import json
from unittest.mock import MagicMock, AsyncMock
from aiogram import types, Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from routers.admin_system import router as admin_router
from tests.conftest import RouterTestMiddleware, create_message_update
from other.global_data import MTLChats, global_data
import datetime
from io import BytesIO

@pytest.fixture(autouse=True)
async def cleanup_router():
    yield
    if admin_router.parent_router:
         admin_router._parent_router = None
    
    # Cleanup state
    global_data.skynet_admins.clear()
    if "skynet.log" in os.listdir("."):
        # We might have created it. But avoid deleting real logs if running on real env.
        # Check if size is small (dummy)
        if os.path.exists("skynet.log") and os.path.getsize("skynet.log") < 100:
             os.remove("skynet.log")

@pytest.mark.asyncio
async def test_sha256_command(mock_server, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
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
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    requests = mock_server.get_requests()
    msg_req = next((r for r in requests if r["method"] == "sendMessage"), None)
    assert msg_req is not None
    assert expected_hash in msg_req["data"]["text"]

@pytest.mark.asyncio
async def test_log_command(mock_server, router_app_context):
    global_data.skynet_admins = ["@admin"]
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(admin_router)
    
    # create dummy log file
    with open("skynet.log", "w") as f:
        f.write("dummy log content")
        
    update = types.Update(
        update_id=3,
        message=types.Message(
            message_id=3,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='private'),
            from_user=types.User(id=MTLChats.ITolstov, is_bot=False, first_name="Admin", username="admin"),
            text="/log"
        )
    )
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    requests = mock_server.get_requests()
    doc_req = next((r for r in requests if r["method"] == "sendDocument"), None)
    assert doc_req is not None

@pytest.mark.asyncio
async def test_ping_piro(mock_server, router_app_context):
    global_data.skynet_admins = ["@admin"]
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(admin_router)
    
    # Mock group_service.ping_piro
    router_app_context.group_service.ping_piro = AsyncMock()
    
    update = types.Update(
        update_id=6,
        message=types.Message(
            message_id=6,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='private'),
            from_user=types.User(id=MTLChats.ITolstov, is_bot=False, first_name="Admin", username="admin"),
            text="/ping_piro"
        )
    )
    
    print(f"DEBUG: ITolstov={MTLChats.ITolstov}")
    print(f"DEBUG: Message User ID={update.message.from_user.id}")
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    assert router_app_context.group_service.ping_piro.called

@pytest.mark.asyncio
async def test_grist_command(mock_server, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(admin_router)
    
    # Mock grist service
    router_app_context.grist_service.load_table_data.return_value = [
        {"user_id": MTLChats.ITolstov, "id": 1, "fields": {}}
    ]
    router_app_context.grist_service.patch_data = AsyncMock()
    
    update = types.Update(
        update_id=12,
        message=types.Message(
            message_id=12,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='private'),
            from_user=types.User(id=MTLChats.ITolstov, is_bot=False, first_name="User", username="user"),
            text="/grist"
        )
    )
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    requests = mock_server.get_requests()
    msg_req = next((r for r in requests if r["method"] == "sendMessage"), None)
    assert msg_req is not None
    assert "новый ключ" in msg_req["data"]["text"].lower()
    
    assert router_app_context.grist_service.patch_data.called

@pytest.mark.asyncio
async def test_update_mtlap(mock_server, router_app_context):
    global_data.skynet_admins = ["@admin"]
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(admin_router)
    
    # Mock gspread and mtl services
    # Dummy data: Headers + 1 row
    # Headers must have len >= 15, index 1 = "TGID", index 14 = "SkyNet"
    headers = [""] * 20
    headers[1] = "TGID"
    headers[14] = "SkyNet"
    row = [""] * 20
    row[1] = "12345"
    
    router_app_context.gspread_service.get_all_mtlap.return_value = [headers, row, row]
    router_app_context.gspread_service.get_update_mtlap_skynet_row = AsyncMock()
    router_app_context.mtl_service.check_consul_mtla_chats.return_value = ["Chat updated"]
    
    update = types.Update(
        update_id=13,
        message=types.Message(
            message_id=13,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='private'),
            from_user=types.User(id=MTLChats.ITolstov, is_bot=False, first_name="Admin", username="admin"),
            text="/update_mtlap"
        )
    )
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    requests = mock_server.get_requests()
    # Check for "Готово 1", "Chat updated", "Готово 2"
    messages = [r["data"]["text"] for r in requests if r["method"] == "sendMessage"]
    assert "Готово 1" in messages
    assert "Chat updated" in messages
    assert "Готово 2" in messages

@pytest.mark.asyncio
async def test_sha1_command(mock_server, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(admin_router)
    
    # Mock bot.download directly on the instance
    file_bytes = b"test"
    router_app_context.bot.download = AsyncMock(return_value=BytesIO(file_bytes))
    
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
                file_size=len(file_bytes),
                mime_type="text/plain"
            )
        )
    )
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    requests = mock_server.get_requests()
    msg_req = next((r for r in requests if r["method"] == "sendMessage"), None)
    assert msg_req is not None
    assert "SHA-1" in msg_req["data"]["text"]

@pytest.mark.asyncio
async def test_exit_command(mock_server, router_app_context):
    global_data.skynet_admins = ["@admin"]
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(admin_router)
    
    # First call sets state
    update = types.Update(
        update_id=4,
        message=types.Message(
            message_id=4,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='private'),
            from_user=types.User(id=MTLChats.ITolstov, is_bot=False, first_name="Admin", username="admin"),
            text="/exit"
        )
    )
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    requests = mock_server.get_requests()
    msg_req = next((r for r in requests if r["method"] == "sendMessage"), None)
    assert msg_req is not None
    assert "боюсь" in msg_req["data"]["text"]
    
    # Second call triggers exit
    # We expect SystemExit
    with pytest.raises(SystemExit):
        await dp.feed_update(bot=router_app_context.bot, update=update)
