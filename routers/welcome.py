import asyncio
import json
import random
import re
import datetime
from contextlib import suppress

from aiogram import Router, Bot, F
from aiogram.enums import ParseMode, ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import (Command, ChatMemberUpdatedFilter, IS_NOT_MEMBER, IS_MEMBER, PROMOTED_TRANSITION, MEMBER,
                             ADMINISTRATOR)
from aiogram.filters.callback_data import CallbackData
from aiogram.types import (Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions,
                           ChatMemberUpdated, ChatMemberMember, ChatJoinRequest)
from loguru import logger
from sqlalchemy.orm import Session

from db.repositories import MessageRepository
# from routers.multi_handler import check_membership, enforce_entry_channel
from routers.moderation import UnbanCallbackData
from start import add_bot_users
from other.aiogram_tools import is_admin, cmd_sleep_and_delete, get_username_link, get_chat_link
from other.constants import MTLChats, BotValueTypes
from services.command_registry_service import update_command_info
from other.pyro_tools import GroupMember
from shared.domain.user import SpamStatus
from db.repositories import ConfigRepository, ChatsRepository
# from other.spam_cheker import combo_check_spammer, lols_check_spammer

router = Router()


class CaptchaCallbackData(CallbackData, prefix="captcha"):
    answer: int


class JoinCallbackData(CallbackData, prefix="join"):
    user_id: int
    chat_id: int
    can_join: bool


class EmojiCaptchaCallbackData(CallbackData, prefix="e_captcha"):
    user_id: int
    square: str
    num: int


def generate_number_with_sum(target_sum):
    while True:
        # Генерируем случайное четырехзначное число
        num = random.randint(1000, 9999)
        # Вычисляем сумму цифр этого числа
        digits_sum = sum(int(digit) for digit in str(num))
        # Если сумма цифр оканчивается на нужную цифру, возвращаем число
        if digits_sum % 10 == target_sum:
            return num


def get_last_digit_of_sum(number):
    digits_sum = sum(int(digit) for digit in str(number))
    return digits_sum % 10


emoji_pairs = [
    ["🔴", "🟠", "🟡", "🟢", "🔵", "🟣", "⚫️", "⚪️", "🟤"],  # Круги
    ["🟥", "🟧", "🟨", "🟩", "🟦", "🟪", "⬛️", "⬜️", "🟫"]  # Квадраты
]

dal = ("🔴🟤",  # 1 9  # 0 8
       "🟠🟢",  # 2 4   # 1 3
       "🔵🟣")  # 5 6   # 4 5


# первый и последний; второй и четвертый; пятый и шестой; для дальтоников сильно похожи

def create_emoji_captcha_keyboard(user_id, required_num):
    random_indices = random.sample(range(9), 6)

    if required_num not in random_indices:
        random_indices[random.randint(0, 5)] = required_num

    buttons = []

    for index in random_indices:
        square = emoji_pairs[1][index]
        num = generate_number_with_sum(index)
        if index != required_num:
            num += 1
        button = InlineKeyboardButton(
            text=square,
            callback_data=EmojiCaptchaCallbackData(user_id=user_id, square=square, num=num).pack()
        )
        buttons.append(button)

    random.shuffle(buttons)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        buttons[:3],
        buttons[3:]
    ])

    return keyboard


@update_command_info("/delete_welcome", "Отключить сообщения приветствия")
@router.message(Command(commands=["delete_welcome"]))
async def cmd_delete_welcome(message: Message, session: Session, app_context=None):
    admin = await app_context.utils_service.is_admin(message)

    if not admin:
        await message.reply('You are not admin.')
        return False

    has_welcome = app_context.config_service.get_welcome_message(message.chat.id) is not None

    if has_welcome:
        app_context.config_service.remove_welcome_message(message.chat.id, session)

    msg = await message.reply('Removed')
    await app_context.utils_service.sleep_and_delete(msg, 60)
    await app_context.utils_service.sleep_and_delete(message, 60)


@update_command_info("/set_welcome", "Установить сообщение приветствия при входе. Шаблон на имя $$USER$$", 2,
                     "welcome_messages")
