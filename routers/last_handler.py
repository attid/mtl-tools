import asyncio
import html
from contextlib import suppress

from aiogram import F, Bot, Router
from aiogram.enums import MessageEntityType
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters.callback_data import CallbackData
from aiogram.types import (Message, ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery,
                           ReplyParameters)
from loguru import logger
from sqlalchemy.orm import Session

from db.requests import extract_url, db_save_message, db_get_user_id, db_update_user_chat_date
from middlewares.throttling import rate_limit
from start import add_bot_users
from utils.aiogram_utils import (multi_reply, is_admin, ChatInOption,
                                 get_username_link, cmd_sleep_and_delete)
from utils.dialog import talk_check_spam
from utils.global_data import MTLChats, BotValueTypes, global_data
from utils.pyro_tools import MessageInfo
from utils.spam_cheker import is_mixed_word, contains_spam_phrases
from utils.stellar_utils import check_url_xdr
from utils.telegraph_tools import telegraph

router = Router()


class SpamCheckCallbackData(CallbackData, prefix="SpamCheck"):
    message_id: int
    chat_id: int
    user_id: int
    good: bool
    new_message_id: int


class ReplyCallbackData(CallbackData, prefix="Reply"):
    message_id: int
    chat_id: int
    user_id: int


class FirstMessageCallbackData(CallbackData, prefix="first"):
    user_id: int
    message_id: int
    spam: bool


########################################################################################################################
##########################################  functions  #################################################################
########################################################################################################################

async def save_url(chat_id, msg_id, msg):
    url = extract_url(msg)
    await global_data.mongo_config.save_bot_value(chat_id, BotValueTypes.PinnedUrl, url)
    await global_data.mongo_config.save_bot_value(chat_id, BotValueTypes.PinnedId, msg_id)


async def check_spam(message, session):
    if message.from_user.id in global_data.users_list and global_data.users_list[message.from_user.id] == 1:
        return False

    rules_name = 'xz'
    process_message = False
    if message.entities:
        custom_emoji_count = 0
        for entity in message.entities:
            if entity.type in ('url', 'text_link', 'mention'):
                rules_name = 'link'
                process_message = True
                break  # Прерываем цикл, так как нашли ссылку или упоминание
            elif entity.type == 'custom_emoji':
                custom_emoji_count += 1

        if custom_emoji_count > 3:
            process_message = True
            rules_name = 'emoji'

    words = message.text.split()
    mixed_word_count = sum(is_mixed_word(word) for word in words)
    if mixed_word_count >= 3:
        process_message = True
        rules_name = 'mixed'

    if contains_spam_phrases(message.text):
        process_message = True
        rules_name = 'spam_phrases'

    if not process_message:
        spam_persent = await talk_check_spam(message.text)
        logger.info(f"{spam_persent} {message.text}")
        if spam_persent and spam_persent > 69:
            process_message = True
            rules_name = 'open AI'

    if process_message:
        await message.chat.restrict(message.from_user.id,
                                    permissions=ChatPermissions(can_send_messages=False,
                                                                can_send_media_messages=False,
                                                                can_send_other_messages=False))
        msg = await message.forward(MTLChats.SpamGroup)
        chat_link = f'@{message.chat.username}' if message.chat.username else message.chat.invite_link
        msg_text =  f'Сообщение из чата {message.chat.title} {chat_link}\n{rules_name}'
        if message.reply_to_message:
            msg_text += f'\nОтвет на сообщение: {message.reply_to_message.get_url()}'

        await msg.reply(msg_text,
                        reply_markup=InlineKeyboardMarkup(
                            inline_keyboard=[[InlineKeyboardButton(text='Restore. Its good msg !',
                                                                   callback_data=SpamCheckCallbackData(
                                                                       message_id=message.message_id,
                                                                       chat_id=message.chat.id,
                                                                       user_id=message.from_user.id,
                                                                       new_message_id=msg.message_id,
                                                                       good=True).pack())],
                                             [InlineKeyboardButton(text='Its spam! Kick him !',
                                                                   callback_data=SpamCheckCallbackData(
                                                                       message_id=message.message_id,
                                                                       chat_id=message.chat.id,
                                                                       user_id=message.from_user.id,
                                                                       new_message_id=msg.message_id,
                                                                       good=False).pack())]
                                             ]))
        await message.delete()
        add_bot_users(session, message.from_user.id, message.from_user.username, 0)
        return True
    else:
        add_bot_users(session, message.from_user.id, message.from_user.username, 1)
        await set_vote(message)
        return False


