import pytest
from aiogram import types

from other import antispam_logic
from tests.fakes import FakeAsyncMethod


@pytest.mark.asyncio
async def test_set_vote_sends_keyboard_when_enabled(monkeypatch, router_app_context):
    monkeypatch.setattr(antispam_logic, "app_context", router_app_context, raising=True)

    chat_id = 123
    router_app_context.voting_service.enable_first_vote(chat_id)

    message = type("Msg", (), {})()
    message.sender_chat = None
    message.from_user = types.User(id=100, is_bot=False, first_name="Test")
    message.chat = types.Chat(id=chat_id, type="supergroup")
    message.message_id = 10
    message.reply = FakeAsyncMethod(return_value=None)

    await antispam_logic.set_vote(message)

    message.reply.assert_awaited_once()
    args, kwargs = message.reply.call_args
    text = kwargs.get("text") if kwargs else (args[0] if args else "")
    assert "detect spam messages" in text

    reply_markup = kwargs.get("reply_markup")
    assert reply_markup is not None
    assert len(reply_markup.inline_keyboard[0]) == 2


@pytest.mark.asyncio
async def test_set_vote_does_nothing_when_disabled(monkeypatch, router_app_context):
    monkeypatch.setattr(antispam_logic, "app_context", router_app_context, raising=True)

    message = type("Msg", (), {})()
    message.sender_chat = None
    message.from_user = types.User(id=101, is_bot=False, first_name="Test")
    message.chat = types.Chat(id=999, type="supergroup")
    message.message_id = 11
    message.reply = FakeAsyncMethod(return_value=None)

    await antispam_logic.set_vote(message)

    message.reply.assert_not_called()
