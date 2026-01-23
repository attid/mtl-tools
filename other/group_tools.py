import asyncio
from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import User
from loguru import logger

async def check_membership(bot: Bot, chat_id: str, user_id: int) -> tuple[bool, User | None]:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        is_member = member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR]
        return is_member, member.user

    except TelegramBadRequest:
        return False, None

async def enforce_entry_channel(bot: Bot, chat_id: int, user_id: int, required_channel: str) -> tuple[bool, bool]:
    is_member, _ = await check_membership(bot, required_channel, user_id)
    if is_member:
        return True, False

    try:
        await bot.unban_chat_member(chat_id, user_id)
        await asyncio.sleep(0.2)
        return False, True
    except (TelegramBadRequest, TelegramForbiddenError) as exc:
        logger.warning(f'enforce_entry_channel failed for user {user_id} in chat {chat_id}: {exc}')
        return False, False
