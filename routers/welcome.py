import json
import re

from aiogram import Router, Bot, F
from aiogram.enums import ParseMode
from aiogram.filters import Command, Text, ChatMemberUpdatedFilter, IS_NOT_MEMBER, IS_MEMBER
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions, \
    ChatMemberUpdated, ChatMemberMember
from loguru import logger
from sqlalchemy.orm import Session

from db.requests import db_save_bot_user, db_save_bot_value, db_load_bot_value, db_send_admin_message
from utils.aiogram_utils import is_admin, cmd_delete_later
from utils.global_data import MTLChats, global_data, BotValueTypes, is_skynet_admin
from utils.stellar_utils import stellar_stop_all_exchange

router = Router()


class CaptchaCallbackData(CallbackData, prefix="captcha"):
    answer: int


@router.message(Command(commands=["delete_income"]))
async def cmd_delete_income(message: Message, session: Session):
    if not await is_admin(message):
        await message.reply('You are not admin.')
        return False

    if message.chat.id in global_data.delete_income:
        global_data.delete_income[message.chat.id] = None
        db_save_bot_value(session, message.chat.id, BotValueTypes.DeleteIncome, None)
        await message.reply('Removed')
    else:
        type_delete = 1
        if len(message.text.split()) > 1:
            global_data.delete_income[message.chat.id] = message.text.split()[1]
        global_data.delete_income[message.chat.id] = 1
        db_save_bot_value(session, message.chat.id, BotValueTypes.DeleteIncome, type_delete)
        await message.reply('Added')


@router.message(Command(commands=["delete_welcome"]))
async def cmd_delete_welcome(message: Message, session: Session):
    if not await is_admin(message):
        await message.reply('You are not admin.')
        return False

    if message.chat.id in global_data.welcome_messages:
        global_data.welcome_messages[message.chat.id] = None
        db_save_bot_value(session, message.chat.id, BotValueTypes.WelcomeMessage, None)

    msg = await message.reply('Removed')
    cmd_delete_later(msg, 1)
    cmd_delete_later(message, 1)


@router.message(Command(commands=["set_welcome"]))
async def cmd_set_welcome(message: Message, session: Session):
    if not await is_admin(message):
        await message.reply('You are not admin.')
        return False

    if len(message.text.split()) > 1:
        global_data.welcome_messages[message.chat.id] = message.html_text[13:]
        db_save_bot_value(session, message.chat.id, BotValueTypes.WelcomeMessage, message.html_text[13:])
        msg = await message.reply('Added')
        cmd_delete_later(msg, 1)
    else:
        await cmd_delete_welcome(message, session)

    cmd_delete_later(message, 1)


@router.message(Command(commands=["set_reply_only"]))
async def cmd_set_reply_only(message: Message, session: Session):
    if not await is_admin(message):
        await message.reply('You are not admin.')
        return False

    if message.chat.id in global_data.reply_only:
        global_data.reply_only.remove(message.chat.id)
        db_save_bot_value(session, message.chat.id, BotValueTypes.ReplyOnly, None)
        await message.reply('Removed')
    else:
        global_data.reply_only.append(message.chat.id)
        db_save_bot_value(session, message.chat.id, BotValueTypes.ReplyOnly, 1)
        await message.reply('Added')

    cmd_delete_later(message, 1)


@router.message(Command(commands=["set_welcome_button"]))
async def cmd_set_welcome(message: Message, session: Session):
    if not await is_admin(message):
        await message.reply('You are not admin.')
        return False

    if len(message.text.split()) > 1:
        global_data.welcome_button[message.chat.id] = message.text[19:]
        db_save_bot_value(session, message.chat.id, BotValueTypes.WelcomeButton, message.text[19:])
        msg = await message.reply('Added')
        cmd_delete_later(msg, 1)
    else:
        msg = await message.reply('need more words')
        cmd_delete_later(msg, 1)

    cmd_delete_later(message, 1)


@router.message(Command(commands=["set_captcha"]))
async def cmd_set_captcha(message: Message, session: Session):
    if not await is_admin(message):
        await message.reply('You are not admin.')
        return False

    if message.text.split()[1] == 'on':
        global_data.captcha.append(message.chat.id)
        db_save_bot_value(session, message.chat.id, BotValueTypes.Captcha, 1)
        msg = await message.reply('captcha on')
        cmd_delete_later(msg, 1)
    elif message.text.split()[1] == 'off':
        global_data.captcha.remove(message.chat.id)
        db_save_bot_value(session, message.chat.id, BotValueTypes.Captcha, None)
        msg = await message.reply('captcha off')
        cmd_delete_later(msg, 1)
    cmd_delete_later(message, 1)


@router.message(Command(commands=["stop_exchange"]))
async def cmd_stop_exchange(message: Message, session: Session):
    if not is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return False

    db_save_bot_value(session, 0, BotValueTypes.StopExchange, 1)
    stellar_stop_all_exchange()

    await message.reply('Was stop')


@router.message(Command(commands=["start_exchange"]))
async def cmd_start_exchange(message: Message, session: Session):
    if not is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return False

    db_save_bot_value(session, 0, BotValueTypes.StopExchange, None)

    await message.reply('Was start')


