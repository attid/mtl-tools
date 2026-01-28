import datetime
import json
import pytest
from aiogram import types

from routers.welcome import router as welcome_router, CaptchaCallbackData, JoinCallbackData
from tests.conftest import RouterTestMiddleware
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
async def test_set_welcome_command(mock_telegram, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(welcome_router)
    
    update = types.Update(
        update_id=1,
        message=types.Message(
            message_id=1,
            date=datetime.datetime.now(),
            chat=types.Chat(id=MTLChats.TestGroup, type='supergroup', title="Test Chat"),
            from_user=types.User(id=123456, is_bot=False, first_name="Admin", username="admin"),
            text="/set_welcome Hello $$USER$$"
        )
    )
    
    await dp.feed_update(bot=router_app_context.bot, update=update)

    # Verify config_service was updated (DI service interface)
    assert router_app_context.config_service.get_welcome_message(MTLChats.TestGroup) == "Hello $$USER$$"

    # Verify reply
    requests = mock_telegram.get_requests()
    assert any("Added" in r["data"]["text"] for r in requests if r["method"] == "sendMessage")

@pytest.mark.asyncio
async def test_new_chat_member_welcome(mock_telegram, router_app_context):
    dp = router_app_context.dispatcher
    dp.chat_member.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(welcome_router)

    # Set welcome message in both global_data (for fallback) and config_service (for DI)
    global_data.welcome_messages[MTLChats.TestGroup] = "Welcome $$USER$$!"
    router_app_context.config_service.set_welcome_message(MTLChats.TestGroup, "Welcome $$USER$$!")

    # Mocks
    user = types.User(id=123, is_bot=False, first_name="Joiner", username="joiner")
    router_app_context.antispam_service.combo_check_spammer.return_value = False
    router_app_context.antispam_service.lols_check_spammer.return_value = False
    router_app_context.group_service.enforce_entry_channel.return_value = (True, None)
    router_app_context.config_service.set_user_status(user.id, 0)

    event = types.ChatMemberUpdated(
        chat=types.Chat(id=MTLChats.TestGroup, type='supergroup', title="Test Chat"),
        from_user=user,
        date=datetime.datetime.now(),
        old_chat_member=types.ChatMemberLeft(user=user),
        new_chat_member=types.ChatMemberMember(user=user)
    )

    update = types.Update(update_id=2, chat_member=event)

    await dp.feed_update(bot=router_app_context.bot, update=update)

    # Note: ChatsRepository(session).add_user_to_chat is now called directly, not config_service
    # Verify welcome message was sent
    requests = mock_telegram.get_requests()
    assert any("Welcome" in r["data"]["text"] for r in requests if r["method"] == "sendMessage")

@pytest.mark.asyncio
async def test_stop_exchange_command(mock_telegram, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(welcome_router)

    router_app_context.admin_service.set_skynet_admins(["@admin"])

    router_app_context.stellar_service.stop_all_exchange.return_value = None

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
    requests = mock_telegram.get_requests()
    assert any("Was stop" in r["data"]["text"] for r in requests if r["method"] == "sendMessage")

@pytest.mark.asyncio
async def test_join_request(mock_telegram, router_app_context):
    dp = router_app_context.dispatcher
    dp.chat_join_request.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(welcome_router)

    # Configure notification_service (DI) instead of global_data.notify_join
    router_app_context.notification_service.set_join_notify(MTLChats.TestGroup, "123456")

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

    requests = mock_telegram.get_requests()
    assert any("Новый участник" in r["data"]["text"] for r in requests if r["method"] == "sendMessage")

@pytest.mark.asyncio
async def test_cq_join(mock_telegram, router_app_context):
    dp = router_app_context.dispatcher
    dp.callback_query.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(welcome_router)
    
    cb_data = JoinCallbackData(user_id=1, chat_id=MTLChats.TestGroup, can_join=True).pack()
    
    update = types.Update(
        update_id=5,
        callback_query=types.CallbackQuery(
            id="cb1",
            chat_instance="ci1",
            from_user=types.User(id=123456, is_bot=False, first_name="Admin", username="admin"),
            message=types.Message(message_id=10, date=datetime.datetime.now(), chat=types.Chat(id=123, type='supergroup'), text="Join req"),
            data=cb_data
        )
    )
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    requests = mock_telegram.get_requests()
    assert any(r["method"] == "approveChatJoinRequest" for r in requests)
    assert any("✅" in r["data"]["text"] for r in requests if r["method"] == "answerCallbackQuery")

# --- Additional Router Integration Tests (No Fake Bot/Message) ---

def build_chat_member_update(user, chat_id=-1001, update_id=200):
    event = types.ChatMemberUpdated(
        chat=types.Chat(id=chat_id, type="supergroup", title="Test Chat"),
        from_user=user,
        date=datetime.datetime.now(),
        old_chat_member=types.ChatMemberLeft(user=user),
        new_chat_member=types.ChatMemberMember(user=user),
    )
    return types.Update(update_id=update_id, chat_member=event)


@pytest.mark.asyncio
async def test_cas_spam_ban(mock_telegram, router_app_context):
    dp = router_app_context.dispatcher
    dp.chat_member.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(welcome_router)

    router_app_context.antispam_service.combo_check_spammer.return_value = True
    user = types.User(id=123, is_bot=False, first_name="Test", username="testuser")
    update = build_chat_member_update(user, chat_id=-1001, update_id=201)

    await dp.feed_update(bot=router_app_context.bot, update=update)

    requests = mock_telegram.get_requests()
    assert any(r["method"] == "banChatMember" for r in requests)
    assert any("CAS ban" in r["data"]["text"] for r in requests if r["method"] == "sendMessage")


@pytest.mark.asyncio
async def test_lols_spam_ban(mock_telegram, router_app_context):
    dp = router_app_context.dispatcher
    dp.chat_member.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(welcome_router)

    router_app_context.antispam_service.lols_check_spammer.return_value = True
    user = types.User(id=123, is_bot=False, first_name="Test", username="testuser")
    update = build_chat_member_update(user, chat_id=-1002, update_id=202)

    await dp.feed_update(bot=router_app_context.bot, update=update)

    requests = mock_telegram.get_requests()
    assert any(r["method"] == "banChatMember" for r in requests)
    assert any("LOLS base" in r["data"]["text"] for r in requests if r["method"] == "sendMessage")


@pytest.mark.asyncio
async def test_forbidden_name_ban(mock_telegram, router_app_context):
    dp = router_app_context.dispatcher
    dp.chat_member.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(welcome_router)

    bad_user = types.User(id=666, is_bot=False, first_name="ЧВК ВАГНЕР", username="badguy")
    update = build_chat_member_update(bad_user, chat_id=-1003, update_id=203)

    await dp.feed_update(bot=router_app_context.bot, update=update)

    requests = mock_telegram.get_requests()
    assert any(r["method"] == "banChatMember" for r in requests)
    assert any("запрещенного никнейма" in r["data"]["text"] for r in requests if r["method"] == "sendMessage")


@pytest.mark.asyncio
async def test_existing_banned_user(mock_telegram, router_app_context):
    dp = router_app_context.dispatcher
    dp.chat_member.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(welcome_router)

    user = types.User(id=777, is_bot=False, first_name="Test", username="testuser")
    # Set user as banned (user_type=2) in the shared session
    router_app_context.session.set_user(user.id, user_type=2, user_name="testuser")
    update = build_chat_member_update(user, chat_id=-1004, update_id=204)

    await dp.feed_update(bot=router_app_context.bot, update=update)

    requests = mock_telegram.get_requests()
    assert any(r["method"] == "banChatMember" for r in requests)
    # Message goes to SpamGroup, not the chat
    assert any("was banned" in r["data"]["text"] for r in requests if r["method"] == "sendMessage")


@pytest.mark.asyncio
async def test_entry_channel_enforcement_fail(mock_telegram, router_app_context):
    dp = router_app_context.dispatcher
    dp.chat_member.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(welcome_router)

    chat_id = -1005
    user = types.User(id=888, is_bot=False, first_name="Test", username="testuser")
    global_data.entry_channel[chat_id] = -100999
    router_app_context.group_service.enforce_entry_channel.return_value = (False, "Join channel")
    update = build_chat_member_update(user, chat_id=chat_id, update_id=205)

    await dp.feed_update(bot=router_app_context.bot, update=update)

    assert not router_app_context.config_service.add_user_to_chat.called
    requests = mock_telegram.get_requests()
    assert not any(r["method"] == "sendMessage" for r in requests)

    del global_data.entry_channel[chat_id]


@pytest.mark.asyncio
async def test_welcome_message_simple(mock_telegram, router_app_context):
    dp = router_app_context.dispatcher
    dp.chat_member.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(welcome_router)

    chat_id = -1006
    user = types.User(id=123, is_bot=False, first_name="Test", username="testuser")
    # Set welcome message in both global_data (for fallback) and config_service (for DI)
    global_data.welcome_messages[chat_id] = "Hello $$USER$$!"
    router_app_context.config_service.set_welcome_message(chat_id, "Hello $$USER$$!")

    update = build_chat_member_update(user, chat_id=chat_id, update_id=206)
    await dp.feed_update(bot=router_app_context.bot, update=update)

    requests = mock_telegram.get_requests()
    msg_req = next((r for r in requests if r["method"] == "sendMessage" and str(r["data"]["chat_id"]) == str(chat_id)), None)
    assert msg_req is not None
    assert "$$USER$$" not in msg_req["data"]["text"]
    assert len(router_app_context.utils_service.sleep_and_delete_calls) == 1

    del global_data.welcome_messages[chat_id]


@pytest.mark.asyncio
async def test_welcome_captcha(mock_telegram, router_app_context):
    dp = router_app_context.dispatcher
    dp.chat_member.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(welcome_router)

    chat_id = -1007
    user = types.User(id=123, is_bot=False, first_name="Test", username="testuser")
    # Set welcome message and captcha in both global_data (for fallback) and DI services
    global_data.welcome_messages[chat_id] = "Welcome"
    router_app_context.config_service.set_welcome_message(chat_id, "Welcome")
    if chat_id not in global_data.captcha:
        global_data.captcha.append(chat_id)
    router_app_context.feature_flags.enable(chat_id, "captcha")
    global_data.welcome_button[chat_id] = "Click me"
    router_app_context.config_service.set_welcome_button(chat_id, "Click me")

    update = build_chat_member_update(user, chat_id=chat_id, update_id=207)
    await dp.feed_update(bot=router_app_context.bot, update=update)

    requests = mock_telegram.get_requests()
    assert any(r["method"] == "restrictChatMember" for r in requests)
    msg_req = next((r for r in requests if r["method"] == "sendMessage" and str(r["data"]["chat_id"]) == str(chat_id)), None)
    assert msg_req is not None
    assert msg_req["data"].get("reply_markup") is not None

    del global_data.welcome_messages[chat_id]
    if chat_id in global_data.captcha:
        global_data.captcha.remove(chat_id)
    del global_data.welcome_button[chat_id]


@pytest.mark.asyncio
async def test_auto_all_manager_add(mock_telegram, router_app_context):
    dp = router_app_context.dispatcher
    dp.chat_member.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(welcome_router)

    chat_id = -1008
    user = types.User(id=123, is_bot=False, first_name="Test", username="testuser")
    if chat_id not in global_data.auto_all:
        global_data.auto_all.append(chat_id)
    router_app_context.feature_flags.enable(chat_id, "auto_all")
    # Set up existing members in the shared session
    router_app_context.session.set_bot_config(chat_id, BotValueTypes.All, '["@existing"]')

    update = build_chat_member_update(user, chat_id=chat_id, update_id=208)
    await dp.feed_update(bot=router_app_context.bot, update=update)

    # Verify the session now has the updated members list
    saved_value = router_app_context.session.get_bot_config(chat_id, BotValueTypes.All)
    members = json.loads(saved_value) if saved_value else []
    assert "@testuser" in members
    assert "@existing" in members

    global_data.auto_all.remove(chat_id)


@pytest.mark.asyncio
async def test_welcome_emoji_captcha(mock_telegram, router_app_context):
    dp = router_app_context.dispatcher
    dp.chat_member.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(welcome_router)

    chat_id = -1009
    user = types.User(id=123, is_bot=False, first_name="Test", username="testuser")
    # Set welcome message and captcha in both global_data (for fallback) and DI services
    global_data.welcome_messages[chat_id] = "Click the $$COLOR$$ button"
    router_app_context.config_service.set_welcome_message(chat_id, "Click the $$COLOR$$ button")
    if chat_id not in global_data.captcha:
        global_data.captcha.append(chat_id)
    router_app_context.feature_flags.enable(chat_id, "captcha")

    update = build_chat_member_update(user, chat_id=chat_id, update_id=209)
    await dp.feed_update(bot=router_app_context.bot, update=update)

    requests = mock_telegram.get_requests()
    msg_req = next((r for r in requests if r["method"] == "sendMessage" and str(r["data"]["chat_id"]) == str(chat_id)), None)
    assert msg_req is not None
    assert "$$COLOR$$" not in msg_req["data"]["text"]
    assert msg_req["data"].get("reply_markup") is not None

    del global_data.welcome_messages[chat_id]
    if chat_id in global_data.captcha:
        global_data.captcha.remove(chat_id)


@pytest.mark.asyncio
async def test_auto_all_no_username(mock_telegram, router_app_context):
    dp = router_app_context.dispatcher
    dp.chat_member.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(welcome_router)

    chat_id = -1010
    user = types.User(id=777, is_bot=False, first_name="NoUser", username=None)
    # Enable auto_all in both global_data (for fallback) and feature_flags (for DI)
    if chat_id not in global_data.auto_all:
        global_data.auto_all.append(chat_id)
    router_app_context.feature_flags.enable(chat_id, "auto_all")

    update = build_chat_member_update(user, chat_id=chat_id, update_id=210)
    await dp.feed_update(bot=router_app_context.bot, update=update)

    # Verify the "dont have username" message was sent
    requests = mock_telegram.get_requests()
    assert any("dont have username" in r["data"]["text"] for r in requests if r["method"] == "sendMessage")

    global_data.auto_all.remove(chat_id)

@pytest.mark.asyncio
async def test_cq_captcha_restores_permissions(mock_telegram, router_app_context):
    dp = router_app_context.dispatcher
    dp.callback_query.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(welcome_router)

    chat_id = -1011
    user_id = 123
    
    # Callback data must match user_id
    cb_data = CaptchaCallbackData(answer=user_id).pack()
    
    update = types.Update(
        update_id=211,
        callback_query=types.CallbackQuery(
            id="cb_captcha",
            chat_instance="ci_captcha",
            from_user=types.User(id=user_id, is_bot=False, first_name="User", username="user"),
            message=types.Message(
                message_id=11, 
                date=datetime.datetime.now(), 
                chat=types.Chat(id=chat_id, type='supergroup', title="Test Chat"), 
                text="Welcome"
            ),
            data=cb_data
        )
    )
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    requests = mock_telegram.get_requests()
    
    # Verify restrictChatMember was called
    restrict_req = next((r for r in requests if r["method"] == "restrictChatMember"), None)
    assert restrict_req is not None
    assert int(restrict_req["data"]["user_id"]) == user_id
    assert int(restrict_req["data"]["chat_id"]) == chat_id
    
    # Verify until_date is present
    # Aiogram converts timedelta to timestamp (int)
    until_date = restrict_req["data"].get("until_date")
    assert until_date is not None
    assert int(until_date) > datetime.datetime.now().timestamp()