import pytest
from aiogram import types
from unittest.mock import AsyncMock

from routers import mic as mic_module


class FakeMessage:
    def __init__(
        self,
        *,
        chat_id: int,
        message_id: int,
        text: str,
        from_user: types.User | None = None,
        message_thread_id: int | None = None,
        reply_markup: types.InlineKeyboardMarkup | None = None,
    ):
        self.chat = types.Chat(id=chat_id, type="supergroup")
        self.message_id = message_id
        self.text = text
        self.from_user = from_user or types.User(id=1, is_bot=False, first_name="User", username="user")
        self.message_thread_id = message_thread_id
        self.reply_markup = reply_markup
        self.answer = AsyncMock(side_effect=self._answer)
        self._answers: list[dict] = []

    async def _answer(self, text: str, reply_markup=None):
        self._answers.append({"text": text, "reply_markup": reply_markup})
        return FakeMessage(
            chat_id=self.chat.id,
            message_id=self.message_id + 1,
            text=text,
            from_user=self.from_user,
            message_thread_id=self.message_thread_id,
            reply_markup=reply_markup,
        )


class FakeCallback:
    def __init__(self, *, from_user: types.User, message: FakeMessage, data: str):
        self.from_user = from_user
        self.message = message
        self.data = data
        self.answer = AsyncMock()


@pytest.fixture(autouse=True)
def _cleanup_sessions():
    mic_module._locks.clear()
    mic_module._sessions.clear()
    yield
    mic_module._locks.clear()
    mic_module._sessions.clear()


@pytest.mark.asyncio
async def test_mic_command_creates_session_message():
    msg = FakeMessage(chat_id=-100123, message_id=10, text="/mic ютуб выступление", message_thread_id=55)

    await mic_module.cmd_mic(msg)  # type: ignore[arg-type]

    assert msg.answer.called
    sent = msg._answers[0]
    assert "ютуб выступление" in sent["text"]
    assert "Статус: свободно" in sent["text"]
    assert sent["reply_markup"] is not None


@pytest.mark.asyncio
async def test_mic_take_and_release_and_busy_user():
    chat_id = -100123
    topic_id = 55
    message_id = 777

    free_cb = mic_module.MicCallbackData(action="take", owner_id=0).pack()
    free_markup = types.InlineKeyboardMarkup(
        inline_keyboard=[[types.InlineKeyboardButton(text="🟢 Взять", callback_data=free_cb)]]
    )
    msg = FakeMessage(
        chat_id=chat_id,
        message_id=message_id,
        message_thread_id=topic_id,
        text="🎙 Микрофон\nТема: Ютуб\nСтатус: свободно",
        reply_markup=free_markup,
    )

    bot = AsyncMock()

    owner = types.User(id=200, is_bot=False, first_name="Igor", username="igor")
    cb_take = FakeCallback(from_user=owner, message=msg, data=free_cb)
    await mic_module.cb_mic(cb_take, mic_module.MicCallbackData(action="take", owner_id=0), bot)  # type: ignore[arg-type]

    assert bot.edit_message_text.called
    take_text = bot.edit_message_text.call_args.kwargs["text"]
    assert "Статус: взято" in take_text
    assert "@igor" in take_text

    taken_cb = mic_module.MicCallbackData(action="release", owner_id=200).pack()
    taken_markup = types.InlineKeyboardMarkup(
        inline_keyboard=[[types.InlineKeyboardButton(text="🔴 Взято: @igor", callback_data=taken_cb)]]
    )
    msg_taken = FakeMessage(
        chat_id=chat_id,
        message_id=message_id,
        message_thread_id=topic_id,
        text="🎙 Микрофон\nТема: Ютуб\nСтатус: взято @igor",
        reply_markup=taken_markup,
    )

    other = types.User(id=201, is_bot=False, first_name="Other", username="other")
    cb_busy = FakeCallback(from_user=other, message=msg_taken, data=taken_cb)
    await mic_module.cb_mic(cb_busy, mic_module.MicCallbackData(action="release", owner_id=200), bot)  # type: ignore[arg-type]
    assert cb_busy.answer.called

    cb_release = FakeCallback(from_user=owner, message=msg_taken, data=taken_cb)
    await mic_module.cb_mic(cb_release, mic_module.MicCallbackData(action="release", owner_id=200), bot)  # type: ignore[arg-type]

    release_text = bot.edit_message_text.call_args.kwargs["text"]
    assert "Статус: свободно" in release_text