@router.message(Command(commands=["set_welcome"]))
async def cmd_set_welcome(message: Message, session: Session, app_context=None):
    admin = await app_context.utils_service.is_admin(message)

    if not admin:
        await message.reply('You are not admin.')
        return False

    if len(message.text.split()) > 1:
        welcome_text = message.html_text[13:]

        app_context.config_service.set_welcome_message(message.chat.id, welcome_text, session)
        msg = await message.reply('Added')
        await app_context.utils_service.sleep_and_delete(msg, 60)
    else:
        await cmd_delete_welcome(message, session, app_context=app_context)

    await app_context.utils_service.sleep_and_delete(message, 60)


@update_command_info("/set_welcome_button", "Установить текст на кнопке капчи", 2, "welcome_button")
@router.message(Command(commands=["set_welcome_button"]))
async def cmd_set_welcome_button(message: Message, session: Session, app_context=None):
    admin = await app_context.utils_service.is_admin(message)

    if not admin:
        await message.reply('You are not admin.')
        return False

    if len(message.text.split()) > 1:
        text = message.text[19:].strip()

        app_context.config_service.set_welcome_button(message.chat.id, text, session)
        msg = await message.reply('Added')
        await app_context.utils_service.sleep_and_delete(msg, 60)
    else:
        msg = await message.reply('need more words')
        await app_context.utils_service.sleep_and_delete(msg, 60)

    await app_context.utils_service.sleep_and_delete(message, 60)


@update_command_info("/stop_exchange", "Остановить ботов обмена. Только для админов")
@router.message(Command(commands=["stop_exchange"]))
async def cmd_stop_exchange(message: Message, session: Session, app_context=None):
    is_admin_user = app_context.admin_service.is_skynet_admin(message.from_user.username)

    if not is_admin_user:
        await message.reply('You are not my admin.')
        return False

    ConfigRepository(session).save_bot_value(0, BotValueTypes.StopExchange, 1)
    app_context.stellar_service.stop_all_exchange()

    await message.reply('Was stop')


@update_command_info("/start_exchange", "Запустить ботов обмена. Только для админов")
@router.message(Command(commands=["start_exchange"]))
async def cmd_start_exchange(message: Message, session: Session, app_context=None):
    is_admin_user = app_context.admin_service.is_skynet_admin(message.from_user.username)

    if not is_admin_user:
        await message.reply('You are not my admin.')
        return False

    ConfigRepository(session).save_bot_value(0, BotValueTypes.StopExchange, None)
    await message.reply('Was start')


bad_names = ['ЧВК ВАГНЕР', 'ЧВК ВАГНЕР']


