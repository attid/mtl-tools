import json
import re

from aiogram import Router, Bot, F
from aiogram.enums import ParseMode
from aiogram.filters import Command, ChatMemberUpdatedFilter, IS_NOT_MEMBER, IS_MEMBER, PROMOTED_TRANSITION, MEMBER, \
    ADMINISTRATOR
from aiogram.filters.callback_data import CallbackData
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions, \
    ChatMemberUpdated, ChatMemberMember, ChatJoinRequest, User
from sqlalchemy.orm import Session
from db.requests import db_send_admin_message
from utils.aiogram_utils import is_admin, cmd_delete_later, get_username_link
from utils.global_data import global_data, BotValueTypes, is_skynet_admin, update_command_info
from utils.stellar_utils import stellar_stop_all_exchange

router = Router()


class CaptchaCallbackData(CallbackData, prefix="captcha"):
    answer: int


class JoinCallbackData(CallbackData, prefix="join"):
    user_id: int
    chat_id: int
    can_join: bool


@update_command_info("/delete_welcome", "Отключить сообщения приветствия")
@router.message(Command(commands=["delete_welcome"]))
async def cmd_delete_welcome(message: Message, session: Session):
    if not await is_admin(message):
        await message.reply('You are not admin.')
        return False

    if message.chat.id in global_data.welcome_messages:
        global_data.welcome_messages[message.chat.id] = None
        await global_data.json_config.save_bot_value(message.chat.id, BotValueTypes.WelcomeMessage, None)

    msg = await message.reply('Removed')
    cmd_delete_later(msg, 1)
    cmd_delete_later(message, 1)


@update_command_info("/set_welcome", "Установить сообщение приветствия при входе. Шаблон на имя $$USER$$")
@router.message(Command(commands=["set_welcome"]))
async def cmd_set_welcome(message: Message, session: Session):
    if not await is_admin(message):
        await message.reply('You are not admin.')
        return False

    if len(message.text.split()) > 1:
        global_data.welcome_messages[message.chat.id] = message.html_text[13:]
        await global_data.json_config.save_bot_value(message.chat.id, BotValueTypes.WelcomeMessage, message.html_text[13:])
        msg = await message.reply('Added')
        cmd_delete_later(msg, 1)
    else:
        await cmd_delete_welcome(message, session)

    cmd_delete_later(message, 1)


@update_command_info("/set_welcome_button", "Установить текст на кнопке капчи")
@router.message(Command(commands=["set_welcome_button"]))
async def cmd_set_welcome(message: Message, session: Session):
    if not await is_admin(message):
        await message.reply('You are not admin.')
        return False

    if len(message.text.split()) > 1:
        global_data.welcome_button[message.chat.id] = message.text[19:]
        await global_data.json_config.save_bot_value(message.chat.id, BotValueTypes.WelcomeButton, message.text[19:])
        msg = await message.reply('Added')
        cmd_delete_later(msg, 1)
    else:
        msg = await message.reply('need more words')
        cmd_delete_later(msg, 1)

    cmd_delete_later(message, 1)


@update_command_info("/set_captcha on", "Включает капчу")
@update_command_info("/set_captcha off", "Выключает капчу")
@router.message(Command(commands=["set_captcha"]))
async def cmd_set_captcha(message: Message, session: Session):
    if not await is_admin(message):
        await message.reply('You are not admin.')
        return False

    if message.text.split()[1] == 'on':
        global_data.captcha.append(message.chat.id)
        await global_data.json_config.save_bot_value(message.chat.id, BotValueTypes.Captcha, 1)
        msg = await message.reply('captcha on')
        cmd_delete_later(msg, 1)
    elif message.text.split()[1] == 'off':
        global_data.captcha.remove(message.chat.id)
        await global_data.json_config.save_bot_value(message.chat.id, BotValueTypes.Captcha, None)
        msg = await message.reply('captcha off')
        cmd_delete_later(msg, 1)
    cmd_delete_later(message, 1)


@update_command_info("/stop_exchange", "Остановить ботов обмена. Только для админов")
@router.message(Command(commands=["stop_exchange"]))
async def cmd_stop_exchange(message: Message, session: Session):
    if not is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return False

    await global_data.json_config.save_bot_value(0, BotValueTypes.StopExchange, 1)
    stellar_stop_all_exchange()

    await message.reply('Was stop')


@update_command_info("/start_exchange", "Запустить ботов обмена. Только для админов")
@router.message(Command(commands=["start_exchange"]))
async def cmd_start_exchange(message: Message, session: Session):
    if not is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return False

    await global_data.json_config.save_bot_value(0, BotValueTypes.StopExchange, None)

    await message.reply('Was start')


