from contextlib import suppress

from aiogram import Router, Bot, html
from sqlalchemy.orm import Session
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.types import Message, CallbackQuery
from loguru import logger

from other.constants import MTLChats
from services.command_registry_service import update_command_info
from services.app_context import AppContext
from services.skyuser import SkyUser
from shared.domain.user import SpamStatus

router = Router()


class UnbanCallbackData(CallbackData, prefix="unban"):
    user_id: int
    chat_id: int


@router.message(Command(commands=["ban", "sban"]))
async def cmd_ban(message: Message, session: Session, bot: Bot, app_context: AppContext, skyuser: SkyUser):
    if not app_context or not app_context.utils_service or not app_context.feature_flags or not app_context.moderation_service:
        raise ValueError("app_context with utils_service, feature_flags, and moderation_service required")
    skynet_admin = skyuser.is_skynet_admin()

    admin = await skyuser.is_admin()

    if not (skynet_admin or (admin and message.reply_to_message)):
        await message.reply(skyuser.admin_denied_text("You are not my admin."))
        return False

    with suppress(TelegramBadRequest):
        if message.reply_to_message:
            user_id = message.reply_to_message.from_user.id
            username = message.reply_to_message.from_user.username

            await app_context.utils_service.sleep_and_delete(message.reply_to_message, 5)

            msg = await message.reply_to_message.forward(chat_id=MTLChats.SpamGroup)
            spam_check = app_context.feature_flags.is_enabled(message.chat.id, 'no_first_link')
            chat_url = html.link(message.chat.title, message.get_url())
            await msg.reply(f"Was banned by {message.from_user.username} in {chat_url} chat.\n"
                            f"Spam check: {spam_check}")
        elif len(message.text.split()) > 1 and skynet_admin:
            try:
                user_id = app_context.moderation_service.get_user_id(session, message.text.split()[1])
                username = None
            except ValueError as e:
                await message.reply(str(e))
                return
        else:
            await message.reply("You need to specify user ID or @username and be skynet admin.")
            return

        await app_context.moderation_service.ban_user(session, message.chat.id, user_id, bot)

        msg = await message.answer(f"User (ID: {user_id}) has been banned.")
        if message.reply_to_message is None:
            await message.bot.send_message(chat_id=MTLChats.SpamGroup,
                                         text=f"User (ID: {user_id}) has been banned by "
                                              f"{message.from_user.username} in {message.chat.title} chat.")

        # If the command is sban, delete the messages quickly
        tm  = 2 if message.text.startswith("/sban") else 10

        await app_context.utils_service.sleep_and_delete(message, tm)
        await app_context.utils_service.sleep_and_delete(msg, tm)


@router.message(Command(commands=["unban"]))
async def cmd_unban(message: Message, session: Session, bot: Bot, app_context: AppContext, skyuser: SkyUser):
    if not app_context or not app_context.moderation_service:
        raise ValueError("app_context with moderation_service required")
    if not skyuser.is_skynet_admin():
        await message.reply("You are not my admin.")
        return False

    if len(message.text.split()) > 1:
        try:
            param = message.text.split()[1]
            if param.isdigit() or (param.startswith('-') and param[1:].isdigit()):
                user_id = int(param)
            else:
                user_id = app_context.moderation_service.get_user_id(session, param)
        except ValueError as e:
            await message.reply(str(e))
            return

        await app_context.moderation_service.unban_user(session, message.chat.id, user_id, bot)

        await message.reply(f"User (ID: {user_id}) has been unbanned.")
    else:
        await message.reply("You need to specify user ID or @username.")


@update_command_info("/test_id", "Узнать статус ID в списке заблокированных\nПример: /test_id id или /test_id -100id")
@router.message(Command(commands=["test_id"]))
async def cmd_test_id(message: Message, session: Session, bot: Bot, app_context: AppContext, skyuser: SkyUser):
    if not app_context or not app_context.moderation_service:
        raise ValueError("app_context with moderation_service required")
    if len(message.text.split()) > 1:
        param = message.text.split()[1]
        try:
            if param.isdigit() or (param.startswith('-') and param[1:].isdigit()):
                user_id = int(param)
            else:
                user_id = app_context.moderation_service.get_user_id(session, param)
        except ValueError as e:
            await message.reply(str(e))
            return
    else:
        user_id = skyuser.sender_chat_id if message.from_user.id == MTLChats.Channel_Bot else message.from_user.id

    user_status = app_context.moderation_service.check_user_status(session, user_id)

    if user_status == SpamStatus.NEW:
        message_text = "New User"
    elif user_status == SpamStatus.GOOD:
        message_text = "Good User"
    elif user_status == SpamStatus.BAD:
        message_text = "Bad User"
    else:
        message_text = f"unknown status {user_status}"

    await message.reply(f"User ID: {user_id}, Type: {message_text}")


@router.callback_query(UnbanCallbackData.filter())
async def cmd_q_unban(call: CallbackQuery, session: Session, bot: Bot, callback_data: UnbanCallbackData, app_context: AppContext, skyuser: SkyUser):
    if not app_context or not app_context.moderation_service:
        raise ValueError("app_context with moderation_service required")
    if not skyuser.is_skynet_admin():
        await call.answer("You are not my admin.", show_alert=True)
        return False

    await app_context.moderation_service.unban_user(session, callback_data.chat_id, callback_data.user_id, bot)

    await call.answer("User unbanned successfully.")
    await call.message.delete_reply_markup()


def register_handlers(dp, bot):
    dp.include_router(router)
    logger.info('router moderation was loaded')
