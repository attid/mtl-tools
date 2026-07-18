"""Telegram command handlers for stateless LLM translation."""

import html
from typing import Any, cast

from aiogram import Router
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.types import Message
from loguru import logger

from middlewares.throttling import global_user_rate_limit
from services.app_context import AppContext
from services.command_registry_service import update_command_info

router = Router()

SUPPORTED_LANGUAGES = {
    "ru": "Russian",
    "en": "English",
    "es": "Spanish",
    "de": "German",
    "me": "Montenegrin",
    "cnr": "Montenegrin",
}
USAGE_TEXT = (
    "Использование: <code>/tr en текст</code> или ответьте "
    "<code>/tr en</code> на сообщение. Языки: ru, en, es, de, me/cnr."
)
NO_SOURCE_TEXT = "Не найден текст для перевода. Добавьте текст после языка или ответьте на сообщение."
TRANSLATION_ERROR_TEXT = "Не удалось перевести, попробуйте позже."


def parse_translation_request(
    command_text: str,
    *,
    reply_text: str | None = None,
    reply_caption: str | None = None,
) -> tuple[str | None, str | None]:
    """Return normalized target language and source text from a command."""
    parts = command_text.split(maxsplit=2)
    if len(parts) < 2:
        return None, None

    target_language = SUPPORTED_LANGUAGES.get(parts[1].lower())
    if target_language is None:
        return None, None

    inline_text = parts[2].strip() if len(parts) == 3 else ""
    source_text = inline_text or reply_text or reply_caption
    return target_language, source_text


def escape_translation_chunks(text: str, limit: int = 4000) -> list[str]:
    """Escape untrusted text and split it without breaking HTML entities."""
    chunks: list[str] = []
    current: list[str] = []
    current_length = 0

    for char in text:
        escaped_char = html.escape(char, quote=False)
        if current and current_length + len(escaped_char) > limit:
            chunks.append("".join(current))
            current = []
            current_length = 0
        current.append(escaped_char)
        current_length += len(escaped_char)

    if current:
        chunks.append("".join(current))
    return chunks


@router.message(Command(commands=["tr", "translate"]))
@update_command_info("/tr", "Перевести текст: /tr <ru|en|es|de|me|cnr> [текст]")
@global_user_rate_limit(5, "translate")
async def cmd_translate(message: Message, app_context: AppContext) -> None:
    """Translate inline text or the text/caption of a replied message."""
    if not app_context or not app_context.ai_service:
        raise ValueError("app_context with ai_service required")

    reply = message.reply_to_message
    target_language, source_text = parse_translation_request(
        message.text or "",
        reply_text=reply.text if reply else None,
        reply_caption=reply.caption if reply else None,
    )
    if target_language is None:
        await message.reply(USAGE_TEXT)
        return
    if not source_text:
        await message.reply(NO_SOURCE_TEXT)
        return

    bot = message.bot
    if bot is None:
        raise ValueError("message with bot instance required")

    await bot.send_chat_action(
        chat_id=message.chat.id,
        action=ChatAction.TYPING,
        message_thread_id=message.message_thread_id,
    )
    ai_service = cast(Any, app_context.ai_service)
    try:
        translated = await ai_service.translate(source_text, target_language)
    except Exception:
        logger.exception(
            "Translation request failed: chat={} user={} target={}",
            message.chat.id,
            message.from_user.id if message.from_user else None,
            target_language,
        )
        translated = None

    if not translated or not translated.strip():
        await message.reply(TRANSLATION_ERROR_TEXT)
        return

    for chunk in escape_translation_chunks(translated):
        await message.reply(chunk)


def register_handlers(dp, bot) -> None:
    """Register translation handlers."""
    dp.include_router(router)
    logger.info("router translate was loaded")
