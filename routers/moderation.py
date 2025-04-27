from contextlib import suppress

from aiogram import Router, Bot, html
from sqlalchemy.orm import Session
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.types import Message, CallbackQuery
from loguru import logger

from db.requests import db_get_user_id
from other.aiogram_tools import is_admin, cmd_sleep_and_delete
from other.global_data import global_data, is_skynet_admin, update_command_info, MTLChats
from start import add_bot_users


router = Router()


class UnbanCallbackData(CallbackData, prefix="unban"):
    user_id: int
    chat_id: int


@router.message(Command(commands=["ban"]))
async def cmd_ban(message: Message, session: Session, bot: Bot):
    skynet_admin = is_skynet_admin(message)
    admin = await is_admin(message)

    if not (skynet_admin or (admin and message.reply_to_message)):
        await message.reply("You are not my admin.")
        return False

    with suppress(TelegramBadRequest):
        if message.reply_to_message:
            user_id = message.reply_to_message.from_user.id
            username = message.reply_to_message.from_user.username
            await cmd_sleep_and_delete(message.reply_to_message, 5)
            msg = await message.reply_to_message.forward(chat_id=MTLChats.SpamGroup)
            spam_check = message.chat.id in global_data.no_first_link
            chat_url = html.link(message.chat.title, message.get_url())
            await msg.reply(f"Was banned by {message.from_user.username} in {chat_url} chat.\n"
                            f"Spam check: {spam_check}")
        elif len(message.text.split()) > 1 and skynet_admin:
            try:
                user_id = db_get_user_id(session, message.text.split()[1])
                username = None  # We don't have the username here, it's okay for now
            except ValueError as e:
                await message.reply(str(e))
                return
        else:
            await message.reply("You need to specify user ID or @username and be skynet admin.")
            return

        await bot.ban_chat_member(message.chat.id, user_id, revoke_messages=True)
        add_bot_users(session, user_id, username, 2)
        msg = await message.answer(f"User (ID: {user_id}) has been banned.")
        if message.reply_to_message is None:
            await message.bot.send_message(chat_id=MTLChats.SpamGroup,
                                         text=f"User (ID: {user_id}) has been banned by "
                                              f"{message.from_user.username} in {message.chat.title} chat.")
        await cmd_sleep_and_delete(message, 5)
        await cmd_sleep_and_delete(msg, 5)


@router.message(Command(commands=["unban"]))
async def cmd_unban(message: Message, session: Session, bot: Bot):
    if not is_skynet_admin(message):
        await message.reply("You are not my admin.")
        return False

    if len(message.text.split()) > 1:
        try:
            param = message.text.split()[1]
            if param.isdigit() or (param.startswith('-') and param[1:].isdigit()):
                user_id = int(param)
            else:
                user_id = db_get_user_id(session, param)
        except ValueError as e:
            await message.reply(str(e))
            return

        with suppress(TelegramBadRequest):
            if user_id > 0:
                await bot.unban_chat_member(message.chat.id, user_id)
            else: #-100xxxxxxxxxx
                await bot.unban_chat_sender_chat(message.chat.id, user_id)

        add_bot_users(session, user_id, None, 0)
        await message.reply(f"User (ID: {user_id}) has been unbanned.")
    else:
        await message.reply("You need to specify user ID or @username.")


@update_command_info("/test_id", "Узнать статус ID в списке заблокированных\nПример: /test_id id или /test_id -100id")
@router.message(Command(commands=["test_id"]))
async def cmd_test_id(message: Message, session: Session, bot: Bot):
    if len(message.text.split()) > 1:
        param = message.text.split()[1]
        try:
            if param.isdigit() or (param.startswith('-') and param[1:].isdigit()):
                user_id = int(param)
            else:
                user_id = db_get_user_id(session, param)
        except ValueError as e:
            await message.reply(str(e))
            return
    else:
        user_id = message.sender_chat.id if message.from_user.id == MTLChats.Channel_Bot else message.from_user.id

    user_type = global_data.check_user(user_id)
    if user_type == 0:
        message_text = "New User"
    elif user_type == 1:
        message_text = "Good User"
    elif user_type == 2:
        message_text = "Bad User"
    else:
        message_text = f"unknown status {user_type}"

    await message.reply(f"User ID: {user_id}, Type: {message_text}")


@router.callback_query(UnbanCallbackData.filter())
async def cmd_q_unban(call: CallbackQuery, session: Session, bot: Bot, callback_data: UnbanCallbackData):
    if not is_skynet_admin(call):
        await call.answer("You are not my admin.", show_alert=True)
        return False

    with suppress(TelegramBadRequest):
        await bot.unban_chat_member(callback_data.chat_id, callback_data.user_id)
        add_bot_users(session, callback_data.user_id, None, 0)
        await call.answer("User unbanned successfully.")
        await call.message.delete_reply_markup()


def register_handlers(dp, bot):
    dp.include_router(router)
    logger.info('router moderation was loaded')