@router.chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def new_chat_member(event: ChatMemberUpdated, session: Session, bot: Bot):
    if event.chat.id in global_data.welcome_messages:
        if event.new_chat_member.user:
            msg = global_data.welcome_messages.get(event.chat.id, 'Hi new user')
            username = get_username_link(event.new_chat_member.user)
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
                    db_send_admin_message(session, f'new_chat_member error {type(e)} {event.chat.model_dump_json()}')

            answer = await bot.send_message(event.chat.id, msg, parse_mode=ParseMode.HTML,
                                            disable_web_page_preview=True,
                                            reply_markup=kb_captcha)
            cmd_delete_later(answer)

    if event.chat.id in global_data.auto_all:
        members = json.loads(await global_data.json_config.load_bot_value(event.chat.id, BotValueTypes.All, '[]'))
        if event.new_chat_member.user.username:
            members.append('@' + event.new_chat_member.user.username)
        else:
            await bot.send_message(event.chat.id,
                                   f'{event.new_chat_member.user.full_name} dont have username cant add to /all')
        await global_data.json_config.save_bot_value(event.chat.id, BotValueTypes.All, json.dumps(members))


@router.chat_member(ChatMemberUpdatedFilter(IS_MEMBER >> IS_NOT_MEMBER))
async def left_chat_member(event: ChatMemberUpdated, session: Session, bot: Bot):
    if event.chat.id in global_data.auto_all:
        members = json.loads(await global_data.json_config.load_bot_value(event.chat.id, BotValueTypes.All, '[]'))
        if event.from_user.username:
            username = '@' + event.from_user.username
            if username in members:
                members.remove(username)
            await global_data.json_config.save_bot_value(event.chat.id, BotValueTypes.All, json.dumps(members))


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


@router.callback_query(F.data == "ReCaptcha")
async def cq_recaptcha(query: CallbackQuery, session: Session, bot: Bot):
    await new_chat_member(ChatMemberUpdated(chat=query.message.chat,
                                            from_user=query.from_user,
                                            new_chat_member=ChatMemberMember(user=query.from_user),
                                            old_chat_member=ChatMemberMember(user=query.from_user),
                                            date=query.message.date
                                            ), session, bot)
    await query.answer()


@router.chat_member(ChatMemberUpdatedFilter(PROMOTED_TRANSITION))
@router.chat_member(ChatMemberUpdatedFilter(ADMINISTRATOR >> MEMBER))
async def cmd_update_admin(event: ChatMemberUpdated, session: Session, bot: Bot):
    members = await event.chat.get_administrators()
    new_admins = [member.user.id for member in members]
    global_data.admins[event.chat.id] = new_admins
    await global_data.json_config.save_bot_value(event.chat.id, BotValueTypes.Admins, json.dumps(new_admins))


@router.chat_join_request()
async def handle_chat_join_request(chat_join_request: ChatJoinRequest, bot: Bot):
    chat_id = chat_join_request.chat.id
    user_id = chat_join_request.from_user.id

    if chat_id in global_data.notify_join:
        info_chat_id = global_data.notify_join[chat_id]
        username = get_username_link(chat_join_request.from_user)

        kb_join = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Принять",
                                 callback_data=JoinCallbackData(user_id=user_id, chat_id=chat_id,
                                                                can_join=True).pack()),
            InlineKeyboardButton(text="Отказать",
                                 callback_data=JoinCallbackData(user_id=user_id, chat_id=chat_id,
                                                                can_join=False).pack())
        ]])

        if len(info_chat_id) > 5:
            await bot.send_message(
                info_chat_id,
                f"Новый участник {username} хочет присоединиться к чату \"{chat_join_request.chat.title}\". "
                f"Требуется подтверждение.",
                reply_markup=kb_join
            )
        else:
            await bot.send_message(
                chat_id,
                f"Новый участник {username} хочет присоединиться к чату. Требуется подтверждение.",
                reply_markup=kb_join
            )
    # Optional: Auto-approve join request
    # await bot.approve_chat_join_request(chat_id, user_id)


@router.callback_query(JoinCallbackData.filter())
async def cq_join(query: CallbackQuery, callback_data: JoinCallbackData, bot: Bot):
    if not await is_admin(query.message):
        await query.answer('You are not admin.', show_alert=True)
        return False

    if callback_data.can_join:
        await query.bot.approve_chat_join_request(callback_data.chat_id, callback_data.user_id)
    else:
        await query.bot.decline_chat_join_request(callback_data.chat_id, callback_data.user_id)

    await query.answer("Ready !", show_alert=True)