@router.chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def new_chat_member(event: ChatMemberUpdated, session: Session, bot: Bot, app_context=None):
    new_user_id = event.new_chat_member.user.id
    chat_id = event.chat.id

    is_spam1 = await app_context.antispam_service.combo_check_spammer(new_user_id)

    if is_spam1:
        await bot.ban_chat_member(chat_id, event.new_chat_member.user.id)
        await bot.send_message(MTLChats.SpamGroup,
                               f'{event.new_chat_member.user.mention_html()} '
                               f'был забанен в чате {get_chat_link(event.chat)}'
                               f'Reason: <a href="https://cas.chat/query?u={new_user_id}">CAS ban</a>',
                               disable_web_page_preview=True)
        return

    is_spam2 = await app_context.antispam_service.lols_check_spammer(new_user_id)

    if is_spam2:
        await bot.ban_chat_member(chat_id, event.new_chat_member.user.id)
        await bot.send_message(MTLChats.SpamGroup,
                               f'{event.new_chat_member.user.mention_html()} '
                               f'был забанен в чате {get_chat_link(event.chat)}'
                               f'Reason: <a href="https://lols.bot/?u={new_user_id}">LOLS base</a>',
                               disable_web_page_preview=True)
        return

    if event.new_chat_member.user.full_name in bad_names:
        await bot.ban_chat_member(chat_id, event.new_chat_member.user.id)
        await bot.send_message(MTLChats.SpamGroup,
                               f'{event.new_chat_member.user.mention_html()} '
                               f'был забанен в чате {get_chat_link(event.chat)}'
                               f' за использование запрещенного никнейма')
        return

    required_channel = app_context.config_service.load_value(chat_id, 'entry_channel')

    if required_channel:
        membership_ok, _ = await app_context.group_service.enforce_entry_channel(bot, chat_id, new_user_id, required_channel)
        if not membership_ok:
            return

    member = GroupMember(user_id=event.new_chat_member.user.id,
                         username=event.new_chat_member.user.username,
                         full_name=event.new_chat_member.user.full_name,
                         is_admin=False)

    ChatsRepository(session).add_user_to_chat(chat_id, member)
    user = ChatsRepository(session).get_user_by_id(event.new_chat_member.user.id)
    user_type_now = user.user_type if user else 0

    username = get_username_link(event.new_chat_member.user)
    if user_type_now == SpamStatus.BAD:
        with suppress(TelegramBadRequest):
            await bot.ban_chat_member(chat_id, event.new_chat_member.user.id)
        kb_unban = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text='unban',
                                 callback_data=UnbanCallbackData(user_id=event.new_chat_member.user.id,
                                                                 chat_id=chat_id).pack())
        ]])
        # await bot.send_message(chat_id, f'{username} was banned', reply_markup=kb_unban)
        await bot.send_message(MTLChats.SpamGroup, f'{username} was banned in {get_chat_link(event.chat)}',
                               reply_markup=kb_unban)

    welcome_msg = app_context.config_service.get_welcome_message(chat_id)

    if welcome_msg:
        if event.new_chat_member.user:
            msg = welcome_msg if welcome_msg else 'Hi new user'
            msg = msg.replace('$$USER$$', username)

            kb_captcha = None
            captcha_enabled = app_context.feature_flags.is_enabled(chat_id, 'captcha')

            if captcha_enabled:
                btn_msg = app_context.config_service.get_welcome_button(chat_id) or "I'm not bot"

                kb_captcha = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text=btn_msg,
                                         callback_data=CaptchaCallbackData(answer=event.new_chat_member.user.id).pack())
                ]])
                random_color = random.randint(0, 8)
                if msg.find('$$COLOR$$') > 0:
                    msg = msg.replace('$$COLOR$$', emoji_pairs[0][random_color])
                    kb_captcha = create_emoji_captcha_keyboard(event.new_chat_member.user.id, random_color)

                try:
                    await bot.restrict_chat_member(chat_id, event.new_chat_member.user.id,
                                              permissions=ChatPermissions(can_send_messages=False,
                                                                          can_send_media_messages=False,
                                                                          can_send_other_messages=False))
                except Exception as e:
                    MessageRepository(session).send_admin_message(f'new_chat_member error {type(e)} {event.chat.model_dump_json()}')

            answer = await bot.send_message(chat_id, msg, parse_mode=ParseMode.HTML,
                                            disable_web_page_preview=True,
                                            reply_markup=kb_captcha)
            await app_context.utils_service.sleep_and_delete(answer)

    auto_all_enabled = app_context.feature_flags.is_enabled(chat_id, 'auto_all')

    if auto_all_enabled:
        config_repo = ConfigRepository(session)
        json_str = config_repo.load_bot_value(chat_id, BotValueTypes.All, '[]')
        members = json.loads(json_str) if json_str else []

        if event.new_chat_member.user.username:
            members.append('@' + event.new_chat_member.user.username)
        else:
            await bot.send_message(chat_id,
                                   f'{event.new_chat_member.user.full_name} dont have username cant add to /all')

        config_repo.save_bot_value(chat_id, BotValueTypes.All, json.dumps(members))


