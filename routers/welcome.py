import asyncio
import json
import random
import re
from contextlib import suppress

from aiogram import Router, Bot, F, html
from aiogram.enums import ParseMode, ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import (Command, ChatMemberUpdatedFilter, IS_NOT_MEMBER, IS_MEMBER, PROMOTED_TRANSITION, MEMBER,
                             ADMINISTRATOR)
from aiogram.filters.callback_data import CallbackData
from aiogram.types import (Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions,
                            ChatMemberUpdated, ChatMemberMember, ChatJoinRequest)
from loguru import logger
from sqlalchemy.orm import Session

from db.requests import db_send_admin_message
from routers.multi_handler import check_membership
from routers.moderation import UnbanCallbackData
from start import add_bot_users
from other.aiogram_tools import is_admin, cmd_sleep_and_delete, get_username_link, get_chat_link
from other.global_data import global_data, BotValueTypes, is_skynet_admin, update_command_info, MTLChats
from other.pyro_tools import GroupMember
from other.spam_cheker import combo_check_spammer, lols_check_spammer
from other.stellar_tools import stellar_stop_all_exchange

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
async def cmd_delete_welcome(message: Message, session: Session):
    if not await is_admin(message):
        await message.reply('You are not admin.')
        return False

    if message.chat.id in global_data.welcome_messages:
        global_data.welcome_messages[message.chat.id] = None
        await global_data.mongo_config.save_bot_value(message.chat.id, BotValueTypes.WelcomeMessage, None)

    msg = await message.reply('Removed')
    await cmd_sleep_and_delete(msg, 60)
    await cmd_sleep_and_delete(message, 60)


@update_command_info("/set_welcome", "Установить сообщение приветствия при входе. Шаблон на имя $$USER$$", 2,
                     "welcome_messages")
@router.message(Command(commands=["set_welcome"]))
async def cmd_set_welcome(message: Message, session: Session):
    if not await is_admin(message):
        await message.reply('You are not admin.')
        return False

    if len(message.text.split()) > 1:
        global_data.welcome_messages[message.chat.id] = message.html_text[13:]
        await global_data.mongo_config.save_bot_value(message.chat.id, BotValueTypes.WelcomeMessage,
                                                      message.html_text[13:])
        msg = await message.reply('Added')
        await cmd_sleep_and_delete(msg, 60)
    else:
        await cmd_delete_welcome(message, session)

    await cmd_sleep_and_delete(message, 60)


@update_command_info("/set_welcome_button", "Установить текст на кнопке капчи", 2, "welcome_button")
@router.message(Command(commands=["set_welcome_button"]))
async def cmd_set_welcome(message: Message, session: Session):
    if not await is_admin(message):
        await message.reply('You are not admin.')
        return False

    if len(message.text.split()) > 1:
        global_data.welcome_button[message.chat.id] = message.text[19:]
        await global_data.mongo_config.save_bot_value(message.chat.id, BotValueTypes.WelcomeButton, message.text[19:])
        msg = await message.reply('Added')
        await cmd_sleep_and_delete(msg, 60)
    else:
        msg = await message.reply('need more words')
        await cmd_sleep_and_delete(msg, 60)

    await cmd_sleep_and_delete(message, 60)


@update_command_info("/stop_exchange", "Остановить ботов обмена. Только для админов")
@router.message(Command(commands=["stop_exchange"]))
async def cmd_stop_exchange(message: Message, session: Session):
    if not is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return False

    await global_data.mongo_config.save_bot_value(0, BotValueTypes.StopExchange, 1)
    stellar_stop_all_exchange()

    await message.reply('Was stop')


@update_command_info("/start_exchange", "Запустить ботов обмена. Только для админов")
@router.message(Command(commands=["start_exchange"]))
async def cmd_start_exchange(message: Message, session: Session):
    if not is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return False

    await global_data.mongo_config.save_bot_value(0, BotValueTypes.StopExchange, None)

    await message.reply('Was start')


bad_names = ['ЧВК ВАГНЕР', 'ЧВК ВАГНЕР']


