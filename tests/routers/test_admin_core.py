import pytest
from aiogram import types
from routers.admin_core import router as admin_router, message_reaction as message_reaction_handler
from tests.conftest import RouterTestMiddleware
from other.constants import MTLChats
from other.pyro_tools import GroupMember
import datetime

@pytest.fixture(autouse=True)
async def cleanup_router():
    """Ensure router is detached after each test."""
    yield
    if admin_router.parent_router:
         admin_router._parent_router = None

def setup_is_admin(mock_server, user_id, is_admin=True):
    if is_admin:
        result_obj = {
            "status": "creator",
            "user": {"id": user_id, "is_bot": False, "username": "testuser", "first_name": "Test"},
            "is_anonymous": False
        }
        result = [result_obj]
    else:
        result = []

    mock_server.add_response("getChatAdministrators", {
        "ok": True,
        "result": result
    })

@pytest.mark.asyncio
async def test_ro_command(mock_telegram, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(admin_router)

    # Configure is_admin
    setup_is_admin(mock_telegram, 999, True)

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

    await dp.feed_update(bot=router_app_context.bot, update=update)

    # Verify restrict called
    requests = mock_telegram.get_requests()
    req = next((r for r in requests if r["method"] == "restrictChatMember"), None)
    assert req is not None
    assert int(req["data"]["user_id"]) == 789

@pytest.mark.asyncio
async def test_topic_command(mock_telegram, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(admin_router)

    setup_is_admin(mock_telegram, 999, True)

    # Mock createForumTopic response
    mock_telegram.add_response("createForumTopic", {
        "ok": True,
        "result": {
            "message_thread_id": 123,
            "name": "NewTopic",
            "icon_color": 7322096,
            "icon_custom_emoji_id": "🔵"
        }
    })

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

    await dp.feed_update(bot=router_app_context.bot, update=update)

    # Verify createForumTopic called
    requests = mock_telegram.get_requests()
    req = next((r for r in requests if r["method"] == "createForumTopic"), None)
    assert req is not None
    assert req["data"]["name"] == "NewTopic"
    assert req["data"]["icon_custom_emoji_id"] == "🔵"

@pytest.mark.asyncio
async def test_mute_command(mock_telegram, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(admin_router)

    chat_id = 123
    thread_id = 5
    chat_thread_key = f"{chat_id}-{thread_id}"

    # Set up topic admins using the admin_service (DI pattern)
    router_app_context.admin_service.set_topic_admins(chat_id, thread_id, ["@admin"])
    router_app_context.feature_flags.enable(chat_id, 'moderate')

    # Fake mongo config is provided in conftest

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

    await dp.feed_update(bot=router_app_context.bot, update=update)

    # Verify mute logic: Check admin_service.topic_mute updated (DI pattern)
    mutes = router_app_context.admin_service.get_topic_mutes_by_key(chat_thread_key)
    assert 789 in mutes

@pytest.mark.asyncio
async def test_all_command(mock_telegram, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(admin_router)

    # Mock Group Service
    router_app_context.group_service.get_members.return_value = [
        GroupMember(user_id=1, username="user1", full_name="User One", is_admin=False),
        GroupMember(user_id=2, username=None, full_name="User Two", is_admin=False)
    ]

    update = types.Update(
        update_id=5,
        message=types.Message(
            message_id=30,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='supergroup', title="Group"),
            from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
            text="/all"
        )
    )

    await dp.feed_update(bot=router_app_context.bot, update=update)

    requests = mock_telegram.get_requests()
    req = next((r for r in requests if r["method"] == "sendMessage"), None)
    assert req is not None
    assert "@user1" in req["data"]["text"]

@pytest.mark.asyncio
async def test_check_entry_channel_not_admin(mock_telegram, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(admin_router)

    setup_is_admin(mock_telegram, 999, False)

    update = types.Update(
        update_id=6,
        message=types.Message(
            message_id=31,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='supergroup', title="Group"),
            from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
            text="/check_entry_channel"
        )
    )

    await dp.feed_update(bot=router_app_context.bot, update=update)

    requests = mock_telegram.get_requests()
    req = next((r for r in requests if r["method"] == "sendMessage"), None)
    assert req is not None
    assert "You are not admin" in req["data"]["text"]

@pytest.mark.asyncio
async def test_delete_dead_members_invalid_format(mock_telegram, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(admin_router)

    setup_is_admin(mock_telegram, 999, True)

    update = types.Update(
        update_id=7,
        message=types.Message(
            message_id=32,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='supergroup', title="Group"),
            from_user=types.User(id=999, is_bot=False, first_name="Admin", username="admin"),
            text="/delete_dead_members"
        )
    )

    await dp.feed_update(bot=router_app_context.bot, update=update)

    requests = mock_telegram.get_requests()
    req = next((r for r in requests if r["method"] == "sendMessage"), None)
    assert req is not None
    assert "Please provide a chat ID" in req["data"]["text"]

@pytest.mark.asyncio
async def test_show_mutes_no_admins(mock_telegram, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(admin_router)

    # Enable moderation via feature flags
    router_app_context.feature_flags.enable(123, 'moderate')

    update = types.Update(
        update_id=8,
        message=types.Message(
            message_id=33,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='supergroup', is_forum=True),
            message_thread_id=1,
            from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
            text="/show_mute"
        )
    )

    await dp.feed_update(bot=router_app_context.bot, update=update)

    requests = mock_telegram.get_requests()
    req = next((r for r in requests if r["method"] == "sendMessage"), None)
    assert req is not None
    assert "Local admins not set yet" in req["data"]["text"]

@pytest.mark.asyncio
async def test_message_reaction_no_action(router_app_context):
    # This handler uses bot directly, but we can call it manually or via dispatch if we want.
    # The original test called it manually.

    bot = router_app_context.bot
    session = router_app_context.session
    # router_app_context IS the app_context (a TestAppContext instance)
    app_context = router_app_context

    class ReactionEvent:
        def __init__(self):
            self.new_reaction = [types.ReactionTypeCustomEmoji(custom_emoji_id="5220151067429335888")]
            self.chat = types.Chat(id=123, type='supergroup', title="Group")
            self.message_thread_id = None
            self.reply_to_message = None
            self._replies = []

        async def reply(self, text):
            self._replies.append(text)

    reaction_update = ReactionEvent()

    await message_reaction_handler(reaction_update, bot, session, app_context)
    # Assert nothing bad happened

@pytest.mark.asyncio
async def test_on_my_chat_member_added(mock_telegram, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(admin_router)

    chat = types.Chat(id=123, type='supergroup', title="Group")
    user = types.User(id=999, is_bot=False, first_name="User", username="user")
    update_event = types.ChatMemberUpdated(
        chat=chat,
        from_user=user,
        date=datetime.datetime.now(),
        old_chat_member=types.ChatMemberLeft(user=user),
        new_chat_member=types.ChatMemberMember(user=user)
    )
    update = types.Update(update_id=10, my_chat_member=update_event)

    await dp.feed_update(bot=router_app_context.bot, update=update)

    requests = mock_telegram.get_requests()
    req = next((r for r in requests if r["method"] == "sendMessage"), None)
    assert req is not None
    assert "Thanks for adding me" in req["data"]["text"]

@pytest.mark.asyncio
async def test_on_migrate(mock_telegram, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(admin_router)

    update = types.Update(
        update_id=11,
        message=types.Message(
            message_id=35,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='group', title="Group"),
            migrate_to_chat_id=-100123,
            from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
            text="migrate"
        )
    )

    await dp.feed_update(bot=router_app_context.bot, update=update)

    requests = mock_telegram.get_requests()
    req = next((r for r in requests if r["method"] == "sendMessage"), None)
    assert req is not None
    assert "migrated" in req["data"]["text"]

@pytest.mark.asyncio
async def test_send_me_not_admin(mock_telegram, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(admin_router)

    setup_is_admin(mock_telegram, 999, False)

    update = types.Update(
        update_id=12,
        message=types.Message(
            message_id=36,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='supergroup', title="Group"),
            from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
            text="/send_me"
        )
    )

    await dp.feed_update(bot=router_app_context.bot, update=update)

    requests = mock_telegram.get_requests()
    req = next((r for r in requests if r["method"] == "sendMessage"), None)
    assert req is not None
    assert "You are not admin" in req["data"]["text"]

@pytest.mark.asyncio
async def test_alert_me_add(mock_telegram, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(admin_router)

    # Fake mongo config is provided in conftest

    update = types.Update(
        update_id=13,
        message=types.Message(
            message_id=37,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='supergroup', title="Group"),
            from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
            text="/alert_me"
        )
    )

    await dp.feed_update(bot=router_app_context.bot, update=update)

    requests = mock_telegram.get_requests()
    req = next((r for r in requests if r["method"] == "sendMessage" and "Added" in r["data"]["text"]), None)
    assert req is not None

    # Verify sleep_and_delete called
    assert len(router_app_context.utils_service.sleep_and_delete_calls) == 2

@pytest.mark.asyncio
async def test_calc_requires_reply(mock_telegram, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(admin_router)

    update = types.Update(
        update_id=14,
        message=types.Message(
            message_id=38,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='supergroup', title="Group"),
            from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
            text="/calc"
        )
    )

    await dp.feed_update(bot=router_app_context.bot, update=update)

    requests = mock_telegram.get_requests()
    req = next((r for r in requests if r["method"] == "sendMessage"), None)
    assert req is not None
    assert "must be used in reply" in req["data"]["text"]

@pytest.mark.asyncio
async def test_web_pin_in_group(mock_telegram, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(admin_router)

    update = types.Update(
        update_id=15,
        message=types.Message(
            message_id=39,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='supergroup', title="Group"),
            from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
            text="/web_pin hello"
        )
    )

    await dp.feed_update(bot=router_app_context.bot, update=update)

    requests = mock_telegram.get_requests()
    req = next((r for r in requests if r["method"] == "editMessageReplyMarkup"), None)
    assert req is not None

@pytest.mark.asyncio
async def test_show_all_topic_admin_not_admin(mock_telegram, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(admin_router)

    setup_is_admin(mock_telegram, 999, False)

    update = types.Update(
        update_id=16,
        message=types.Message(
            message_id=40,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='supergroup', title="Group"),
            from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
            text="/show_all_topic_admin"
        )
    )

    await dp.feed_update(bot=router_app_context.bot, update=update)

    requests = mock_telegram.get_requests()
    req = next((r for r in requests if r["method"] == "sendMessage"), None)
    assert req is not None
    assert "You are not an admin" in req["data"]["text"]

@pytest.mark.asyncio
async def test_get_users_csv_usage(mock_telegram, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(admin_router)

    update = types.Update(
        update_id=17,
        message=types.Message(
            message_id=41,
            date=datetime.datetime.now(),
            chat=types.Chat(id=MTLChats.MTLIDGroup, type='supergroup', title="Group"),
            from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
            text="/get_users_csv"
        )
    )

    await dp.feed_update(bot=router_app_context.bot, update=update)

    requests = mock_telegram.get_requests()
    req = next((r for r in requests if r["method"] == "sendMessage"), None)
    assert req is not None
    assert "Usage" in req["data"]["text"]
