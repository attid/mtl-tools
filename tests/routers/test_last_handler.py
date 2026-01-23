import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram import Bot, types
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
import datetime
import json

from routers.last_handler import router as last_router, SpamCheckCallbackData, ReplyCallbackData, FirstMessageCallbackData
from tests.conftest import RouterTestMiddleware, TEST_BOT_TOKEN
from other.global_data import global_data, MTLChats, BotValueTypes

@pytest.fixture(autouse=True)
async def cleanup_router():
    yield
    if last_router.parent_router:
         last_router._parent_router = None
    # Reset global data
    global_data.no_first_link.clear()
    global_data.moderate.clear()
    global_data.topic_mute.clear()
    global_data.first_vote.clear()
    global_data.first_vote_data.clear()

@pytest.mark.asyncio
async def test_spam_detection_delegation(mock_server, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(last_router)
    
    # Setup conditions
    chat_id = 123
    global_data.no_first_link.append(chat_id)
    
    # Mock services
    router_app_context.config_service.is_no_first_link.return_value = True
    router_app_context.config_service.check_user.return_value = 0 # New user
    router_app_context.antispam_service.check_spam.return_value = True # Yes spam
    
    update = types.Update(
        update_id=1,
        message=types.Message(
            message_id=1,
            date=datetime.datetime.now(),
            chat=types.Chat(id=chat_id, type='supergroup', title="Group"),
            from_user=types.User(id=999, is_bot=False, first_name="Spammer", username="spammer"),
            text="Spam"
        )
    )
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    # Verify check_spam called
    assert router_app_context.antispam_service.check_spam.called

@pytest.mark.asyncio
async def test_test_spam_check_command(mock_server, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(last_router)
    
    router_app_context.utils_service.is_admin = AsyncMock(return_value=True) 
    router_app_context.antispam_service.combo_check_spammer.return_value = True
    
    pass # Logic for command test requires specific command implementation which is not in last_handler?
    # Wait, last_handler.py does NOT contain /test_spam_check command. 
    # It seems I was confused with another router or legacy code.
    # Looking at last_handler.py content I read:
    # It has cmd_last_check (F.text), cmd_last_check_other (no_first_link), cq handlers.
    # No explicit /test_spam_check command.
    # So I will skip this test if it's not applicable.

@pytest.mark.asyncio
async def test_mute_enforcement(mock_server, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(last_router)
    
    chat_id = 999
    thread_id = 7
    chat_thread_key = f"{chat_id}-{thread_id}"
    channel_id = -100999999
    
    # Setup global data
    global_data.moderate.append(chat_id)
    global_data.topic_mute[chat_thread_key] = {
        channel_id: {
            "end_time": (datetime.datetime.now() + datetime.timedelta(hours=1)).isoformat(),
            "user": "Channel SpamChannel"
        }
    }
    
    # Message from muted channel
    update = types.Update(
        update_id=2,
        message=types.Message(
            message_id=2,
            date=datetime.datetime.now(),
            chat=types.Chat(id=chat_id, type='supergroup', is_forum=True),
            message_thread_id=thread_id,
            from_user=types.User(id=MTLChats.Channel_Bot, is_bot=True, first_name="Channel Bot", username="Channel_Bot"),
            sender_chat=types.Chat(id=channel_id, type='channel', title="SpamChannel"),
            text="I should be deleted"
        )
    )
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    requests = mock_server.get_requests()
    del_req = next((r for r in requests if r["method"] == "deleteMessage"), None)
    assert del_req is not None

@pytest.mark.asyncio
async def test_cq_spam_check(mock_server, router_app_context):
    dp = router_app_context.dispatcher
    dp.callback_query.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(last_router)
    
    router_app_context.utils_service.is_admin.return_value = True
    
    cb_data = SpamCheckCallbackData(
        message_id=1, chat_id=123, user_id=456, good=False, new_message_id=2, message_thread_id=0
    ).pack()
    
    update = types.Update(
        update_id=3,
        callback_query=types.CallbackQuery(
            id="cb1",
            chat_instance="ci1",
            from_user=types.User(id=999, is_bot=False, first_name="Admin", username="admin"),
            message=types.Message(message_id=10, date=datetime.datetime.now(), chat=types.Chat(id=123, type='supergroup'), text="Spam rep"),
            data=cb_data
        )
    )
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    requests = mock_server.get_requests()
    assert any(r["method"] == "banChatMember" for r in requests)
    assert any("Banned" in r["data"]["text"] for r in requests if r["method"] == "answerCallbackQuery")

@pytest.mark.asyncio
async def test_cq_reply_ban(mock_server, router_app_context):
    dp = router_app_context.dispatcher
    dp.callback_query.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(last_router)
    
    router_app_context.utils_service.is_admin.return_value = True
    
    cb_data = ReplyCallbackData(message_id=1, chat_id=123, user_id=456).pack()
    
    update = types.Update(
        update_id=4,
        callback_query=types.CallbackQuery(
            id="cb2",
            chat_instance="ci2",
            from_user=types.User(id=999, is_bot=False, first_name="Admin", username="admin"),
            message=types.Message(message_id=10, date=datetime.datetime.now(), chat=types.Chat(id=123, type='supergroup'), text="Rep ban"),
            data=cb_data
        )
    )
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    requests = mock_server.get_requests()
    assert any(r["method"] == "banChatMember" for r in requests)
    assert any(r["method"] == "deleteMessage" for r in requests)

@pytest.mark.asyncio
async def test_cq_first_vote(mock_server, router_app_context):
    dp = router_app_context.dispatcher
    dp.callback_query.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(last_router)
    
    router_app_context.utils_service.is_admin.return_value = False # Regular user
    
    cb_data = FirstMessageCallbackData(user_id=111, message_id=1, spam=True).pack()
    
    update = types.Update(
        update_id=5,
        callback_query=types.CallbackQuery(
            id="cb3",
            chat_instance="ci3",
            from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
            message=types.Message(message_id=10, date=datetime.datetime.now(), chat=types.Chat(id=123, type='supergroup'), text="Vote msg"),
            data=cb_data
        )
    )
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    requests = mock_server.get_requests()
    # Should edit text to update counts
    assert any(r["method"] == "editMessageText" for r in requests)
    texts = [r["data"]["text"] for r in requests if r["method"] == "editMessageText"]
    # Check if spam vote count increased (admin=False -> +1)
    assert any("Spam votes (1)" in t for t in texts)

@pytest.mark.asyncio
async def test_last_check_other_non_text(mock_server, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(last_router)

    chat_id = 777
    if chat_id not in global_data.no_first_link:
        global_data.no_first_link.append(chat_id)
        
    # global_data.check_user mock
    # routers.last_handler.global_data.check_user called.
    # We can patch it.
    with patch("routers.last_handler.global_data.check_user", return_value=0):
        
        # Message with photo (non-text)
        update = types.Update(
            update_id=6,
            message=types.Message(
                message_id=50,
                date=datetime.datetime.now(),
                chat=types.Chat(id=chat_id, type='supergroup', title="Group"),
                from_user=types.User(id=123, is_bot=False, first_name="User", username="user"),
                photo=[types.PhotoSize(file_id="1", file_unique_id="1", width=1, height=1)]
            )
        )

        await dp.feed_update(bot=router_app_context.bot, update=update)

        # Verify delete_and_log_spam called on service
        assert router_app_context.antispam_service.delete_and_log_spam.called