async def set_vote(message):
    if message.chat.id in global_data.first_vote:
        kb_reply = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Spam",
                                 callback_data=FirstMessageCallbackData(spam=True,
                                                                        message_id=message.message_id,
                                                                        user_id=message.from_user.id).pack()),
            InlineKeyboardButton(text="Good",
                                 callback_data=FirstMessageCallbackData(spam=False,
                                                                        message_id=message.message_id,
                                                                        user_id=message.from_user.id).pack()), ]])
        await message.reply(text="Please help me detect spam messages", reply_markup=kb_reply)


async def check_alert(bot, message, session):
    # if user need be alert
    if message.entities and message.chat.id in global_data.alert_me:
        for entity in message.entities:
            if entity.type == 'mention':
                username = entity.extract_from(message.text)
                try:
                    user_id = db_get_user_id(session, username)
                except ValueError as ex:
                    user_id = 0
                    logger.warning(ex)
                if user_id > 0 and user_id in global_data.alert_me[message.chat.id]:
                    with suppress(TelegramBadRequest, TelegramForbiddenError):
                        alert_username = get_username_link(message.from_user)
                        msg_info = MessageInfo(chat_id=message.chat.id,
                                               user_from=message.from_user.username,
                                               message_id=message.message_id,
                                               chat_name=message.chat.title,
                                               message_text=message.html_text)
                        if message.reply_to_message:
                            msg_info.reply_to_message = MessageInfo(
                                chat_id=message.chat.id,
                                user_from=message.reply_to_message.from_user.username,
                                message_id=message.reply_to_message.message_id,
                                message_text=message.reply_to_message.html_text)

                        telegraph_link = await telegraph.create_uuid_page(msg_info)
                        buttons = [[InlineKeyboardButton(text=f'ПП {msg_info.chat_name[:30]}',
                                                         url=telegraph_link.url)]]

                        await bot.send_message(user_id, f'Вас упомянул {alert_username}\n'
                                                        f'В чате {message.chat.title}\n'
                                                        f'Ссылка на сообщение {message.get_url()}',
                                               reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


async def save_last(message, session):
    if message.chat.id in global_data.save_last_message_date:
        db_update_user_chat_date(session, message.from_user.id, message.chat.id)


async def notify_message(message: Message):
    if message.is_automatic_forward:
        return

    if message.chat.id in global_data.notify_message:
        record = global_data.notify_message[message.chat.id].split(':')
        dest_chat = record[0]
        dest_topic = record[1] if len(record) > 1 else None
        if len(dest_chat) > 3:
            kb_reply = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="BanAndDelete",
                                     callback_data=ReplyCallbackData(chat_id=message.chat.id,
                                                                     message_id=message.message_id,
                                                                     user_id=message.from_user.id).pack()),
                InlineKeyboardButton(text="👀",
                                     callback_data="👀"),
            ]])

            dest_chat_member = await message.bot.get_chat_member(dest_chat, message.from_user.id)
            username = message.from_user.username
            if dest_chat_member.status != 'left':
                user_mention = f"{username}" if username else f"{message.from_user.first_name}"
            else:
                user_mention = f"@{username}" if username else f"{message.from_user.first_name}"

            msg = await message.bot.send_message(
                chat_id=dest_chat,
                message_thread_id=dest_topic,
                text=f'User {user_mention}: \nChat: {html.escape(message.chat.title)}',
                reply_markup=kb_reply,
                reply_parameters=ReplyParameters(
                    message_id=message.message_id,
                    chat_id=message.chat.id)
            )
            # print(msg)