@router.chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def new_chat_member(event: ChatMemberUpdated, session: Session, bot: Bot):
    if event.chat.id in global_data.welcome_messages:
        if event.new_chat_member.user:
            msg = global_data.welcome_messages.get(event.chat.id, 'Hi new user')
            if event.from_user.username:
                username = f'@{event.new_chat_member.user.username} {event.new_chat_member.user.full_name}'
            else:
                username = f'<a href="tg://user?id={event.new_chat_member.user.id}">{event.new_chat_member.user.full_name}</a>'
            msg = msg.replace('$$USER$$', username)

            kb_captcha = None
            if event.chat.id in global_data.captcha:
                btn_msg = global_data.welcome_button.get(event.chat.id, "I'm not bot")
                kb_captcha = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text=btn_msg,
                                         callback_data=CaptchaCallbackData(answer=event.new_chat_member.user.id).pack())
                ]])

                try:
                    await event.chat.restrict(event.new_chat_member.user.id,
                                              permissions=ChatPermissions(can_send_messages=False,
                                                                          can_send_media_messages=False,
                                                                          can_send_other_messages=False))
                except Exception as e:
                    db_send_admin_message(session, f'new_chat_member error {type(e)} {event.chat.json()}')

            answer = await bot.send_message(event.chat.id, msg, parse_mode=ParseMode.HTML,
                                            disable_web_page_preview=True,
                                            reply_markup=kb_captcha)
            cmd_delete_later(answer)

    if event.chat.id in global_data.auto_all:
        members = json.loads(db_load_bot_value(session, event.chat.id, BotValueTypes.All, '[]'))
        if event.new_chat_member.user.username:
            members.append('@' + event.new_chat_member.user.username)
        else:
            await bot.send_message(event.chat.id,
                                   f'{event.new_chat_member.user.full_name} dont have username cant add to /all')
        db_save_bot_value(session, event.chat.id, BotValueTypes.All, json.dumps(members))


@router.chat_member(ChatMemberUpdatedFilter(IS_MEMBER >> IS_NOT_MEMBER))
async def left_chat_member(event: ChatMemberUpdated, session: Session, bot: Bot):
    if event.chat.id in global_data.auto_all:
        members = json.loads(db_load_bot_value(session, event.chat.id, BotValueTypes.All, '[]'))
        if event.from_user.username:
            members.remove('@' + event.from_user.username)
            db_save_bot_value(session, event.chat.id, BotValueTypes.All, json.dumps(members))


def contains_emoji(s: str) -> bool:
    emoji_pattern = re.compile("["
                               u"\U0001F600-\U0001F64F"  # emoticons
                               u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                               u"\U0001F680-\U0001F6FF"  # transport & map symbols
                               u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                               u"\U00002702-\U000027B0"
                               u"\U000024C2-\U0001F251"
                               "]+", flags=re.UNICODE)
    return bool(emoji_pattern.search(s))


@router.message(F.new_chat_members)
@router.message(F.left_chat_member)
async def msg_delete_income(message: Message):
    """
    # только удаляем сообщения о входе
    """
    if message.chat.id in global_data.delete_income:
        if global_data.delete_income[message.chat.id] == 2:
            if contains_emoji(message.from_user.full_name):
                await message.delete()
        else:
            await message.delete()


# new_chat_members = [
#    User(id=5148120261, is_bot=False, first_name='Вредитель', last_name=None, username=None, language_code='ru',
#         is_premium=None, added_to_attachment_menu=None, can_join_groups=None, can_read_all_group_messages=None,
#         supports_inline_queries=None)]
# left_chat_member = User(id=5148120261, is_bot=False, first_name='Вредитель', last_name=None, username=None,
#                        language_code='ru', is_premium=None, added_to_attachment_menu=None, can_join_groups=None,
#                        can_read_all_group_messages=None, supports_inline_queries=None)


@router.callback_query(CaptchaCallbackData.filter())
async def cq_captcha(query: CallbackQuery, callback_data: CaptchaCallbackData, bot: Bot):
    answer = callback_data.answer
    if query.from_user.id == answer:
        await query.answer("Thanks !", show_alert=True)
        chat = await bot.get_chat(query.message.chat.id)
        await query.message.chat.restrict(query.from_user.id, permissions=chat.permissions)
    else:
        await query.answer("For other user", show_alert=True)
    await query.answer()


@router.message(Command(commands=["recaptcha"]))
async def cmd_recaptcha(message: Message, session: Session):
    if not await is_admin(message):
        await message.reply('You are not admin.')
        return False

    if len(message.text.split()) < 2:
        msg = await message.reply('need more words')
        cmd_delete_later(msg)
        return

    await message.answer(' '.join(message.text.split(' ')[1:]), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text='Get Captcha',
                             callback_data='ReCaptcha')
    ]]))
    await message.delete()


@router.callback_query(Text(text=["ReCaptcha"]))
async def cq_recaptcha(query: CallbackQuery, session: Session, bot: Bot):
    await new_chat_member(ChatMemberUpdated(chat=query.message.chat,
                                            from_user=query.from_user,
                                            new_chat_member=ChatMemberMember(user=query.from_user),
                                            old_chat_member=ChatMemberMember(user=query.from_user),
                                            date=query.message.date
                                            ), session, bot)
    await query.answer()
