import datetime
from unittest.mock import AsyncMock

import pytest
from aiogram import types

from routers import mic as mic_module


def _make_message(
    *,
    chat_id: int,
    message_id: int,
    text: str,
    message_thread_id: int | None = None,
    reply_markup: types.InlineKeyboardMarkup | None = None,
    from_user: types.User | None = None,
) -> types.Message:
    return types.Message(
        message_id=message_id,
        date=datetime.datetime.now(),
        chat=types.Chat(id=chat_id, type="supergroup"),
        from_user=from_user or types.User(id=1, is_bot=False, first_name="User", username="user"),
        text=text,
        message_thread_id=message_thread_id,
        reply_markup=reply_markup,
    )


def _make_callback(
    *,
    from_user: types.User,
    message: types.Message,
    data: str,
) -> types.CallbackQuery:
    return types.CallbackQuery(
        id="cb-1",
        from_user=from_user,
        chat_instance="chat-instance",
        message=message,
        data=data,
    )


@pytest.fixture(autouse=True)
def _cleanup_sessions():
    mic_module._locks.clear()
    mic_module._sessions.clear()
    yield
    mic_module._locks.clear()
    mic_module._sessions.clear()


@pytest.mark.asyncio
async def test_mic_command_creates_session_message():
    chat_id = -100123
    topic_id = 55

    sent = _make_message(
        chat_id=chat_id,
        message_id=11,
        message_thread_id=topic_id,
        text="🎙 Микрофон\nТема: ютуб выступление\nСтатус: свободно",
    )

    bot = AsyncMock()
    bot.return_value = sent

    msg = _make_message(
        chat_id=chat_id,
        message_id=10,
        text="/mic ютуб выступление",
        message_thread_id=topic_id,
    ).as_(bot)

    await mic_module.cmd_mic(msg)

    assert bot.call_count == 1
    send_message_call = bot.call_args.args[0]
    assert "ютуб выступление" in send_message_call.text
    assert "Статус: свободно" in send_message_call.text
    assert send_message_call.reply_markup is not None

    expected_key = (chat_id, topic_id, sent.message_id)
    assert expected_key in mic_module._sessions


@pytest.mark.asyncio
async def test_mic_take_and_release_and_busy_user():
    chat_id = -100123
    topic_id = 55
    message_id = 777

    free_cb = mic_module.MicCallbackData(action="take", owner_id=0).pack()
    free_markup = types.InlineKeyboardMarkup(
        inline_keyboard=[[types.InlineKeyboardButton(text="🟢 Взять", callback_data=free_cb)]]
    )
    msg_free = _make_message(
        chat_id=chat_id,
        message_id=message_id,
        message_thread_id=topic_id,
        text="🎙 Микрофон\nТема: Ютуб\nСтатус: свободно",
        reply_markup=free_markup,
    )

    bot = AsyncMock()

    owner = types.User(id=200, is_bot=False, first_name="Igor", username="igor")
    cb_take = _make_callback(from_user=owner, message=msg_free, data=free_cb).as_(bot)
    await mic_module.cb_mic(cb_take, mic_module.MicCallbackData(action="take", owner_id=0), bot)

    assert bot.edit_message_text.called
    take_text = bot.edit_message_text.call_args.kwargs["text"]
    assert "Статус: взято" in take_text
    assert "@igor" in take_text

    taken_cb = mic_module.MicCallbackData(action="release", owner_id=200).pack()
    taken_markup = types.InlineKeyboardMarkup(
        inline_keyboard=[[types.InlineKeyboardButton(text="🔴 Взято: @igor", callback_data=taken_cb)]]
    )
    msg_taken = _make_message(
        chat_id=chat_id,
        message_id=message_id,
        message_thread_id=topic_id,
        text="🎙 Микрофон\nТема: Ютуб\nСтатус: взято @igor",
        reply_markup=taken_markup,
    )

    other = types.User(id=201, is_bot=False, first_name="Other", username="other")
    cb_busy = _make_callback(from_user=other, message=msg_taken, data=taken_cb).as_(bot)
    await mic_module.cb_mic(cb_busy, mic_module.MicCallbackData(action="release", owner_id=200), bot)

    busy_answer = next(
        (c for c in bot.call_args_list if c.args and type(c.args[0]).__name__ == "AnswerCallbackQuery"),
        None,
    )
    assert busy_answer is not None

    cb_release = _make_callback(from_user=owner, message=msg_taken, data=taken_cb).as_(bot)
    await mic_module.cb_mic(cb_release, mic_module.MicCallbackData(action="release", owner_id=200), bot)

    release_text = bot.edit_message_text.call_args.kwargs["text"]
    assert "Статус: свободно" in release_text