async def cmd_check_reply_only(message: Message, session: Session, bot: Bot):
    has_hashtag = False
    if message.entities:
        for entity in message.entities:
            if entity.type == MessageEntityType.HASHTAG:
                has_hashtag = True
                break

    if message.reply_to_message or message.forward_from_chat or has_hashtag or message.is_automatic_forward:
        db_save_message(session=session, user_id=message.from_user.id, username=message.from_user.username,
                        thread_id=message.message_thread_id if message.is_topic_message else None,
                        text=message.text, chat_id=message.chat.id)
    else:
        msg = await message.reply(
            'В этом чате включен режим контроля использования функции ответа. \n'
            'Сообщение будет удаленно через 15 секунд!\n'
            'Рекомендую скопировать его повторить его с использованием функции "ответ" на нужное сообщение.\n'
            '<a href="https://telegra.ph/rc-06-15-3">Подробнее о режиме тут</a>',
            disable_web_page_preview=True)

        await asyncio.sleep(15)
        try:
            if message.has_protected_content:
                await message.copy_to(chat_id=message.from_user.id)
            else:
                await message.forward(chat_id=message.from_user.id)
            msg_d = await bot.send_message(chat_id=message.chat.id, disable_web_page_preview=True,
                                           text=f'Сообщение от {message.from_user.username} переслано в личку.\n'
                                                '<a href="https://telegra.ph/rc-06-15-3">Подробнее о режиме тут</a>')
        except TelegramBadRequest:
            msg_d = await bot.send_message(chat_id=message.chat.id, disable_web_page_preview=True,
                                           text=f'Сообщение от {message.from_user.username} удалено\n'
                                                '<a href="https://telegra.ph/rc-06-15-3">Подробнее о режиме тут</a>')
        except TelegramForbiddenError:
            msg_d = await bot.send_message(chat_id=message.chat.id, disable_web_page_preview=True,
                                           text=f'Сообщение от {message.from_user.username} удалено. Личка в блокировке =(\n'
                                                '<a href="https://telegra.ph/rc-06-15-3">Подробнее о режиме тут</a>')
        with suppress(TelegramBadRequest):
            await message.delete()
            await msg.delete()
        await cmd_sleep_and_delete(msg_d, 120)


async def cmd_tools(message: Message, bot: Bot, session: Session):
    url_found = False
    url_text = message.text
    if message.entities:
        for entity in message.entities:
            if entity.type in ['url', 'text_link']:
                url = entity.url if entity.type == 'text_link' else message.text[entity.offset:entity.offset+entity.length]
                if 'eurmtl.me/sign_tools' in url:
                    url_found = True
                    url_text = url
                    break

    if url_found or url_text.find('eurmtl.me/sign_tools') > -1:
        msg_id = await global_data.mongo_config.load_bot_value(message.chat.id, BotValueTypes.PinnedId)
        with suppress(TelegramBadRequest):
            await bot.unpin_chat_message(message.chat.id, msg_id)

        await save_url(message.chat.id, message.message_id, url_text)
        with suppress(TelegramBadRequest):
            await message.pin()
        msg = await check_url_xdr(
            await global_data.mongo_config.load_bot_value(message.chat.id, BotValueTypes.PinnedUrl))
        msg = f'\n'.join(msg)
        await multi_reply(message, msg)



########################################################################################################################
##########################################  handlers  ##################################################################
########################################################################################################################


@rate_limit(0, 'listen')
@router.message(F.text)  # если текст #точно не приватное, приватные выше остановились
async def cmd_last_check(message: Message, session: Session, bot: Bot):
    if message.chat.id in global_data.no_first_link:
        deleted = await check_spam(message, session)
        if deleted:
            # If the message was deleted during spam check, we stop processing
            return

    if message.chat.id in global_data.need_decode:
        await cmd_tools(message, bot, session)

    if message.chat.id in global_data.save_last_message_date:
        await save_last(message, session)

    if message.chat.id in global_data.notify_message:
        await notify_message(message)

    if message.chat.id in global_data.reply_only:
        await cmd_check_reply_only(message, session, bot)

    await check_alert(bot, message, session)

    if message.chat.id in global_data.save_last_message_date:
        await save_last(message, session)

    if message.from_user.id in global_data.users_list and global_data.users_list[message.from_user.id] == 0:
        await set_vote(message)  ##########

    add_bot_users(session, message.from_user.id, message.from_user.username, 1)

    if message.chat.id in global_data.listen:
        db_save_message(session=session, user_id=message.from_user.id, username=message.from_user.username,
                        thread_id=message.message_thread_id if message.is_topic_message else None,
                        text=message.text, chat_id=message.chat.id)


########################################################################################################################
#####################################  callback_query  #################################################################
########################################################################################################################


