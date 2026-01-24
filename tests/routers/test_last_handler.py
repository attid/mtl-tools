import pytest
import datetime
from datetime import timedelta
import json
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram import Bot, types
from aiogram.types import Message, Chat, User, ReplyParameters
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer

from routers.last_handler import router as last_router, SpamCheckCallbackData, ReplyCallbackData, FirstMessageCallbackData, cmd_last_check
from tests.conftest import RouterTestMiddleware, TEST_BOT_TOKEN
from other.global_data import global_data, MTLChats, BotValueTypes

# --- Existing Tests (Router Integration) ---

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
    global_data.reply_only.clear()
    global_data.listen.clear()
    global_data.notify_message.clear()

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
    assert any(r["method"] == "editMessageText" for r in requests)
    texts = [r["data"]["text"] for r in requests if r["method"] == "editMessageText"]
    assert any("Spam votes (1)" in t for t in texts)

@pytest.mark.asyncio
async def test_last_check_other_non_text(mock_server, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(last_router)

    chat_id = 777
    if chat_id not in global_data.no_first_link:
        global_data.no_first_link.append(chat_id)
        
    with patch("routers.last_handler.global_data.check_user", return_value=0):
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

        assert router_app_context.antispam_service.delete_and_log_spam.called

# --- E2E Unit Tests (Direct Handler Call) ---

@pytest.fixture
def mock_bot():
    bot = AsyncMock(spec=Bot)
    bot.ban_chat_member = AsyncMock()
    bot.send_message = AsyncMock()
    bot.restrict_chat_member = AsyncMock()
    bot.delete_message = AsyncMock()
    bot.forward_message = AsyncMock()
    bot.edit_message_text = AsyncMock()
    bot.get_chat_member = AsyncMock()
    return bot

@pytest.fixture
def mock_session():
    return MagicMock()

@pytest.fixture
def mock_state():
    state = AsyncMock()
    state.get_data.return_value = {}
    return state

@pytest.fixture
def mock_app_context():
    app_context = MagicMock()
    app_context.antispam_service = AsyncMock()
    app_context.utils_service = AsyncMock()
    app_context.config_service = MagicMock() # Sync methods mock
    app_context.antispam_service.check_spam.return_value = False
    return app_context

@pytest.fixture
def message_event():
    user = User(id=123, is_bot=False, first_name="Test", last_name="User", username="testuser")
    chat = Chat(id=-1001, type="supergroup", title="Test Chat")
    message = Message(
        message_id=999,
        date=datetime.datetime.now(),
        chat=chat,
        from_user=user,
        text="Hello world"
    )
    return message

@pytest.fixture
def patch_message_methods():
    with patch('aiogram.types.Message.delete', new_callable=AsyncMock) as mock_delete, \
         patch('aiogram.types.Message.reply', new_callable=AsyncMock) as mock_reply, \
         patch('aiogram.types.Message.answer', new_callable=AsyncMock) as mock_answer, \
         patch('aiogram.types.Message.forward', new_callable=AsyncMock) as mock_forward, \
         patch('aiogram.types.Message.copy_to', new_callable=AsyncMock) as mock_copy_to:
        yield {
            'delete': mock_delete,
            'reply': mock_reply,
            'answer': mock_answer,
            'forward': mock_forward,
            'copy_to': mock_copy_to
        }

@pytest.mark.asyncio
async def test_spam_check_blocked(message_event, mock_session, mock_bot, mock_state, mock_app_context, patch_message_methods):
    if message_event.chat.id not in global_data.no_first_link:
        global_data.no_first_link.append(message_event.chat.id)
    
    mock_app_context.antispam_service.check_spam.return_value = True
    
    await cmd_last_check(message_event, mock_session, mock_bot, mock_state, app_context=mock_app_context)
    
    mock_app_context.antispam_service.check_spam.assert_awaited_once_with(message_event)
    patch_message_methods['reply'].assert_not_awaited()
    
    if message_event.chat.id in global_data.no_first_link:
        global_data.no_first_link.remove(message_event.chat.id)

@pytest.mark.asyncio
async def test_spam_check_passed(message_event, mock_session, mock_bot, mock_state, mock_app_context, patch_message_methods):
    if message_event.chat.id not in global_data.no_first_link:
        global_data.no_first_link.append(message_event.chat.id)
    if message_event.chat.id not in global_data.listen:
        global_data.listen.append(message_event.chat.id)
        
    mock_app_context.antispam_service.check_spam.return_value = False
    
    with patch('routers.last_handler.MessageRepository') as MockRepo:
        await cmd_last_check(message_event, mock_session, mock_bot, mock_state, app_context=mock_app_context)
        MockRepo.return_value.save_message.assert_called() 

    if message_event.chat.id in global_data.no_first_link:
        global_data.no_first_link.remove(message_event.chat.id)
    if message_event.chat.id in global_data.listen:
        global_data.listen.remove(message_event.chat.id)

@pytest.mark.asyncio
async def test_mute_check_active(message_event, mock_session, mock_bot, mock_state, mock_app_context, patch_message_methods):
    if message_event.chat.id not in global_data.moderate:
        global_data.moderate.append(message_event.chat.id)
        
    chat_thread_key = f"{message_event.chat.id}-None"
    
    future_time = (datetime.datetime.now() + datetime.timedelta(minutes=10)).isoformat()
    global_data.topic_mute[chat_thread_key] = {
        message_event.from_user.id: {"end_time": future_time}
    }
    
    await cmd_last_check(message_event, mock_session, mock_bot, mock_state, app_context=mock_app_context)
    
    patch_message_methods['delete'].assert_awaited_once()
    
    if message_event.chat.id in global_data.moderate:
        global_data.moderate.remove(message_event.chat.id)
    del global_data.topic_mute[chat_thread_key]

@pytest.mark.asyncio
async def test_mute_check_expired(message_event, mock_session, mock_bot, mock_state, mock_app_context, patch_message_methods):
    if message_event.chat.id not in global_data.moderate:
        global_data.moderate.append(message_event.chat.id)
        
    chat_thread_key = f"{message_event.chat.id}-None"
    
    past_time = (datetime.datetime.now() - datetime.timedelta(minutes=10)).isoformat()
    global_data.topic_mute[chat_thread_key] = {
        message_event.from_user.id: {"end_time": past_time}
    }
    
    await cmd_last_check(message_event, mock_session, mock_bot, mock_state, app_context=mock_app_context)
    
    patch_message_methods['delete'].assert_not_awaited()
    assert message_event.from_user.id not in global_data.topic_mute.get(chat_thread_key, {})
    
    if message_event.chat.id in global_data.moderate:
        global_data.moderate.remove(message_event.chat.id)
    if chat_thread_key in global_data.topic_mute:
        del global_data.topic_mute[chat_thread_key]

@pytest.mark.asyncio
async def test_reply_only_violation(message_event, mock_session, mock_bot, mock_state, mock_app_context, patch_message_methods):
    if message_event.chat.id not in global_data.reply_only:
        global_data.reply_only.append(message_event.chat.id)
        
    await cmd_last_check(message_event, mock_session, mock_bot, mock_state, app_context=mock_app_context)
    
    patch_message_methods['reply'].assert_awaited_once()
    assert "режим контроля использования функции ответа" in patch_message_methods['reply'].call_args[0][0]

    if message_event.chat.id in global_data.reply_only:
        global_data.reply_only.remove(message_event.chat.id)

@pytest.mark.asyncio
async def test_reply_only_allowed(message_event, mock_session, mock_bot, mock_state, mock_app_context, patch_message_methods):
    if message_event.chat.id not in global_data.reply_only:
        global_data.reply_only.append(message_event.chat.id)
        
    reply_msg = Message(message_id=1, date=datetime.datetime.now(), chat=message_event.chat, text="Original")
    new_message = Message(
        message_id=message_event.message_id,
        date=message_event.date,
        chat=message_event.chat,
        from_user=message_event.from_user,
        text="Reply",
        reply_to_message=reply_msg
    )
    
    with patch('routers.last_handler.MessageRepository') as MockRepo:
        await cmd_last_check(new_message, mock_session, mock_bot, mock_state, app_context=mock_app_context)
        MockRepo.return_value.save_message.assert_called()
    
    patch_message_methods['reply'].assert_not_awaited()

    if message_event.chat.id in global_data.reply_only:
        global_data.reply_only.remove(message_event.chat.id)

@pytest.mark.asyncio
async def test_community_vote_prompt(message_event, mock_session, mock_bot, mock_state, mock_app_context, patch_message_methods):
    global_data.add_user(message_event.from_user.id, 0)
    
    if message_event.chat.id not in global_data.first_vote:
        global_data.first_vote.append(message_event.chat.id)
    
    await cmd_last_check(message_event, mock_session, mock_bot, mock_state, app_context=mock_app_context)
    
    patch_message_methods['reply'].assert_awaited_once()
    args = patch_message_methods['reply'].call_args
    text = args[1].get('text') if args[1].get('text') else (args[0][0] if args[0] else "")
    assert "Please help me detect spam messages" in text

    if message_event.chat.id in global_data.first_vote:
        global_data.first_vote.remove(message_event.chat.id)
    global_data.add_user(message_event.from_user.id, -1)

@pytest.mark.asyncio
async def test_notify_message(message_event, mock_session, mock_bot, mock_state, mock_app_context, patch_message_methods):
    dest_chat_id = -100555
    global_data.notify_message[message_event.chat.id] = f"{dest_chat_id}"
    
    from aiogram.types.base import TelegramObject
    from unittest.mock import PropertyMock
    
    with patch.object(TelegramObject, 'bot', new_callable=PropertyMock) as mock_bot_prop:
        mock_bot_prop.return_value = mock_bot
        mock_bot.get_chat_member.return_value.status = 'member'
        
        await cmd_last_check(message_event, mock_session, mock_bot, mock_state, app_context=mock_app_context)
    
    mock_bot.send_message.assert_awaited()
    call_args = mock_bot.send_message.call_args
    assert call_args[1].get('chat_id') == dest_chat_id or call_args[1].get('chat_id') == str(dest_chat_id)
    
    del global_data.notify_message[message_event.chat.id]
