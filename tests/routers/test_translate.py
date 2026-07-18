"""Tests for the Telegram translation command."""

import datetime
import html
import importlib
import json

import pytest
from aiogram import types

from tests.fakes import FakeAsyncMethod


def _translate_module():
    return importlib.import_module("routers.translate")


@pytest.mark.parametrize(
    ("code", "language"),
    [
        ("ru", "Russian"),
        ("EN", "English"),
        ("es", "Spanish"),
        ("de", "German"),
        ("me", "Montenegrin"),
        ("cnr", "Montenegrin"),
    ],
)
def test_parse_translation_request_normalizes_supported_language(code, language):
    translate = _translate_module()

    assert translate.parse_translation_request(f"/tr {code} hello") == (language, "hello")


def test_parse_translation_request_prefers_inline_text():
    translate = _translate_module()

    result = translate.parse_translation_request(
        "/tr es inline text",
        reply_text="reply text",
        reply_caption="reply caption",
    )

    assert result == ("Spanish", "inline text")


def test_parse_translation_request_uses_reply_text_before_caption():
    translate = _translate_module()

    result = translate.parse_translation_request(
        "/translate de",
        reply_text="reply text",
        reply_caption="reply caption",
    )

    assert result == ("German", "reply text")


def test_parse_translation_request_uses_reply_caption():
    translate = _translate_module()

    result = translate.parse_translation_request("/tr me", reply_caption="reply caption")

    assert result == ("Montenegrin", "reply caption")


@pytest.mark.parametrize("command", ["/tr", "/tr zz text"])
def test_parse_translation_request_rejects_missing_or_unknown_language(command):
    translate = _translate_module()

    assert translate.parse_translation_request(command, reply_text="reply text") == (None, None)


def test_parse_translation_request_returns_language_when_source_is_missing():
    translate = _translate_module()

    assert translate.parse_translation_request("/tr en") == ("English", None)


def _make_message(text: str, *, reply: types.Message | None = None) -> types.Message:
    return types.Message(
        message_id=42,
        date=datetime.datetime.now(),
        chat=types.Chat(id=-100123, type="supergroup", title="Test"),
        from_user=types.User(id=123, is_bot=False, first_name="User"),
        text=text,
        reply_to_message=reply,
    )


@pytest.mark.asyncio
async def test_translate_command_sends_escaped_translation_as_reply(mock_telegram, router_bot, router_app_context):
    translate = _translate_module()
    mock_translate = FakeAsyncMethod(return_value="<Hola & mundo>")
    router_app_context.ai_service.translate = mock_translate
    message = _make_message("/tr es Hello world").as_(router_bot)

    await translate.cmd_translate(message, router_app_context)

    mock_translate.assert_awaited_once_with("Hello world", "Spanish")
    requests = mock_telegram.get_requests()
    assert any(request["method"] == "sendChatAction" for request in requests)
    send_calls = [request for request in requests if request["method"] == "sendMessage"]
    assert len(send_calls) == 1
    assert send_calls[0]["data"]["text"] == html.escape("<Hola & mundo>", quote=False)
    reply_parameters = json.loads(send_calls[0]["data"]["reply_parameters"])
    assert reply_parameters["message_id"] == message.message_id


@pytest.mark.asyncio
async def test_translate_command_uses_reply_caption(mock_telegram, router_bot, router_app_context):
    translate = _translate_module()
    mock_translate = FakeAsyncMethod(return_value="Translated caption")
    router_app_context.ai_service.translate = mock_translate
    reply = types.Message(
        message_id=41,
        date=datetime.datetime.now(),
        chat=types.Chat(id=-100123, type="supergroup", title="Test"),
        caption="Original caption",
    )
    message = _make_message("/translate de", reply=reply).as_(router_bot)

    await translate.cmd_translate(message, router_app_context)

    mock_translate.assert_awaited_once_with("Original caption", "German")


@pytest.mark.asyncio
@pytest.mark.parametrize("command", ["/tr", "/tr zz text", "/tr en"])
async def test_invalid_translate_command_does_not_call_llm(
    command,
    mock_telegram,
    router_bot,
    router_app_context,
):
    translate = _translate_module()
    mock_translate = FakeAsyncMethod(return_value="unused")
    router_app_context.ai_service.translate = mock_translate
    message = _make_message(command).as_(router_bot)

    await translate.cmd_translate(message, router_app_context)

    mock_translate.assert_not_called()
    send_calls = [request for request in mock_telegram.get_requests() if request["method"] == "sendMessage"]
    assert len(send_calls) == 1


@pytest.mark.asyncio
async def test_translate_command_handles_llm_failure(mock_telegram, router_bot, router_app_context):
    translate = _translate_module()
    router_app_context.ai_service.translate = FakeAsyncMethod(return_value=None)
    message = _make_message("/tr ru Hello").as_(router_bot)

    await translate.cmd_translate(message, router_app_context)

    send_calls = [request for request in mock_telegram.get_requests() if request["method"] == "sendMessage"]
    assert send_calls[-1]["data"]["text"] == "Не удалось перевести, попробуйте позже."


def test_translation_html_chunks_are_safe_and_bounded():
    translate = _translate_module()
    source = "<&>" * 2000

    chunks = translate.escape_translation_chunks(source)

    assert all(len(chunk) <= 4000 for chunk in chunks)
    assert html.unescape("".join(chunks)) == source


def test_translate_handler_has_dedicated_rate_limit():
    translate = _translate_module()

    assert translate.cmd_translate.global_user_throttling_rate_limit == 5
    assert translate.cmd_translate.global_user_throttling_key == "translate"