@router.chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def new_chat_member(event: ChatMemberUpdated, session: Session, bot: Bot):
    new_user_id = event.new_chat_member.user.id
    if await combo_check_spammer(new_user_id):
        await bot.ban_chat_member(event.chat.id, event.new_chat_member.user.id)
        await bot.send_message(MTLChats.SpamGroup,
                               f'{event.new_chat_member.user.mention_html()} '
                               f'был забанен в чате {get_chat_link(event.chat)}'
                               f'Reason: <a href="https://cas.chat/query?u={new_user_id}">CAS ban</a>',
                               disable_web_page_preview=True)
        return

    if await lols_check_spammer(new_user_id):
        await bot.ban_chat_member(event.chat.id, event.new_chat_member.user.id)
        await bot.send_message(MTLChats.SpamGroup,
                               f'{event.new_chat_member.user.mention_html()} '
                               f'был забанен в чате {get_chat_link(event.chat)}'
                               f'Reason: <a href="https://lols.bot/?u={new_user_id}">LOLS base</a>',
                               disable_web_page_preview=True)
        return

    if event.new_chat_member.user.full_name in bad_names:
        await bot.ban_chat_member(event.chat.id, event.new_chat_member.user.id)
        await bot.send_message(MTLChats.SpamGroup,
                               f'{event.new_chat_member.user.mention_html()} '
                               f'был забанен в чате {get_chat_link(event.chat)}'
                               f' за использование запрещенного никнейма')
        return

    member = GroupMember(user_id=event.new_chat_member.user.id,
                         username=event.new_chat_member.user.username,
                         full_name=event.new_chat_member.user.full_name,
                         is_admin=False)
    _ = asyncio.create_task(global_data.mongo_config.add_user_to_chat(event.chat.id, member))
    user_type_now = global_data.check_user(event.new_chat_member.user.id)
    username = get_username_link(event.new_chat_member.user)
    if user_type_now == 2:
        with suppress(TelegramBadRequest):
            await bot.ban_chat_member(event.chat.id, event.new_chat_member.user.id)
        kb_unban = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text='unban',
                                 callback_data=UnbanCallbackData(user_id=event.new_chat_member.user.id,
                                                                 chat_id=event.chat.id).pack())
        ]])
        # await bot.send_message(event.chat.id, f'{username} was banned', reply_markup=kb_unban)
        await bot.send_message(MTLChats.SpamGroup, f'{username} was banned in {get_chat_link(event.chat)}',
                               reply_markup=kb_unban)

    if event.chat.id in global_data.welcome_messages:
        if event.new_chat_member.user:
            msg = global_data.welcome_messages.get(event.chat.id, 'Hi new user')
            msg = msg.replace('$$USER$$', username)

            kb_captcha = None
            if event.chat.id in global_data.captcha:
                btn_msg = global_data.welcome_button.get(event.chat.id, "I'm not bot")
                kb_captcha = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text=btn_msg,
                                         callback_data=CaptchaCallbackData(answer=event.new_chat_member.user.id).pack())
                ]])
                random_color = random.randint(0, 8)
                if msg.find('$$COLOR$$') > 0:
                    msg = msg.replace('$$COLOR$$', emoji_pairs[0][random_color])
                    kb_captcha = create_emoji_captcha_keyboard(event.new_chat_member.user.id, random_color)

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
            await cmd_sleep_and_delete(answer)

    if event.chat.id in global_data.auto_all:
        members = json.loads(await global_data.mongo_config.load_bot_value(event.chat.id, BotValueTypes.All, '[]'))
        if event.new_chat_member.user.username:
            members.append('@' + event.new_chat_member.user.username)
        else:
            await bot.send_message(event.chat.id,
                                   f'{event.new_chat_member.user.full_name} dont have username cant add to /all')
        await global_data.mongo_config.save_bot_value(event.chat.id, BotValueTypes.All, json.dumps(members))


@router.chat_member(ChatMemberUpdatedFilter(IS_MEMBER >> IS_NOT_MEMBER))
async def left_chat_member(event: ChatMemberUpdated, session: Session, bot: Bot):
    _ = asyncio.create_task(global_data.mongo_config.remove_user_from_chat(event.chat.id,
                                                                           event.new_chat_member.user.id))
    if event.chat.id in global_data.auto_all:
        members = json.loads(await global_data.mongo_config.load_bot_value(event.chat.id, BotValueTypes.All, '[]'))
        if event.from_user.username:
            username = '@' + event.from_user.username
            if username in members:
                members.remove(username)
            await global_data.mongo_config.save_bot_value(event.chat.id, BotValueTypes.All, json.dumps(members))
    if event.new_chat_member.status == ChatMemberStatus.KICKED:
        if is_skynet_admin(event):
            logger.info(
                f"{event.old_chat_member.user} kicked from {get_chat_link(event.chat)} by {event.from_user.username}")
            if (await check_membership(bot, MTLChats.SerpicaGroup, event.old_chat_member.user.id) or
                    await check_membership(bot, MTLChats.MTLAAgoraGroup, event.old_chat_member.user.id) or
                    await check_membership(bot, MTLChats.ClubFMCGroup, event.old_chat_member.user.id)):
                return

            add_bot_users(session, event.old_chat_member.user.id, None, 2)
            username = get_username_link(event.new_chat_member.user)
            kb_unban = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text='unban',
                                     callback_data=UnbanCallbackData(user_id=event.new_chat_member.user.id,
                                                                     chat_id=event.chat.id).pack())
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
async def msg_delete_income(message: Message):
    """
    # только удаляем сообщения о входе
    """
    if message.chat.id in global_data.delete_income:
        with suppress(TelegramBadRequest):
            if global_data.delete_income[message.chat.id] == 2:
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
        await query.message.chat.restrict(query.from_user.id, permissions=chat.permissions)
    else:
        await query.answer("For other user", show_alert=True)
    await query.answer()


@router.callback_query(EmojiCaptchaCallbackData.filter())
async def cq_captcha(query: CallbackQuery, callback_data: EmojiCaptchaCallbackData, bot: Bot):
    if query.from_user.id == callback_data.user_id:
        index = emoji_pairs[1].index(callback_data.square)
        if get_last_digit_of_sum(callback_data.num) == index:
            await query.answer("Thanks !", show_alert=True)
            chat = await bot.get_chat(query.message.chat.id)
            await query.message.chat.restrict(query.from_user.id, permissions=chat.permissions)
        else:
            await query.answer("Wrong answer", show_alert=True)
            await query.message.delete_reply_markup()
    else:
        await query.answer("For other user", show_alert=True)


@router.message(Command(commands=["recaptcha"]))
async def cmd_recaptcha(message: Message, session: Session):
    if not await is_admin(message):
        await message.reply('You are not admin.')
        return False

    if len(message.text.split()) < 2:
        msg = await message.reply('need more words')
        await cmd_sleep_and_delete(msg)
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
    await global_data.mongo_config.save_bot_value(event.chat.id, BotValueTypes.Admins, json.dumps(new_admins))


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
        if chat_id in global_data.join_request_captcha:
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
async def cq_join(query: CallbackQuery, callback_data: JoinCallbackData, bot: Bot):
    if not await is_admin(query, callback_data.chat_id):
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
