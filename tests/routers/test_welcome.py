import pytest
import datetime
import json
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram import Bot, types
from aiogram.enums import ChatMemberStatus
from aiogram.types import ChatMemberUpdated, User, Chat, ChatMemberOwner, Message
from loguru import logger

from routers.welcome import router as welcome_router, CaptchaCallbackData, JoinCallbackData, emoji_pairs, new_chat_member
from tests.conftest import RouterTestMiddleware, TEST_BOT_TOKEN
from other.global_data import global_data, MTLChats, BotValueTypes

# --- Existing Tests (Router Integration) ---

@pytest.fixture(autouse=True)
async def cleanup_router():
    yield
    if welcome_router.parent_router:
         welcome_router._parent_router = None
    # Reset global data if needed
    global_data.welcome_messages = {}
    global_data.welcome_button = {}
    global_data.captcha = []
    global_data.auto_all = []
    global_data.entry_channel = {}

@pytest.mark.asyncio
async def test_set_welcome_command(mock_server, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(welcome_router)
    
    router_app_context.utils_service.is_admin.return_value = True
    router_app_context.utils_service.sleep_and_delete = AsyncMock()
    
    update = types.Update(
        update_id=1,
        message=types.Message(
            message_id=1,
            date=datetime.datetime.now(),
            chat=types.Chat(id=MTLChats.TestGroup, type='supergroup', title="Test Chat"),
            from_user=types.User(id=999, is_bot=False, first_name="Admin", username="admin"),
            text="/set_welcome Hello $$USER$$"
        )
    )
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    # Verify DB save
    assert router_app_context.config_service.save_bot_value.called
    args = router_app_context.config_service.save_bot_value.call_args[0]
    assert args[0] == MTLChats.TestGroup
    assert args[1] == BotValueTypes.WelcomeMessage
    assert args[2] == "Hello $$USER$$"
    
    # Verify reply
    requests = mock_server.get_requests()
    assert any("Added" in r["data"]["text"] for r in requests if r["method"] == "sendMessage")

@pytest.mark.asyncio
async def test_new_chat_member_welcome(mock_server, router_app_context):
    dp = router_app_context.dispatcher
    dp.chat_member.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(welcome_router)
    
    global_data.welcome_messages[MTLChats.TestGroup] = "Welcome $$USER$$!"
    
    # Mocks
    router_app_context.antispam_service.combo_check_spammer.return_value = False
    router_app_context.antispam_service.lols_check_spammer.return_value = False
    router_app_context.group_service.enforce_entry_channel.return_value = (True, None) # membership_ok=True
    router_app_context.config_service.check_user.return_value = 0 # New user
    
    user = types.User(id=123, is_bot=False, first_name="Joiner", username="joiner")
    event = types.ChatMemberUpdated(
        chat=types.Chat(id=MTLChats.TestGroup, type='supergroup', title="Test Chat"),
        from_user=user,
        date=datetime.datetime.now(),
        old_chat_member=types.ChatMemberLeft(user=user),
        new_chat_member=types.ChatMemberMember(user=user)
    )
    
    update = types.Update(update_id=2, chat_member=event)
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    # Verify add user
    assert router_app_context.config_service.add_user_to_chat.called
    
    # Verify welcome message
    requests = mock_server.get_requests()
    assert any("Welcome" in r["data"]["text"] for r in requests if r["method"] == "sendMessage")

@pytest.mark.asyncio
async def test_stop_exchange_command(mock_server, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(welcome_router)
    
    global_data.skynet_admins = ["@admin"]
    
    router_app_context.stellar_service.stop_all_exchange = MagicMock()
    
    update = types.Update(
        update_id=3,
        message=types.Message(
            message_id=3,
            date=datetime.datetime.now(),
            chat=types.Chat(id=MTLChats.TestGroup, type='supergroup', title="Test Chat"),
            from_user=types.User(id=999, is_bot=False, first_name="Admin", username="admin"),
            text="/stop_exchange"
        )
    )
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    assert router_app_context.stellar_service.stop_all_exchange.called
    requests = mock_server.get_requests()
    assert any("Was stop" in r["data"]["text"] for r in requests if r["method"] == "sendMessage")

@pytest.mark.asyncio
async def test_join_request(mock_server, router_app_context):
    dp = router_app_context.dispatcher
    dp.include_router(welcome_router)
    
    global_data.notify_join[MTLChats.TestGroup] = "123456"
    
    update = types.Update(
        update_id=4,
        chat_join_request=types.ChatJoinRequest(
            chat=types.Chat(id=MTLChats.TestGroup, type='supergroup', title="Test Chat"),
            from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
            user_chat_id=999,
            date=datetime.datetime.now()
        )
    )
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    requests = mock_server.get_requests()
    assert any("Новый участник" in r["data"]["text"] for r in requests if r["method"] == "sendMessage")

@pytest.mark.asyncio
async def test_cq_join(mock_server, router_app_context):
    dp = router_app_context.dispatcher
    dp.callback_query.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(welcome_router)
    
    router_app_context.utils_service.is_admin.return_value = True
    
    cb_data = JoinCallbackData(user_id=1, chat_id=MTLChats.TestGroup, can_join=True).pack()
    
    update = types.Update(
        update_id=5,
        callback_query=types.CallbackQuery(
            id="cb1",
            chat_instance="ci1",
            from_user=types.User(id=999, is_bot=False, first_name="Admin", username="admin"),
            message=types.Message(message_id=10, date=datetime.datetime.now(), chat=types.Chat(id=123, type='supergroup'), text="Join req"),
            data=cb_data
        )
    )
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    requests = mock_server.get_requests()
    assert any(r["method"] == "approveChatJoinRequest" for r in requests)
    assert any("✅" in r["data"]["text"] for r in requests if r["method"] == "answerCallbackQuery")

# --- E2E Unit Tests (Direct Handler Call) ---

@pytest.fixture
def mock_bot():
    bot = AsyncMock(spec=Bot)
    bot.ban_chat_member = AsyncMock()
    bot.send_message = AsyncMock()
    bot.restrict_chat_member = AsyncMock()
    bot.get_chat = AsyncMock()
    
    # Context patching removed as code now uses explicit bot instance
    return bot

@pytest.fixture
def mock_session():
    return MagicMock()

@pytest.fixture
def mock_app_context():
    app_context = MagicMock()
    app_context.antispam_service = AsyncMock()
    app_context.group_service = AsyncMock()
    app_context.config_service = MagicMock() # MagicMock for sync methods
    app_context.utils_service = AsyncMock()
    app_context.stellar_service = AsyncMock() 

    # Default behaviors
    app_context.antispam_service.combo_check_spammer.return_value = False
    app_context.antispam_service.lols_check_spammer.return_value = False
    app_context.group_service.enforce_entry_channel.return_value = (True, None)
    
    # config_service sync methods
    app_context.config_service.check_user.return_value = 0 # Not banned
    app_context.config_service.load_bot_value.return_value = '[]' # Default empty list for /all

    # config_service async methods
    app_context.config_service.add_user_to_chat = AsyncMock()
    app_context.config_service.save_bot_value = AsyncMock()

    return app_context

@pytest.fixture
def chat_member_event():
    user = User(id=123, is_bot=False, first_name="Test", last_name="User", username="testuser")
    chat = Chat(id=-1001, type="supergroup", title="Test Chat")
    return ChatMemberUpdated(
        chat=chat,
        from_user=user,
        date=1234567890,
        old_chat_member=ChatMemberOwner(user=user, is_anonymous=False), 
        new_chat_member=ChatMemberOwner(user=user, is_anonymous=False)  
    )

@pytest.mark.asyncio
async def test_cas_spam_ban(chat_member_event, mock_session, mock_bot, mock_app_context):
    mock_app_context.antispam_service.combo_check_spammer.return_value = True
    await new_chat_member(chat_member_event, mock_session, mock_bot, app_context=mock_app_context)
    mock_bot.ban_chat_member.assert_awaited_once_with(chat_member_event.chat.id, chat_member_event.new_chat_member.user.id)
    mock_bot.send_message.assert_awaited_once()
    assert "CAS ban" in mock_bot.send_message.call_args[0][1]

@pytest.mark.asyncio
async def test_lols_spam_ban(chat_member_event, mock_session, mock_bot, mock_app_context):
    mock_app_context.antispam_service.lols_check_spammer.return_value = True
    await new_chat_member(chat_member_event, mock_session, mock_bot, app_context=mock_app_context)
    mock_bot.ban_chat_member.assert_awaited_once_with(chat_member_event.chat.id, chat_member_event.new_chat_member.user.id)
    assert "LOLS base" in mock_bot.send_message.call_args[0][1]

@pytest.mark.asyncio
async def test_forbidden_name_ban(chat_member_event, mock_session, mock_bot, mock_app_context):
    bad_user = User(id=666, is_bot=False, first_name="ЧВК ВАГНЕР", last_name="", username="badguy")
    # Reconstruct the entire event because it is frozen
    new_event = ChatMemberUpdated(
        chat=chat_member_event.chat,
        from_user=chat_member_event.from_user,
        date=chat_member_event.date,
        old_chat_member=chat_member_event.old_chat_member,
        new_chat_member=ChatMemberOwner(user=bad_user, is_anonymous=False)
    )
    
    await new_chat_member(new_event, mock_session, mock_bot, app_context=mock_app_context)
    mock_bot.ban_chat_member.assert_awaited_once_with(new_event.chat.id, bad_user.id)
    assert "за использование запрещенного никнейма" in mock_bot.send_message.call_args[0][1]

@pytest.mark.asyncio
async def test_existing_banned_user(chat_member_event, mock_session, mock_bot, mock_app_context):
    mock_app_context.config_service.check_user.return_value = 2 # Banned
    await new_chat_member(chat_member_event, mock_session, mock_bot, app_context=mock_app_context)
    mock_bot.ban_chat_member.assert_awaited_once_with(chat_member_event.chat.id, chat_member_event.new_chat_member.user.id)
    assert "was banned" in mock_bot.send_message.call_args[0][1]

@pytest.mark.asyncio
async def test_entry_channel_enforcement_fail(chat_member_event, mock_session, mock_bot, mock_app_context):
    # Setup global_data to require entry channel
    global_data.entry_channel[chat_member_event.chat.id] = -100999
    
    # Mock enforcement failure (user not in channel)
    mock_app_context.group_service.enforce_entry_channel.return_value = (False, "Please join channel X first")
    
    await new_chat_member(chat_member_event, mock_session, mock_bot, app_context=mock_app_context)
    
    # Assert: Should expect enforce_entry_channel to be called
    mock_app_context.group_service.enforce_entry_channel.assert_awaited_once_with(
        mock_bot, chat_member_event.chat.id, chat_member_event.new_chat_member.user.id, -100999
    )
    # Assert: Should NOT obtain user info (indicating logic stopped early)
    mock_app_context.config_service.check_user.assert_not_called()
    
    # Cleanup global_data
    del global_data.entry_channel[chat_member_event.chat.id]

@pytest.mark.asyncio
async def test_welcome_message_simple(chat_member_event, mock_session, mock_bot, mock_app_context):
    # Setup welcome message
    welcome_text = "Hello $$USER$$!"
    global_data.welcome_messages[chat_member_event.chat.id] = welcome_text
    
    # Execute
    await new_chat_member(chat_member_event, mock_session, mock_bot, app_context=mock_app_context)
    
    # Assert
    mock_bot.send_message.assert_awaited_once()
    args, kwargs = mock_bot.send_message.call_args
    assert args[0] == chat_member_event.chat.id
    assert "$$USER$$" not in args[1]
    
    # Check sleep_and_delete called
    mock_app_context.utils_service.sleep_and_delete.assert_awaited_once()

    # Cleanup
    del global_data.welcome_messages[chat_member_event.chat.id]

@pytest.mark.asyncio
async def test_welcome_captcha(chat_member_event, mock_session, mock_bot, mock_app_context):
    # Setup welcome + captcha
    global_data.welcome_messages[chat_member_event.chat.id] = "Welcome"
    
    # Fix: captcha is a list of chat_ids
    if chat_member_event.chat.id not in global_data.captcha:
        global_data.captcha.append(chat_member_event.chat.id)
        
    global_data.welcome_button[chat_member_event.chat.id] = "Click me"
    
    # Execute
    await new_chat_member(chat_member_event, mock_session, mock_bot, app_context=mock_app_context)
    
    # Assert
    mock_bot.restrict_chat_member.assert_awaited_once()
    
    # Check button
    mock_bot.send_message.assert_awaited_once()
    _, kwargs = mock_bot.send_message.call_args
    assert kwargs.get('reply_markup') is not None

    # Cleanup
    del global_data.welcome_messages[chat_member_event.chat.id]
    if chat_member_event.chat.id in global_data.captcha:
        global_data.captcha.remove(chat_member_event.chat.id)
    del global_data.welcome_button[chat_member_event.chat.id]

@pytest.mark.asyncio
async def test_auto_all_manager_add(chat_member_event, mock_session, mock_bot, mock_app_context):
    # Fix: auto_all is a list
    if chat_member_event.chat.id not in global_data.auto_all:
        global_data.auto_all.append(chat_member_event.chat.id)
        
    mock_app_context.config_service.load_bot_value = AsyncMock(return_value='["@existing"]')
    
    await new_chat_member(chat_member_event, mock_session, mock_bot, app_context=mock_app_context)
    
    mock_app_context.config_service.save_bot_value.assert_awaited_once()
    args, _ = mock_app_context.config_service.save_bot_value.call_args
    saved_json = args[2] # 3rd arg is value
    members = json.loads(saved_json)
    assert "@testuser" in members
    assert "@existing" in members

    # Cleanup
    if chat_member_event.chat.id in global_data.auto_all:
        global_data.auto_all.remove(chat_member_event.chat.id)

@pytest.mark.asyncio
async def test_welcome_emoji_captcha(chat_member_event, mock_session, mock_bot, mock_app_context):
    # Setup welcome with color placeholder
    global_data.welcome_messages[chat_member_event.chat.id] = "Click the $$COLOR$$ button"
    if chat_member_event.chat.id not in global_data.captcha:
        global_data.captcha.append(chat_member_event.chat.id)
    
    # Execute
    await new_chat_member(chat_member_event, mock_session, mock_bot, app_context=mock_app_context)
    
    # Assert
    mock_bot.send_message.assert_awaited_once()
    args, kwargs = mock_bot.send_message.call_args
    text = args[1]
    
    # Should have replaced $$COLOR$$ with an emoji
    assert "$$COLOR$$" not in text
    
    # Should have a keyboard
    assert kwargs.get('reply_markup') is not None
    # We can inspect the keyboard to ensure it has 6 buttons (3x2 random) but simpler to just check presence
    
    # Cleanup
    del global_data.welcome_messages[chat_member_event.chat.id]
    if chat_member_event.chat.id in global_data.captcha:
        global_data.captcha.remove(chat_member_event.chat.id)

@pytest.mark.asyncio
async def test_auto_all_no_username(chat_member_event, mock_session, mock_bot, mock_app_context):
    if chat_member_event.chat.id not in global_data.auto_all:
        global_data.auto_all.append(chat_member_event.chat.id)
    
    # Remove username - Reconstruct event similar to forbidden name test
    no_username_user = User(id=777, is_bot=False, first_name="NoUser", last_name="Name", username=None)
    new_event = ChatMemberUpdated(
        chat=chat_member_event.chat,
        from_user=chat_member_event.from_user,
        date=chat_member_event.date,
        old_chat_member=chat_member_event.old_chat_member,
        new_chat_member=ChatMemberOwner(user=no_username_user, is_anonymous=False)
    )
    
    mock_app_context.config_service.load_bot_value = AsyncMock(return_value='["@existing"]')
    
    await new_chat_member(new_event, mock_session, mock_bot, app_context=mock_app_context)
    
    # Assert: Should warn about no username
    mock_bot.send_message.assert_awaited_once()
    assert "dont have username" in mock_bot.send_message.call_args[0][1]
    
    # Assert: Should NOT have added to list
    mock_app_context.config_service.save_bot_value.assert_awaited_once()
    args, _ = mock_app_context.config_service.save_bot_value.call_args
    saved_json = args[2]
    members = json.loads(saved_json)
    assert len(members) == 1
    assert "@existing" in members

    # Cleanup
    if chat_member_event.chat.id in global_data.auto_all:
        global_data.auto_all.remove(chat_member_event.chat.id)