@router.chat_member(ChatMemberUpdatedFilter(IS_MEMBER >> IS_NOT_MEMBER))
async def left_chat_member(event: ChatMemberUpdated, session: Session, bot: Bot, app_context=None):
    chat_id = event.chat.id

    ChatsRepository(session).remove_user_from_chat(chat_id, event.new_chat_member.user.id)

    auto_all_enabled = app_context.feature_flags.is_enabled(chat_id, 'auto_all')

    if auto_all_enabled:
        config_repo = ConfigRepository(session)
        json_str = config_repo.load_bot_value(chat_id, BotValueTypes.All, '[]')
        members = json.loads(json_str) if json_str else []

        if event.from_user.username:
            username = '@' + event.from_user.username
            if username in members:
                members.remove(username)
            config_repo.save_bot_value(chat_id, BotValueTypes.All, json.dumps(members))

    if event.new_chat_member.status == ChatMemberStatus.KICKED:
        is_admin_user = app_context.admin_service.is_skynet_admin(event.from_user.username)

        if is_admin_user:
            logger.info(
                f"{event.old_chat_member.user} kicked from {get_chat_link(event.chat)} by {event.from_user.username}")

            c1, _ = await app_context.group_service.check_membership(bot, MTLChats.SerpicaGroup, event.old_chat_member.user.id)
            c2, _ = await app_context.group_service.check_membership(bot, MTLChats.MTLAAgoraGroup, event.old_chat_member.user.id)
            c3, _ = await app_context.group_service.check_membership(bot, MTLChats.ClubFMCGroup, event.old_chat_member.user.id)
            in_other_chats = c1 or c2 or c3

            if in_other_chats:
                return

            add_bot_users(session, event.old_chat_member.user.id, None, 2)
            username = get_username_link(event.new_chat_member.user)
            kb_unban = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text='unban',
                                     callback_data=UnbanCallbackData(user_id=event.new_chat_member.user.id,
                                                                     chat_id=chat_id).pack())
            ]])
            await bot.send_message(MTLChats.SpamGroup, f'{username} was banned in {get_chat_link(event.chat)}',
                                   reply_markup=kb_unban)


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
async def msg_delete_income(message: Message, app_context=None):
    """
    # только удаляем сообщения о входе
    """
    chat_id = message.chat.id

    # Get delete_income config using DI service (app_context required)
    delete_income_config = None
    if app_context and app_context.config_service:
        delete_income_config = app_context.config_service.get_delete_income(chat_id)

    if delete_income_config is not None:
        with suppress(TelegramBadRequest):
            if delete_income_config == 2:
                if contains_emoji(message.from_user.full_name):
                    await message.delete()
            else:
                await message.delete()


@router.callback_query(CaptchaCallbackData.filter())
async def cq_captcha(query: CallbackQuery, callback_data: CaptchaCallbackData, bot: Bot):
    answer = callback_data.answer
    if query.from_user.id == answer:
        await query.answer("Thanks !", show_alert=True)
        chat = await bot.get_chat(query.message.chat.id)
        await bot.restrict_chat_member(query.message.chat.id, query.from_user.id, permissions=chat.permissions,
                                       until_date=datetime.timedelta(seconds=65))
    else:
        await query.answer("For other user", show_alert=True)
    await query.answer()


@router.callback_query(EmojiCaptchaCallbackData.filter())
async def cq_emoji_captcha(query: CallbackQuery, callback_data: EmojiCaptchaCallbackData, bot: Bot):
    if query.from_user.id == callback_data.user_id:
        index = emoji_pairs[1].index(callback_data.square)
        if get_last_digit_of_sum(callback_data.num) == index:
            await query.answer("Thanks !", show_alert=True)
            chat = await bot.get_chat(query.message.chat.id)
            await bot.restrict_chat_member(query.message.chat.id, query.from_user.id, permissions=chat.permissions,
                                           until_date=datetime.timedelta(seconds=65))
        else:
            await query.answer("Wrong answer", show_alert=True)
            await query.message.delete_reply_markup()
    else:
        await query.answer("For other user", show_alert=True)


@router.message(Command(commands=["recaptcha"]))
async def cmd_recaptcha(message: Message, session: Session, app_context=None):
    admin = await app_context.utils_service.is_admin(message)

    if not admin:
        await message.reply('You are not admin.')
        return None

    if len(message.text.split()) < 2:
        msg = await message.reply('need more words')
        await app_context.utils_service.sleep_and_delete(msg)
        return None

    await message.answer(' '.join(message.text.split(' ')[1:]), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text='Get Captcha',
                             callback_data='ReCaptcha')
    ]]))
    await message.delete()
    return None