@rate_limit(0, 'listen')
@router.callback_query(SpamCheckCallbackData.filter())
async def cq_spam_check(query: CallbackQuery, callback_data: SpamCheckCallbackData, bot: Bot, session: Session):
    if not await is_admin(query):
        await query.answer('You are not admin.', show_alert=True)
        return False

    if callback_data.good:
        chat = await bot.get_chat(callback_data.chat_id)
        await bot.forward_message(callback_data.chat_id, query.message.chat.id, callback_data.new_message_id)
        await bot.restrict_chat_member(chat_id=callback_data.chat_id, user_id=callback_data.user_id,
                                       permissions=chat.permissions)
        await query.answer("Oops, bringing the message back!", show_alert=True)
    else:
        add_bot_users(session, callback_data.user_id, None, 2)
        await query.answer("Забанен !", show_alert=True)


@router.callback_query(ReplyCallbackData.filter())
async def cq_reply_ban(query: CallbackQuery, callback_data: ReplyCallbackData):
    if not await is_admin(query, callback_data.chat_id):
        await query.answer("Вы не являетесь администратором в том чате.", show_alert=True)
        return

    with suppress(TelegramBadRequest):
        await query.bot.ban_chat_member(
            chat_id=callback_data.chat_id,
            user_id=callback_data.user_id
        )

    with suppress(TelegramBadRequest):
        await query.bot.delete_message(
            chat_id=callback_data.chat_id,
            message_id=callback_data.message_id
        )

    with suppress(TelegramBadRequest):
        await query.message.delete()

    await query.answer("Пользователь забанен и сообщения удалены.", show_alert=True)


@router.callback_query(F.data == "👀")
async def cq_look(query: CallbackQuery):
    await query.answer("👀", show_alert=True)


@router.callback_query(FirstMessageCallbackData.filter())
async def cq_first_vote_check(query: CallbackQuery, callback_data: FirstMessageCallbackData, bot: Bot,
                              session: Session):
    if query.from_user.id == callback_data.user_id:
        await query.answer("You can't vote", show_alert=True)
        return False

    key = f"{callback_data.message_id}{query.message.chat.id}"
    data = global_data.first_vote_data.get(key, {"spam": 0, "good": 0, "users": []})

    if query.from_user.id in data["users"]:
        await query.answer('You have already voted.', show_alert=True)
        return False

    # Определяем вес голоса: 5 для администраторов, 1 для остальных
    vote_weight = 5 if await is_admin(query) else 1

    # Обновляем данные голосования
    if callback_data.spam:
        data["spam"] += vote_weight
    else:
        data["good"] += vote_weight

    data["users"].append(query.from_user.id)
    global_data.first_vote_data[key] = data

    # Проверяем, достиг ли счет 5 для спама
    if data["spam"] >= 5:
        # Удаляем сообщение голосования и сообщение о котором голосование
        with suppress(TelegramBadRequest):
            await bot.delete_message(query.message.chat.id, callback_data.message_id)
        with suppress(TelegramBadRequest):
            await bot.delete_message(query.message.chat.id, query.message.message_id)

        # Рестрикт для пользователя
        with suppress(TelegramBadRequest):
            await query.message.chat.restrict(callback_data.user_id,
                                              permissions=ChatPermissions(
                                                  can_send_messages=False,
                                                  can_send_media_messages=False,
                                                  can_send_other_messages=False))
        add_bot_users(session, callback_data.user_id, None, 2)
        await query.answer('Message marked as spam and user restricted.', show_alert=True)
    elif data["good"] >= 5:
        # Если набрано 5 голосов за "Good", просто удаляем сообщение голосования
        await bot.delete_message(query.message.chat.id, query.message.message_id)
        await query.answer('Message marked as good.', show_alert=True)
    else:
        # Обновляем текст кнопок с количеством голосов
        kb_reply = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text=f"Spam ({data['spam']})",
                callback_data=FirstMessageCallbackData(spam=True, message_id=callback_data.message_id,
                                                       user_id=callback_data.user_id).pack()
            ),
            InlineKeyboardButton(
                text=f"Good ({data['good']})",
                callback_data=FirstMessageCallbackData(spam=False, message_id=callback_data.message_id,
                                                       user_id=callback_data.user_id).pack()
            )
        ]])

        # Редактируем сообщение с новыми кнопками
        await bot.edit_message_reply_markup(chat_id=query.message.chat.id, message_id=query.message.message_id,
                                            reply_markup=kb_reply)
        await query.answer('Your vote has been counted.', show_alert=True)
