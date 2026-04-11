import datetime

import pytest
from aiogram import types

from routers import mic as mic_module


CHAT_ID = -100123
TOPIC_ID = 55


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
async def test_mic_command_creates_session_message(mock_telegram, router_bot):
    sent_message_id = 4242
    # Pin sendMessage response so we know the exact key the handler will store.
    mock_telegram.add_response(
        "sendMessage",
        {
            "ok": True,
            "result": {
                "message_id": sent_message_id,
                "date": 1234567890,
                "chat": {"id": CHAT_ID, "type": "supergroup"},
                "message_thread_id": TOPIC_ID,
                "text": "🎙 Микрофон\nТема: ютуб выступление\nСтатус: свободно",
            },
        },
    )

    msg = _make_message(
        chat_id=CHAT_ID,
        message_id=10,
        text="/mic ютуб выступление",
        message_thread_id=TOPIC_ID,
    ).as_(router_bot)

    await mic_module.cmd_mic(msg)

    requests = mock_telegram.get_requests()
    send_calls = [r for r in requests if r["method"] == "sendMessage"]
    assert len(send_calls) == 1
    sent_text = send_calls[0]["data"]["text"]
    assert "ютуб выступление" in sent_text
    assert "Статус: свободно" in sent_text
    assert send_calls[0]["data"].get("reply_markup") is not None

    expected_key = (CHAT_ID, TOPIC_ID, sent_message_id)
    assert expected_key in mic_module._sessions


@pytest.mark.asyncio
async def test_mic_take_and_release_and_busy_user(mock_telegram, router_bot):
    message_id = 777

    free_cb = mic_module.MicCallbackData(action="take", owner_id=0).pack()
    free_markup = types.InlineKeyboardMarkup(
        inline_keyboard=[[types.InlineKeyboardButton(text="🟢 Взять", callback_data=free_cb)]]
    )
    msg_free = _make_message(
        chat_id=CHAT_ID,
        message_id=message_id,
        message_thread_id=TOPIC_ID,
        text="🎙 Микрофон\nТема: Ютуб\nСтатус: свободно",
        reply_markup=free_markup,
    )

    owner = types.User(id=200, is_bot=False, first_name="Igor", username="igor")
    cb_take = _make_callback(from_user=owner, message=msg_free, data=free_cb).as_(bot=router_bot)
    await mic_module.cb_mic(
        cb_take,
        mic_module.MicCallbackData(action="take", owner_id=0),
        router_bot,
    )

    requests = mock_telegram.get_requests()
    edit_calls = [r for r in requests if r["method"] == "editMessageText"]
    assert len(edit_calls) == 1
    take_text = edit_calls[0]["data"]["text"]
    assert "Статус: взято" in take_text
    assert "@igor" in take_text

    taken_cb = mic_module.MicCallbackData(action="release", owner_id=200).pack()
    taken_markup = types.InlineKeyboardMarkup(
        inline_keyboard=[[types.InlineKeyboardButton(text="🔴 Взято: @igor", callback_data=taken_cb)]]
    )
    msg_taken = _make_message(
        chat_id=CHAT_ID,
        message_id=message_id,
        message_thread_id=TOPIC_ID,
        text="🎙 Микрофон\nТема: Ютуб\nСтатус: взято @igor",
        reply_markup=taken_markup,
    )

    # Non-owner tries to release: should get a "busy" answerCallbackQuery,
    # and no additional editMessageText should be issued.
    other = types.User(id=201, is_bot=False, first_name="Other", username="other")
    cb_busy = _make_callback(from_user=other, message=msg_taken, data=taken_cb).as_(bot=router_bot)
    await mic_module.cb_mic(
        cb_busy,
        mic_module.MicCallbackData(action="release", owner_id=200),
        router_bot,
    )

    requests = mock_telegram.get_requests()
    answer_calls = [r for r in requests if r["method"] == "answerCallbackQuery"]
    assert any("Занято" in (r["data"].get("text") or "") for r in answer_calls)
    # Still only the single edit from the take step.
    edit_calls = [r for r in requests if r["method"] == "editMessageText"]
    assert len(edit_calls) == 1

    # Owner releases.
    cb_release = _make_callback(from_user=owner, message=msg_taken, data=taken_cb).as_(bot=router_bot)
    await mic_module.cb_mic(
        cb_release,
        mic_module.MicCallbackData(action="release", owner_id=200),
        router_bot,
    )

    requests = mock_telegram.get_requests()
    edit_calls = [r for r in requests if r["method"] == "editMessageText"]
    assert len(edit_calls) == 2
    release_text = edit_calls[-1]["data"]["text"]
    assert "Статус: свободно" in release_text
