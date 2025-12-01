import asyncio
import html
import json
from contextlib import suppress
from datetime import datetime

from aiogram import F, Bot, Router
from aiogram.enums import MessageEntityType
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters.callback_data import CallbackData
from aiogram.types import (Message, ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery,
                           ReplyParameters)
from aiogram.fsm.context import FSMContext
from loguru import logger
from sqlalchemy.orm import Session

from db.requests import extract_url, db_save_message, db_get_user_id, db_update_user_chat_date
from middlewares.throttling import rate_limit
from start import add_bot_users
from other.aiogram_tools import (multi_reply, is_admin, ChatInOption,
                                 get_username_link, cmd_sleep_and_delete)
from other.open_ai_tools import talk_check_spam
from other.global_data import MTLChats, BotValueTypes, global_data
from other.pyro_tools import MessageInfo, pyro_update_msg_info
from other.spam_cheker import is_mixed_word, contains_spam_phrases, combo_check_spammer, lols_check_spammer
from other.stellar_tools import check_url_xdr
from other.telegraph_tools import telegraph
from datetime import datetime, timedelta

router = Router()


class SpamCheckCallbackData(CallbackData, prefix="SpamCheck"):
    message_id: int
    chat_id: int
    user_id: int
    good: bool
    new_message_id: int
    message_thread_id: int


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


async def delete_and_log_spam(message, session, rules_name):
    user_id = message.sender_chat.id if message.sender_chat else message.from_user.id
    user_username = message.sender_chat.username if message.sender_chat else message.from_user.username
    with suppress(TelegramBadRequest):
        await message.chat.restrict(user_id,
                                    permissions=ChatPermissions(can_send_messages=False,
                                                                can_send_media_messages=False,
                                                                can_send_other_messages=False))
    msg = await message.forward(MTLChats.SpamGroup)
    chat_link = f'@{message.chat.username}' if message.chat.username else message.chat.invite_link
    msg_text = f'Сообщение из чата {message.chat.title} {chat_link}\n{rules_name}'
    if message.reply_to_message:
        msg_text += f'\nОтвет на сообщение: {message.reply_to_message.get_url()}'

    await msg.reply(msg_text, disable_web_page_preview=True,
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[[InlineKeyboardButton(text='Restore. Its good msg !',
                                                               callback_data=SpamCheckCallbackData(
                                                                   message_id=message.message_id,
                                                                   chat_id=message.chat.id,
                                                                   user_id=user_id,
                                                                   new_message_id=msg.message_id,
                                                                   message_thread_id=message.message_thread_id if message.message_thread_id else 0,
                                                                   good=True).pack())],
                                         [InlineKeyboardButton(text='Its spam! Kick him !',
                                                               callback_data=SpamCheckCallbackData(
                                                                   message_id=message.message_id,
                                                                   chat_id=message.chat.id,
                                                                   user_id=user_id,
                                                                   new_message_id=msg.message_id,
                                                                   message_thread_id=message.message_thread_id if message.message_thread_id else 0,
                                                                   good=False).pack())]
                                         ]))
    await message.delete()
    add_bot_users(session, user_id, message.from_user.username, 0)


async def check_spam(message, session):
    if message.from_user.id == MTLChats.Telegram_Repost_Bot:
        return False

    user_id = message.sender_chat.id if message.from_user.id == MTLChats.Channel_Bot else message.from_user.id

    # if user_id in global_data.users_list:
    if global_data.check_user(user_id) == 1:
        return False

    rules_name = 'xz'
    process_message = False

    if await combo_check_spammer(user_id):
        process_message = True
        rules_name = f'<a href="https://cas.chat/query?u={user_id}">CAS ban</a>'

    if await lols_check_spammer(user_id):
        process_message = True
        rules_name = f'<a href="https://lols.bot/?u={user_id}">LOLS base</a>',

    if not process_message and message.entities:
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

    if not process_message:
        words = message.text.split()
        mixed_word_count = sum(is_mixed_word(word) for word in words)
        if mixed_word_count >= 3:
            process_message = True
            rules_name = 'mixed'

    if not process_message and contains_spam_phrases(message.text):
        process_message = True
        rules_name = 'spam_phrases'

    if not process_message:
        spam_persent = await talk_check_spam(message.text)
        logger.info(f"{spam_persent} {message.text}")
        if spam_persent and spam_persent > 69:
            process_message = True
            rules_name = 'open AI'

    if process_message:
        await delete_and_log_spam(message, session, rules_name)
        return True
    else:
        add_bot_users(session, user_id, message.from_user.username, 1)
        await set_vote(message)
        return False


async def set_vote(message):
    user_id = message.sender_chat.id if message.sender_chat else message.from_user.id
    if message.chat.id in global_data.first_vote:
        kb_reply = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Spam",
                                 callback_data=FirstMessageCallbackData(spam=True,
                                                                        message_id=message.message_id,
                                                                        user_id=user_id).pack()),
            InlineKeyboardButton(text="Good",
                                 callback_data=FirstMessageCallbackData(spam=False,
                                                                        message_id=message.message_id,
                                                                        user_id=user_id).pack()), ]])
        await message.reply(text="Please help me detect spam messages", reply_markup=kb_reply)


