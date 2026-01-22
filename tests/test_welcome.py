
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from aiogram import Bot, types, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.enums import ChatMemberStatus
import datetime

from routers.welcome import router as welcome_router, CaptchaCallbackData, EmojiCaptchaCallbackData, JoinCallbackData, emoji_pairs
from tests.conftest import TEST_BOT_TOKEN
from other.global_data import global_data, MTLChats

class MockDbMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        data["session"] = MagicMock()
        return await handler(event, data)

@pytest.fixture(autouse=True)
async def cleanup_router():
    yield
    if welcome_router.parent_router:
         welcome_router._parent_router = None

@pytest.mark.asyncio
async def test_set_welcome_command(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(welcome_router)
    dp.message.middleware(MockDbMiddleware())

    # Mock is_admin
    with patch("routers.welcome.is_admin", new_callable=AsyncMock, return_value=True), \
         patch("other.global_data.global_data.mongo_config.save_bot_value", new_callable=AsyncMock), \
         patch("routers.welcome.cmd_sleep_and_delete", new_callable=AsyncMock):
        
        # Test /set_welcome
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
        
        await dp.feed_update(bot=bot, update=update)
        
        # Verify changes in global_data
        assert global_data.welcome_messages.get(MTLChats.TestGroup) == "Hello $$USER$$"
        
        # Verify confirmation message
        msg_req = next((r for r in mock_server if r["method"] == "sendMessage" and "Added" in r["data"]["text"]), None)
        assert msg_req is not None

    await bot.session.close()

@pytest.mark.asyncio
async def test_new_chat_member_welcome(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(welcome_router)
    dp.chat_member.middleware(MockDbMiddleware())

    # Setup global data for welcome message
    global_data.welcome_messages[MTLChats.TestGroup] = "Welcome $$USER$$!"
    
    # Mock mocks
    with patch("routers.welcome.combo_check_spammer", return_value=False), \
         patch("routers.welcome.lols_check_spammer", return_value=False), \
         patch("routers.welcome.enforce_entry_channel", return_value=(True, None)), \
         patch("other.global_data.global_data.mongo_config.add_user_to_chat", new_callable=AsyncMock), \
         patch("routers.welcome.global_data.check_user", return_value=0): # 0 = New User

        # Simulate ChatMemberUpdated (Join)
        user = types.User(id=123, is_bot=False, first_name="Joiner", username="joiner")
        date = datetime.datetime.now()
        chat = types.Chat(id=MTLChats.TestGroup, type='supergroup', title="Test Chat")
        
        event = types.ChatMemberUpdated(
            chat=chat,
            from_user=user,
            date=date,
            old_chat_member=types.ChatMemberLeft(user=user),
            new_chat_member=types.ChatMemberMember(user=user)
        )
        
        update = types.Update(
            update_id=2,
            chat_member=event
        )
        
        # We need to manually register the update type if it's not default?
        # chat_member updates are allowed by default if we use polling or feed_update but we need to verify.
        
        await dp.feed_update(bot=bot, update=update)
        
        # Verify welcome message
        msg_req = next((r for r in mock_server if r["method"] == "sendMessage" and "Welcome" in r["data"]["text"]), None)
        assert msg_req is not None
        assert "joiner" in msg_req["data"]["text"] # $$USER$$ replaced

    await bot.session.close()

@pytest.mark.asyncio
async def test_delete_welcome_command(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(welcome_router)
    dp.message.middleware(MockDbMiddleware())

    global_data.welcome_messages[MTLChats.TestGroup] = "Hi"

    with patch("routers.welcome.is_admin", new_callable=AsyncMock, return_value=True), \
         patch("other.global_data.global_data.mongo_config.save_bot_value", new_callable=AsyncMock), \
         patch("routers.welcome.cmd_sleep_and_delete", new_callable=AsyncMock):
        update = types.Update(
            update_id=3,
            message=types.Message(
                message_id=3,
                date=datetime.datetime.now(),
                chat=types.Chat(id=MTLChats.TestGroup, type='supergroup', title="Test Chat"),
                from_user=types.User(id=999, is_bot=False, first_name="Admin", username="admin"),
                text="/delete_welcome"
            )
        )

        await dp.feed_update(bot=bot, update=update)

        assert global_data.welcome_messages.get(MTLChats.TestGroup) is None
        msg_req = next((r for r in mock_server if r["method"] == "sendMessage" and "Removed" in r["data"]["text"]), None)
        assert msg_req is not None

    await bot.session.close()

@pytest.mark.asyncio
async def test_set_welcome_button_command(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(welcome_router)
    dp.message.middleware(MockDbMiddleware())

    with patch("routers.welcome.is_admin", new_callable=AsyncMock, return_value=True), \
         patch("other.global_data.global_data.mongo_config.save_bot_value", new_callable=AsyncMock), \
         patch("routers.welcome.cmd_sleep_and_delete", new_callable=AsyncMock):
        update = types.Update(
            update_id=4,
            message=types.Message(
                message_id=4,
                date=datetime.datetime.now(),
                chat=types.Chat(id=MTLChats.TestGroup, type='supergroup', title="Test Chat"),
                from_user=types.User(id=999, is_bot=False, first_name="Admin", username="admin"),
                text="/set_welcome_button Press me"
            )
        )

        await dp.feed_update(bot=bot, update=update)

        assert global_data.welcome_button.get(MTLChats.TestGroup) == "Press me"
        msg_req = next((r for r in mock_server if r["method"] == "sendMessage" and "Added" in r["data"]["text"]), None)
        assert msg_req is not None

    await bot.session.close()

@pytest.mark.asyncio
async def test_stop_exchange_command_admin(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(welcome_router)
    dp.message.middleware(MockDbMiddleware())

    with patch("routers.welcome.is_skynet_admin", return_value=True), \
         patch("routers.welcome.stellar_stop_all_exchange"), \
         patch("other.global_data.global_data.mongo_config.save_bot_value", new_callable=AsyncMock):
        update = types.Update(
            update_id=5,
            message=types.Message(
                message_id=5,
                date=datetime.datetime.now(),
                chat=types.Chat(id=MTLChats.TestGroup, type='supergroup', title="Test Chat"),
                from_user=types.User(id=999, is_bot=False, first_name="Admin", username="admin"),
                text="/stop_exchange"
            )
        )

        await dp.feed_update(bot=bot, update=update)

        msg_req = next((r for r in mock_server if r["method"] == "sendMessage" and "Was stop" in r["data"]["text"]), None)
        assert msg_req is not None

    await bot.session.close()

@pytest.mark.asyncio
async def test_start_exchange_command_admin(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(welcome_router)
    dp.message.middleware(MockDbMiddleware())

    with patch("routers.welcome.is_skynet_admin", return_value=True), \
         patch("other.global_data.global_data.mongo_config.save_bot_value", new_callable=AsyncMock):
        update = types.Update(
            update_id=6,
            message=types.Message(
                message_id=6,
                date=datetime.datetime.now(),
                chat=types.Chat(id=MTLChats.TestGroup, type='supergroup', title="Test Chat"),
                from_user=types.User(id=999, is_bot=False, first_name="Admin", username="admin"),
                text="/start_exchange"
            )
        )

        await dp.feed_update(bot=bot, update=update)

        msg_req = next((r for r in mock_server if r["method"] == "sendMessage" and "Was start" in r["data"]["text"]), None)
        assert msg_req is not None

    await bot.session.close()

@pytest.mark.asyncio
async def test_left_chat_member_auto_all(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(welcome_router)
    dp.chat_member.middleware(MockDbMiddleware())

    global_data.auto_all = [MTLChats.TestGroup]
    global_data.mongo_config.remove_user_from_chat = AsyncMock()
    global_data.mongo_config.load_bot_value = AsyncMock(return_value='["@user"]')
    global_data.mongo_config.save_bot_value = AsyncMock()

    user = types.User(id=123, is_bot=False, first_name="Left", username="user")
    date = datetime.datetime.now()
    chat = types.Chat(id=MTLChats.TestGroup, type='supergroup', title="Test Chat")
    event = types.ChatMemberUpdated(
        chat=chat,
        from_user=user,
        date=date,
        old_chat_member=types.ChatMemberMember(user=user),
        new_chat_member=types.ChatMemberLeft(user=user)
    )
    update = types.Update(update_id=7, chat_member=event)

    await dp.feed_update(bot=bot, update=update)

    global_data.mongo_config.save_bot_value.assert_called()

    await bot.session.close()

@pytest.mark.asyncio
async def test_msg_delete_income(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(welcome_router)

    global_data.delete_income[MTLChats.TestGroup] = 1

    update = types.Update(
        update_id=8,
        message=types.Message(
            message_id=8,
            date=datetime.datetime.now(),
            chat=types.Chat(id=MTLChats.TestGroup, type='supergroup', title="Test Chat"),
            from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
            new_chat_members=[types.User(id=123, is_bot=False, first_name="Joiner", username="joiner")]
        )
    )

    await dp.feed_update(bot=bot, update=update)

    req_delete = next((r for r in mock_server if r["method"] == "deleteMessage"), None)
    assert req_delete is not None

    await bot.session.close()

@pytest.mark.asyncio
async def test_captcha_callback_correct_user(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(welcome_router)

    cb_data = CaptchaCallbackData(answer=999).pack()
    update = types.Update(
        update_id=9,
        callback_query=types.CallbackQuery(
            id="cb1",
            chat_instance="ci1",
            from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
            message=types.Message(
                message_id=9,
                date=datetime.datetime.now(),
                chat=types.Chat(id=MTLChats.TestGroup, type='supergroup', title="Test Chat"),
                text="Captcha"
            ),
            data=cb_data
        )
    )

    await dp.feed_update(bot=bot, update=update)

    req_restrict = next((r for r in mock_server if r["method"] == "restrictChatMember"), None)
    assert req_restrict is not None

    await bot.session.close()

@pytest.mark.asyncio
async def test_emoji_captcha_callback_correct(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(welcome_router)

    cb_data = EmojiCaptchaCallbackData(user_id=999, square=emoji_pairs[1][0], num=1009).pack()
    update = types.Update(
        update_id=10,
        callback_query=types.CallbackQuery(
            id="cb2",
            chat_instance="ci2",
            from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
            message=types.Message(
                message_id=10,
                date=datetime.datetime.now(),
                chat=types.Chat(id=MTLChats.TestGroup, type='supergroup', title="Test Chat"),
                text="Captcha"
            ),
            data=cb_data
        )
    )

    await dp.feed_update(bot=bot, update=update)

    req_restrict = next((r for r in mock_server if r["method"] == "restrictChatMember"), None)
    assert req_restrict is not None

    await bot.session.close()

@pytest.mark.asyncio
async def test_recaptcha_command_need_words(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(welcome_router)
    dp.message.middleware(MockDbMiddleware())

    with patch("routers.welcome.is_admin", new_callable=AsyncMock, return_value=True), \
         patch("routers.welcome.cmd_sleep_and_delete", new_callable=AsyncMock):
        update = types.Update(
            update_id=11,
            message=types.Message(
                message_id=11,
                date=datetime.datetime.now(),
                chat=types.Chat(id=MTLChats.TestGroup, type='supergroup', title="Test Chat"),
                from_user=types.User(id=999, is_bot=False, first_name="Admin", username="admin"),
                text="/recaptcha"
            )
        )

        await dp.feed_update(bot=bot, update=update)

        msg_req = next((r for r in mock_server if r["method"] == "sendMessage" and "need more words" in r["data"]["text"]), None)
        assert msg_req is not None

    await bot.session.close()

@pytest.mark.asyncio
async def test_recaptcha_callback(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(welcome_router)
    dp.callback_query.middleware(MockDbMiddleware())

    with patch("routers.welcome.new_chat_member", new_callable=AsyncMock) as mock_new_member:
        update = types.Update(
            update_id=12,
            callback_query=types.CallbackQuery(
                id="cb3",
                chat_instance="ci3",
                from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                message=types.Message(
                    message_id=12,
                    date=datetime.datetime.now(),
                    chat=types.Chat(id=MTLChats.TestGroup, type='supergroup', title="Test Chat"),
                    text="ReCaptcha"
                ),
                data="ReCaptcha"
            )
        )

        await dp.feed_update(bot=bot, update=update)

        assert mock_new_member.called

    await bot.session.close()

@pytest.mark.asyncio
async def test_update_admins(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(welcome_router)
    dp.chat_member.middleware(MockDbMiddleware())

    global_data.mongo_config.save_bot_value = AsyncMock()

    user = types.User(id=123, is_bot=False, first_name="Admin", username="admin")
    date = datetime.datetime.now()
    chat = types.Chat(id=MTLChats.TestGroup, type='supergroup', title="Test Chat")
    event = types.ChatMemberUpdated(
        chat=chat,
        from_user=user,
        date=date,
        old_chat_member=types.ChatMemberMember(user=user),
        new_chat_member=types.ChatMemberAdministrator(
            user=user,
            can_be_edited=True,
            is_anonymous=False,
            can_manage_chat=True,
            can_delete_messages=True,
            can_manage_video_chats=True,
            can_restrict_members=True,
            can_promote_members=True,
            can_change_info=True,
            can_invite_users=True,
            can_post_stories=True,
            can_edit_stories=True,
            can_delete_stories=True
        )
    )

    update = types.Update(update_id=13, chat_member=event)
    await dp.feed_update(bot=bot, update=update)

    global_data.mongo_config.save_bot_value.assert_called()
    await bot.session.close()

@pytest.mark.asyncio
async def test_handle_chat_join_request(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(welcome_router)

    global_data.notify_join[MTLChats.TestGroup] = "123456"

    update = types.Update(
        update_id=14,
        chat_join_request=types.ChatJoinRequest(
            chat=types.Chat(id=MTLChats.TestGroup, type='supergroup', title="Test Chat"),
            from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
            user_chat_id=999,
            date=datetime.datetime.now()
        )
    )

    await dp.feed_update(bot=bot, update=update)

    req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
    assert req is not None
    assert "Новый участник" in req["data"]["text"]

    await bot.session.close()

@pytest.mark.asyncio
async def test_join_callback_not_admin(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(welcome_router)

    cb_data = JoinCallbackData(user_id=1, chat_id=MTLChats.TestGroup, can_join=True).pack()
    with patch("routers.welcome.is_admin", new_callable=AsyncMock, return_value=False):
        update = types.Update(
            update_id=15,
            callback_query=types.CallbackQuery(
                id="cb4",
                chat_instance="ci4",
                from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                message=types.Message(
                    message_id=13,
                    date=datetime.datetime.now(),
                    chat=types.Chat(id=MTLChats.TestGroup, type='supergroup', title="Test Chat"),
                    text="Join"
                ),
                data=cb_data
            )
        )

        await dp.feed_update(bot=bot, update=update)

        req = next((r for r in mock_server if r["method"] == "answerCallbackQuery"), None)
        assert req is not None

    await bot.session.close()