@router.callback_query(F.data == "ReCaptcha")
async def cq_recaptcha(query: CallbackQuery, session: Session, bot: Bot, app_context=None):
    await new_chat_member(ChatMemberUpdated(chat=query.message.chat,
                                            from_user=query.from_user,
                                            new_chat_member=ChatMemberMember(user=query.from_user),
                                            old_chat_member=ChatMemberMember(user=query.from_user),
                                            date=query.message.date
                                            ), session, bot, app_context=app_context)
    await query.answer()


@router.chat_member(ChatMemberUpdatedFilter(PROMOTED_TRANSITION))
@router.chat_member(ChatMemberUpdatedFilter(ADMINISTRATOR >> MEMBER))
async def cmd_update_admin(event: ChatMemberUpdated, session: Session, bot: Bot, app_context=None):
    chat_id = event.chat.id

    # Chat is accessible if we received this update - remove from inaccessible list
    from routers.admin_panel import unmark_chat_accessible
    unmark_chat_accessible(chat_id, session)

    members = await event.chat.get_administrators()
    new_admins = [member.user.id for member in members]

    app_context.admin_service.set_chat_admins(chat_id, new_admins)
    ConfigRepository(session).save_bot_value(chat_id, BotValueTypes.Admins, json.dumps(new_admins))


@router.chat_join_request()
async def handle_chat_join_request(chat_join_request: ChatJoinRequest, bot: Bot, app_context=None):
    chat_id = chat_join_request.chat.id
    user_id = chat_join_request.from_user.id

    info_chat_id = app_context.notification_service.get_join_notify_config(chat_id)

    if info_chat_id:
        username = get_username_link(chat_join_request.from_user)

        kb_join = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Принять",
                                 callback_data=JoinCallbackData(user_id=user_id, chat_id=chat_id,
                                                                can_join=True).pack()),
            InlineKeyboardButton(text="Отказать",
                                 callback_data=JoinCallbackData(user_id=user_id, chat_id=chat_id,
                                                                can_join=False).pack())
        ]])

        if len(str(info_chat_id)) > 5:
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

        join_request_captcha_enabled = app_context.feature_flags.is_enabled(chat_id, 'join_request_captcha')

        if join_request_captcha_enabled:
            with suppress(TelegramBadRequest, TelegramForbiddenError):
                edit_button_url = f'https://t.me/myMTLbot/JoinCaptcha?startapp={chat_id}'

                # Создаем клавиатуру с кнопками
                reply_markup = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text='Start Captcha v1', url=edit_button_url + '_1')],
                    [InlineKeyboardButton(text='Start Captcha v2', url=edit_button_url + '_2')]
                ])
                await bot.send_message(chat_id=chat_join_request.user_chat_id,
                                       text=f"К сожалению из-за натиска ботов в чат добавляются только "
                                            f"те кто прошел проверку. \n\n"
                                            f"Для того чтоб зайти в чат '{chat_join_request.chat.title}' вам "
                                            f"надо нажать на одну из кнопок ниже и подтвердить что вы человек. ",
                                       reply_markup=reply_markup)

    # Optional: Auto-approve join request
    # await bot.approve_chat_join_request(chat_id, user_id)


@router.callback_query(JoinCallbackData.filter())
async def cq_join(query: CallbackQuery, callback_data: JoinCallbackData, bot: Bot, app_context=None):
    admin = await app_context.utils_service.is_admin(query, callback_data.chat_id)

    if not admin:
        await query.answer('You are not admin.', show_alert=True)
        return False

    if callback_data.can_join:
        with suppress(TelegramBadRequest):
            await query.bot.approve_chat_join_request(callback_data.chat_id, callback_data.user_id)
        await query.answer("✅")
        await query.message.edit_reply_markup(
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text=f"✅ {query.from_user.username}", callback_data="👀")]]))

    else:
        await query.bot.decline_chat_join_request(callback_data.chat_id, callback_data.user_id)
        await query.answer("❌")
        await query.message.edit_reply_markup(
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text=f"❌ {query.from_user.username}", callback_data="👀")]]))

    # await query.answer("Ready !", show_alert=True)


def register_handlers(dp, bot):
    dp.include_router(router)
    logger.info('router welcome was loaded')


if __name__ == '__main__':
    print(create_emoji_captcha_keyboard(1, 0))