async def check_alert(bot, message, session):
    # if user need be alert
    if message.entities and message.chat.id in global_data.alert_me:
        # Создаем msg_info один раз для всего сообщения
        msg_info = MessageInfo(chat_id=message.chat.id,
                               user_from=message.from_user.username or "",
                               message_id=message.message_id,
                               chat_name=message.chat.title or "",
                               message_text=message.html_text or "")
        if message.reply_to_message:
            msg_info.reply_to_message = MessageInfo(
                chat_id=message.chat.id,
                user_from=message.reply_to_message.from_user.username or "" if message.reply_to_message.from_user else "",
                message_id=message.reply_to_message.message_id,
                message_text=message.reply_to_message.html_text or "")
        
        # Получаем инфу о топике через Pyro один раз для сообщения
        await pyro_update_msg_info(msg_info)
        
        # Формируем topic_info один раз
        topic_info = ""
        if getattr(msg_info, "thread_id", None):
            chat_id_num = str(abs(message.chat.id))[3:]
            thread_id = msg_info.thread_id
            thread_name = getattr(msg_info, "thread_name", None)
            #thread_link = f"https://t.me/c/{chat_id_num}/{message.message_id}?thread={thread_id}"
            thread_link = f"https://t.me/c/{chat_id_num}/{thread_id}"
            if thread_name:
                topic_info = f'Топик <a href="{thread_link}">"{thread_name}"</a>\n'
            else:
                topic_info = f'Топик <a href="{thread_link}">id {thread_id}</a>\n'

        # Создаем Telegraph страницу один раз для всего сообщения
        telegraph_link = await telegraph.create_uuid_page(msg_info)
        chat_name_display = (msg_info.chat_name or "")[:30]
        buttons = [[InlineKeyboardButton(text=f'ПП {chat_name_display}',
                                         url=telegraph_link.url)]]

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

                        await bot.send_message(
                            user_id,
                            f'Вас упомянул {alert_username}\n'
                            f'В чате {message.chat.title}\n'
                            f'{topic_info}'
                            f'Ссылка на сообщение {message.get_url()}',
                            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
                            parse_mode="HTML"
                        )


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


async def cmd_check_reply_only(message: Message, session: Session, bot: Bot, state: FSMContext):
    has_hashtag = False
    if message.entities:
        for entity in message.entities:
            if entity.type == MessageEntityType.HASHTAG:
                has_hashtag = True
                break

    # Проверяем временное разрешение от FSM
    has_temp_permission = False
    fsm_data = await state.get_data()
    expiration_str = fsm_data.get('reply_only_expiration')
    
    if expiration_str:
        try:
            expiration_time = datetime.fromisoformat(expiration_str)
            if datetime.now() <= expiration_time:
                has_temp_permission = True
            else:
                # Время истекло, удаляем наш ключ
                await state.update_data(reply_only_expiration=None)
        except ValueError:
            # Некорректный формат времени, удаляем ключ
            await state.update_data(reply_only_expiration=None)

    # Если есть хэштег, устанавливаем временное разрешение
    if has_hashtag:
        expiration_time = datetime.now() + timedelta(minutes=1)
        await state.update_data(reply_only_expiration=expiration_time.isoformat())

    if message.reply_to_message or message.forward_from_chat or has_hashtag or has_temp_permission or message.is_automatic_forward:
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
                url = entity.url if entity.type == 'text_link' else message.text[
                                                                    entity.offset:entity.offset + entity.length]
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
        msg = '\n'.join(msg)
        await multi_reply(message, msg)


async def check_mute(message, session):
    #     global_data.topic_mute[chat_thread_key][user_id] = {"end_time": end_time, "user": user}
    #     await global_data.mongo_config.save_bot_value(0, BotValueTypes.TopicMutes, json.dumps(global_data.topic_mute))
    if message.chat.id not in global_data.moderate:
        return False

    chat_thread_key = f"{message.chat.id}-{message.message_thread_id}"

    if chat_thread_key not in global_data.topic_mute:
        return False

    user_id = message.from_user.id
    if user_id not in global_data.topic_mute[chat_thread_key]:
        return False

    mute_info = global_data.topic_mute[chat_thread_key][user_id]
    current_time = datetime.now()

    try:
        end_time = datetime.fromisoformat(mute_info["end_time"])
    except ValueError as e:
        logger.error(f"Invalid date format for user {user_id} in chat {chat_thread_key}: {e}")
        # Remove the invalid entry
        del global_data.topic_mute[chat_thread_key][user_id]
        if not global_data.topic_mute[chat_thread_key]:
            del global_data.topic_mute[chat_thread_key]
        await global_data.mongo_config.save_bot_value(0, BotValueTypes.TopicMutes,
                                                      json.dumps(global_data.topic_mute))
        return False

    if current_time < end_time:
        await message.delete()
        return True
    else:
        del global_data.topic_mute[chat_thread_key][user_id]
        if not global_data.topic_mute[chat_thread_key]:
            del global_data.topic_mute[chat_thread_key]
        await global_data.mongo_config.save_bot_value(0, BotValueTypes.TopicMutes,
                                                      json.dumps(global_data.topic_mute))
        return False


