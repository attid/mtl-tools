from typing import Optional, Tuple, TYPE_CHECKING

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from loguru import logger

from other.aiogram_tools import cmd_sleep_and_delete as original_sleep_and_delete

if TYPE_CHECKING:
    from services.database_service import DatabaseService


class TelegramUtilsService:
    async def sleep_and_delete(self, message, seconds):
        await original_sleep_and_delete(message, seconds)


async def get_chat_info(
    chat_id: int,
    bot: Bot,
    db_service: "DatabaseService"
) -> Tuple[Optional[str], Optional[str]]:
    """
    Get chat (title, username) - database first, API fallback.

    Returns: (title, username) tuple. Both can be None if chat is inaccessible.
    """
    # 1. Check database first
    chat = await db_service.get_chat_by_id(chat_id)
    if chat and chat.title:
        return (chat.title, chat.username)

    # 2. Fallback to Telegram API
    try:
        tg_chat = await bot.get_chat(chat_id)
        title = tg_chat.title or tg_chat.first_name
        username = tg_chat.username

        # 3. Save to database for future use
        await db_service.upsert_chat_info(chat_id, title, username)

        return (title, username)
    except (TelegramBadRequest, TelegramForbiddenError) as e:
        logger.warning(f"Cannot get chat info for {chat_id}: {e}")
        return (None, None)