########################################################################################################################
##########################################  handlers  ##################################################################
########################################################################################################################


@rate_limit(0, 'listen')
@router.message(F.text)  # если текст #точно не приватное, приватные выше остановились
async def cmd_last_check(message: Message, session: Session, bot: Bot, state: FSMContext):
    if message.chat.id in global_data.no_first_link:
        deleted = await check_spam(message, session)
        if deleted:
            # If the message was deleted during spam check, we stop processing
            return

    if message.chat.id in global_data.need_decode:
        await cmd_tools(message, bot, session)

    if message.chat.id in global_data.save_last_message_date:
        await save_last(message, session)

    if message.chat.id in global_data.moderate:
        await check_mute(message, session)

    if message.chat.id in global_data.notify_message:
        await notify_message(message)

    if message.chat.id in global_data.reply_only:
        await cmd_check_reply_only(message, session, bot, state)

    await check_alert(bot, message, session)

    user_id = message.sender_chat.id if message.sender_chat else message.from_user.id
    if global_data.check_user(user_id) == 0:
        await set_vote(message)  ##########

    add_bot_users(session, user_id, message.from_user.username, 1)

    if message.chat.id in global_data.listen:
        db_save_message(session=session, user_id=user_id, username=message.from_user.username,
                        thread_id=message.message_thread_id if message.is_topic_message else None,
                        text=message.text, chat_id=message.chat.id)


@router.message(ChatInOption('no_first_link'))  # точно не текс, выше остановились
async def cmd_last_check_other(message: Message, session: Session, bot: Bot):
    user_id = message.sender_chat.id if message.from_user.id == MTLChats.Channel_Bot else message.from_user.id

    if global_data.check_user(user_id) == 1:
        return False

    await delete_and_log_spam(message, session, 'not text')


########################################################################################################################
#####################################  callback_query  #################################################################
########################################################################################################################

def get_named_reply_markup(button_text):
    reply_markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=button_text,
                             callback_data="👀")]])
    return reply_markup


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
        add_bot_users(session, callback_data.user_id, None, 1)
        await query.message.edit_reply_markup(
            reply_markup=get_named_reply_markup(f"✅ Restored {query.from_user.username}"))
    else:
        add_bot_users(session, callback_data.user_id, None, 2)
        await query.answer("Banned !")
        await query.message.edit_reply_markup(
            reply_markup=get_named_reply_markup(f"✅ Banned {query.from_user.username}"))
        with suppress(TelegramBadRequest):
            await query.bot.ban_chat_member(chat_id=callback_data.chat_id, user_id=callback_data.user_id)


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
    data = global_data.first_vote_data.get(key, {"spam": 0, "good": 0, "users": [], "spam_users_mentions": [],
                                                 "good_users_mentions": []})

    if query.from_user.id in data["users"]:
        await query.answer('You have already voted.', show_alert=True)
        return False

    # Определяем вес голоса: 5 для администраторов, 1 для остальных
    vote_weight = 5 if await is_admin(query) else 1
    username_link = get_username_link(query.from_user)

    # Добавляем пользователя в общий список
    data["users"].append(query.from_user.id)

    if callback_data.spam:
        data["spam"] += vote_weight
        data["spam_users_mentions"].append(username_link)
    else:
        data["good"] += vote_weight
        data["good_users_mentions"].append(username_link)

    global_data.first_vote_data[key] = data

    # Проверяем, достиг ли счет 5 для спама
    if data["spam"] >= 5:
        # Удаляем сообщение голосования и сообщение о котором голосование
        with suppress(TelegramBadRequest):
            await bot.delete_message(query.message.chat.id, callback_data.message_id)
        with suppress(TelegramBadRequest):
            await query.message.forward(MTLChats.SpamGroup)
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
        return None

    if data["good"] >= 5:
        with suppress(TelegramBadRequest):
            await query.message.forward(MTLChats.SpamGroup)
        with suppress(TelegramBadRequest):
            await bot.delete_message(query.message.chat.id, query.message.message_id)
        await query.answer('Message marked as good.', show_alert=True)
        return None

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
    spam_list = '\n'.join(data.get("spam_users_mentions", []))
    good_list = '\n'.join(data.get("good_users_mentions", []))
    text = (
        "Please help me detect spam messages\n"
        f"\n*Spam votes ({data['spam']}):*\n{spam_list if spam_list else 'None'}"
        f"\n\n*Good votes ({data['good']}):*\n{good_list if good_list else 'None'}"
    )

    await bot.edit_message_text(chat_id=query.message.chat.id,
                                message_id=query.message.message_id,
                                text=text,
                                parse_mode="HTML",
                                reply_markup=kb_reply)
    await query.answer('Your vote has been counted.', show_alert=True)
    return None


def register_handlers(dp, bot):
    dp.include_router(router)
    logger.info('router last_handler was loaded')


register_handlers.priority = 99
