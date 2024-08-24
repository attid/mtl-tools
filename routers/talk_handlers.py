import asyncio
import html
import re
from contextlib import suppress

from aiogram import F, Bot, Router
from aiogram.enums import ChatType, ParseMode, ChatAction, MessageEntityType
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.types import (Message, ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery,
                           URLInputFile, ReplyParameters)
from loguru import logger
from sqlalchemy.orm import Session

from db.requests import extract_url, db_save_message, db_get_user_id, db_update_user_chat_date
from middlewares.throttling import rate_limit
from scripts.update_data import update_lab
from scripts.update_report import (update_guarantors_report, update_main_report, update_fire, update_donate_report,
                                   update_mmwb_report, update_bim_data)
from skynet_start import add_bot_users
from utils import dialog
from utils.aiogram_utils import (multi_reply, HasText, has_words, StartText, is_admin, ReplyToBot, ChatInOption,
                                 get_username_link, cmd_sleep_and_delete)
from utils.dialog import talk_check_spam, add_task_to_google, generate_image
from utils.global_data import MTLChats, BotValueTypes, is_skynet_admin, global_data, update_command_info
from utils.pyro_tools import extract_telegram_info, pyro_update_msg_info, MessageInfo
from utils.spam_cheker import is_mixed_word, contains_spam_phrases
from utils.stellar_utils import check_url_xdr, cmd_alarm_url, send_by_list
from utils.telegraph_tools import telegraph

router = Router()

my_talk_message = []


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


# @router.message(F.chat == MTLChats.Employment)
async def cmd_employment(message: Message, bot: Bot):
    spam_persent = await talk_check_spam(message.text)
    if spam_persent > 69:
        await message.forward(chat_id=MTLChats.TestGroup)
        await bot.send_message(chat_id=MTLChats.TestGroup, text=f'Спам {spam_persent}% set RO')
        await message.chat.restrict(message.from_user.id, permissions=ChatPermissions(can_send_messages=False,
                                                                                      can_send_media_messages=False,
                                                                                      can_send_other_messages=False))
        await message.delete()
    elif spam_persent > 50:
        await message.forward(chat_id=MTLChats.TestGroup)
        await bot.send_message(chat_id=MTLChats.TestGroup, text=f'Спам {spam_persent}% check please')


@router.message(Command(commands=["img"]))
async def cmd_img(message: Message, bot: Bot):
    if message.chat.id in (MTLChats.CyberGroup,) or f'@{message.from_user.username.lower()}' in global_data.skynet_img:
        await bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_PHOTO)
        await bot.send_message(chat_id=MTLChats.ITolstov, text=f'{message.from_user.username}:{message.text}')
        text = message.text[5:]
        image_urls = await generate_image(text)

        for url in image_urls:
            image_file = URLInputFile(url, filename="image.png")
            await message.reply_photo(image_file)
    else:
        await message.reply('Только в канале фракции Киберократии')
        return False


async def save_url(chat_id, msg_id, msg):
    url = extract_url(msg)
    await global_data.mongo_config.save_bot_value(chat_id, BotValueTypes.PinnedUrl, url)
    await global_data.mongo_config.save_bot_value(chat_id, BotValueTypes.PinnedId, msg_id)


@router.message(ChatInOption('need_decode'), F.text.contains('eurmtl.me/sign_tools'))
async def cmd_tools(message: Message, bot: Bot, session: Session):
    await check_alert(bot, message, session)
    if message.text.find('eurmtl.me/sign_tools') > -1:
        msg_id = await global_data.mongo_config.load_bot_value(message.chat.id, BotValueTypes.PinnedId)
        try:
            await bot.unpin_chat_message(message.chat.id, msg_id)
        except:
            pass
        await save_url(message.chat.id, message.message_id, message.text)
        await message.pin()
        msg = await check_url_xdr(
            await global_data.mongo_config.load_bot_value(message.chat.id, BotValueTypes.PinnedUrl))
        msg = f'\n'.join(msg)
        await multi_reply(message, msg)


@router.message(Command(commands=["comment"]))
async def cmd_comment(message: Message):
    if message.reply_to_message is None:
        await message.reply('А чего комментировать то?')
        return
    if message.reply_to_message.text:
        msg = message.reply_to_message.text
    else:
        msg = message.reply_to_message.caption
    try:
        await message.delete()
    except:
        pass
    msg = await dialog.talk_get_comment(message.chat.id, msg)
    msg = await message.reply_to_message.reply(msg)
    my_talk_message.append(f'{msg.message_id}*{msg.chat.id}')


async def remind(message: Message, session: Session, bot: Bot):
    if message.reply_to_message and message.reply_to_message.forward_from_chat:
        alarm_list = cmd_alarm_url(extract_url(message.reply_to_message.text))
        msg = alarm_list + '\nСмотрите топик / Look at the topic message'
        await message.reply(text=msg)
        if alarm_list.find('@') != -1:
            if is_skynet_admin(message):
                all_users = alarm_list.split()
                url = f'https://t.me/c/1649743884/{message.reply_to_message.forward_from_message_id}'
                await send_by_list(bot=bot, all_users=all_users, message=message, url=url, session=session)

    else:
        msg_id = await global_data.mongo_config.load_bot_value(message.chat.id, BotValueTypes.PinnedId)
        msg = await global_data.mongo_config.load_bot_value(message.chat.id,
                                                            BotValueTypes.PinnedUrl) + '\nСмотрите закреп / Look at the pinned message'
        await bot.send_message(message.chat.id, msg, reply_to_message_id=msg_id,
                               message_thread_id=message.message_thread_id)


@router.message(F.text, F.reply_to_message, ReplyToBot(), F.chat.type != ChatType.PRIVATE)
async def cmd_last_check_reply_to_bot(message: Message):
    if f'{message.reply_to_message.message_id}*{message.chat.id}' in my_talk_message:
        # answer on bot message
        msg_text = await dialog.talk(message.chat.id, message.text)
        try:
            msg = await message.reply(msg_text, parse_mode=ParseMode.MARKDOWN)
        except:
            msg = await message.reply(msg_text)
        my_talk_message.append(f'{msg.message_id}*{msg.chat.id}')

    await answer_notify_message(message)


@router.message(StartText(('SKYNET', 'СКАЙНЕТ')),
                HasText(('УБИТЬ', 'убей', 'kill')))
async def cmd_last_check_nap(message: Message):
    await message.answer('Нельзя убивать. NAP NAP NAP')


@router.message(StartText(('SKYNET', 'СКАЙНЕТ')),
                HasText(('ДЕКОДИРУЙ', 'decode')))
async def cmd_last_check_decode(message: Message, session: Session, bot: Bot):
    if message.reply_to_message:
        if message.reply_to_message.text.find('eurmtl.me/sign_tools') > -1:
            msg = await check_url_xdr(extract_url(message.reply_to_message.text))
            msg = f'\n'.join(msg)
            await multi_reply(message, msg)
        else:
            await message.reply('Ссылка не найдена')
    else:
        msg = await check_url_xdr(
            await global_data.mongo_config.load_bot_value(message.chat.id, BotValueTypes.PinnedUrl))
        msg = f'\n'.join(msg)
        await multi_reply(message, msg[:4000])


@update_command_info("Скайнет напомни", "Попросить Скайнет напомнить про подпись транзакции. Только в рабочем чате.")
@router.message(StartText(('SKYNET', 'СКАЙНЕТ')),
                HasText(('НАПОМНИ',)))
async def cmd_last_check_remind(message: Message, session: Session, bot: Bot):
    await remind(message, session, bot)


@router.message(StartText(('SKYNET', 'СКАЙНЕТ')),
                HasText(('задач',)))
async def cmd_last_check_task(message: Message, session: Session, bot: Bot):
    tmp_msg = await message.reply('Анализирую задачу...')
    msg = ''
    if message.reply_to_message:
        msg += (f'сообщение от: {message.reply_to_message.from_user.username} \n'
                f'ссылка: {message.reply_to_message.get_url()}\n')
        msg += f'текст: """{message.reply_to_message.text}"""\n\n\n'

    msg += f'сообщение от: {message.from_user.username} \n'
    msg += f'ссылка: {message.get_url()}\n'
    msg += f'текст: """{message.text[7:]}"""\n\n\n'

    print(msg)
    msg = await add_task_to_google(msg)
    await message.reply(msg)
    await tmp_msg.delete()


@router.message(StartText(('SKYNET', 'СКАЙНЕТ')),
                HasText(('гороскоп',)))
async def cmd_last_check_horoscope(message: Message, session: Session, bot: Bot):
    await message.answer('\n'.join(dialog.get_horoscope()), parse_mode=ParseMode.MARKDOWN)


@update_command_info("Скайнет обнови отчёт", "Попросить Скайнет обновить файл отчета. Только в рабочем чате.")
@update_command_info("Скайнет обнови гарантов", "Попросить Скайнет обновить файл гарантов. Только в рабочем чате.")
@router.message(StartText(('SKYNET', 'СКАЙНЕТ')),
                HasText(('ОБНОВИ',)))
async def cmd_last_check_update(message: Message, session: Session, bot: Bot):
    if not is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return False
    if has_words(message.text, ['MM', 'ММ']):
        msg = await message.reply('Зай, я запустила обновление')
        await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        await update_mmwb_report(session)
        await msg.reply('Обновление завершено')
    if has_words(message.text, ['БДМ', 'BIM']):
        msg = await message.reply('Зай, я запустила обновление')
        await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        await update_bim_data(session)
        await msg.reply('Обновление завершено')
    if has_words(message.text, ['ГАРАНТОВ']):
        msg = await message.reply('Зай, я запустила обновление')
        await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        await update_guarantors_report()
        await msg.reply('Обновление завершено')
    if has_words(message.text, ['ОТЧЕТ', 'отчёт', 'report']):
        msg = await message.reply('Зай, я запустила обновление')
        await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        await update_main_report(session)
        await update_fire(session)
        await msg.reply('Обновление завершено')
    if has_words(message.text, ['donate', 'donates', 'donated']):
        msg = await message.reply('Зай, я запустила обновление')
        await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        await update_donate_report(session)
        await msg.reply('Обновление завершено')
    if has_words(message.text, ['лабу', 'тулзу']):
        msg = await message.reply('Зай, я запустила обновление')
        await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        await update_lab()
        await msg.reply('Обновление завершено')


@rate_limit(5, 'private_links')
@router.message(F.chat.type == ChatType.PRIVATE, F.entities)
async def handle_private_message_links(message: Message, bot: Bot):
    telegram_links = []
    buttons = []

    for entity in message.entities:
        if entity.type in ['url', 'text_link']:
            url = entity.url if entity.type == 'text_link' else entity.extract_from(message.text)
            if 't.me/' in url:
                msg_info = extract_telegram_info(url)
                if msg_info:
                    try:
                        chat = await bot.get_chat(msg_info.chat_id)
                        telegram_links.append(f"{url} Группа \"{chat.title}\"")

                        chat_member = await bot.get_chat_member(msg_info.chat_id, message.from_user.id)
                        if chat_member and chat_member.status not in ['left', 'kicked']:
                            await pyro_update_msg_info(msg_info)
                            if msg_info.thread_name:
                                thread_link = '/'.join(url.split('/')[:-1])
                                telegram_links.append(
                                    f"Топик <a href=\"{thread_link}\"> \"{msg_info.thread_name}\"</a>")

                            if msg_info.message_text:
                                telegraph_link = await telegraph.create_uuid_page(msg_info)
                                buttons.append([InlineKeyboardButton(text=f'ПП {msg_info.chat_name[:30]}',
                                                                     url=telegraph_link.url)])
                    except TelegramBadRequest as e:
                        logger.error(f"Ошибка TelegramBadRequest при обработке {url}: {e}")
                        telegram_links.append(f"{url} группа \"не определена\"")
                    except Exception as e:
                        logger.error(f"Неожиданная ошибка при обработке {url}: {e}")

                    telegram_links.append(" ")

    if telegram_links:
        response = "Найдены ссылки:\n" + "\n".join(telegram_links)
        if buttons:
            response += "\n\n предпросмотр сообщений : "
        await message.reply(response, disable_web_page_preview=True,
                            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None)


@router.message(F.chat.type == ChatType.PRIVATE, F.text)
@router.message(StartText(('SKYNET', 'СКАЙНЕТ', 'SKYNET4', 'СКАЙНЕТ4')), F.text)
@router.message(Command(commands=["skynet"]))
async def cmd_last_check_p(message: Message, session: Session, bot: Bot):
    gpt4 = False
    if len(message.text) > 7 and message.text[7] == '4':
        if message.chat.id != MTLChats.CyberGroup:
            await message.reply('Только в канале фракции Киберократии')
            return False
        gpt4 = True

    msg = message.text
    if message.reply_to_message and message.reply_to_message.text:
        msg = f"{message.reply_to_message.text} \n================\n{message.text}"

    msg = await dialog.talk(message.chat.id, msg, gpt4)
    if msg is None:
        msg = '=( connection error, retry again )='
    try:
        msg = await message.reply(msg, parse_mode=ParseMode.MARKDOWN)
    except:
        msg = await message.reply(msg)
    if message.chat.type != ChatType.PRIVATE:
        # на случай вызова из /skynet
        my_talk_message.append(f'{msg.message_id}*{msg.chat.id}')


@router.message(ChatInOption('reply_only'), F.text)
async def cmd_check_reply_only(message: Message, session: Session, bot: Bot):
    if message.chat.id in global_data.save_last_message_date:
        await save_last(message, session)

    await check_alert(bot, message, session)

    if message.from_user.id in global_data.users_list and global_data.users_list[message.from_user.id] != 1:
        await set_vote(message)

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


@rate_limit(0, 'listen')
@router.message(ChatInOption('listen'), F.text)
async def cmd_save_msg(message: Message, session: Session, bot: Bot):
    if message.chat.id in global_data.save_last_message_date:
        await save_last(message, session)

    await check_alert(bot, message, session)

    if message.from_user.id in global_data.users_list and global_data.users_list[message.from_user.id] != 1:
        await set_vote(message)

    db_save_message(session=session, user_id=message.from_user.id, username=message.from_user.username,
                    thread_id=message.message_thread_id if message.is_topic_message else None,
                    text=message.text, chat_id=message.chat.id)

    await notify_message(message)


@rate_limit(0, 'listen')
@router.message(~F.entities, F.text)  # если текст без ссылок #точно не приватное, приватные выше остановились
async def cmd_save_good_user(message: Message, session: Session):
    if message.chat.id in global_data.save_last_message_date:
        await save_last(message, session)

    if message.from_user.id in global_data.users_list and global_data.users_list[message.from_user.id] != 1:
        await set_vote(message)
    add_bot_users(session, message.from_user.id, message.from_user.username, 1)

    # [MessageEntity(type='url', offset=33, length=5, url=None, user=None, language=None, custom_emoji_id=None), MessageEntity(type='text_link', offset=41, length=4, url='http://xbet.org/', user=None, language=None, custom_emoji_id=None), MessageEntity(type='mention', offset=48, length=8, url=None, user=None, language=None, custom_emoji_id=None)]
    await notify_message(message)






@rate_limit(0, 'listen')
@router.message(F.entities, F.text)  # если текст с link # точно не приватное, приватные выше остановились
async def cmd_no_first_link(message: Message, session: Session, bot: Bot):
    await check_alert(bot, message, session)

    if message.chat.id in global_data.no_first_link:
        await check_spam(message, session)

    if message.chat.id in global_data.save_last_message_date:
        await save_last(message, session)

    if message.chat.id in global_data.notify_message:
        await notify_message(message)


@rate_limit(0, 'listen')
@router.message(ChatInOption('notify_message'))
async def cmd_notify_msg(message: Message):
    await notify_message(message)


async def check_spam(message, session):
    if message.from_user.id in global_data.users_list and global_data.users_list[message.from_user.id] == 1:
        return

    custom_emoji_count = 0
    process_message = False
    for entity in message.entities:
        if entity.type in ('url', 'text_link', 'mention'):
            process_message = True
            break  # Прерываем цикл, так как нашли ссылку или упоминание
        elif entity.type == 'custom_emoji':
            custom_emoji_count += 1

    if custom_emoji_count > 3:
        process_message = True

    words = message.text.split()
    mixed_word_count = sum(is_mixed_word(word) for word in words)
    if mixed_word_count >= 3:
        process_message = True

    if contains_spam_phrases(message.text):
        process_message = True

    if process_message:
        await message.chat.restrict(message.from_user.id,
                                    permissions=ChatPermissions(can_send_messages=False,
                                                                can_send_media_messages=False,
                                                                can_send_other_messages=False))
        msg = await message.forward(MTLChats.SpamGroup)
        chat_link = f'@{message.chat.username}' if message.chat.username else message.chat.invite_link
        await msg.reply(f'Сообщение из чата {message.chat.title} {chat_link}',
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
    else:
        add_bot_users(session, message.from_user.id, message.from_user.username, 1)
        await set_vote(message)


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


async def answer_notify_message(message: Message):
    if (message.reply_to_message.from_user.id == message.bot.id
            and message.reply_to_message.reply_markup
            and message.reply_to_message.external_reply
            and message.reply_to_message.external_reply.chat.id in global_data.notify_message):
        info = message.reply_to_message.reply_markup.inline_keyboard[0][0].callback_data.split(':')
        # "Reply:96:-1002175508678" msg_id:chat_id
        if len(info) > 2 and info[0] == 'Reply':
            msg = await message.copy_to(chat_id=int(info[2]), reply_to_message_id=int(info[1]))
            if message.chat.username:
                await message.bot.send_message(
                    chat_id=int(info[2]),
                    text=f'Ответ из чата @{message.chat.username}',
                    reply_to_message_id=msg.message_id
                )


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
async def cq_first_vote_check(query: CallbackQuery, callback_data: FirstMessageCallbackData, bot: Bot, session: Session):
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
                callback_data=FirstMessageCallbackData(spam=True, message_id=callback_data.message_id, user_id=callback_data.user_id).pack()
            ),
            InlineKeyboardButton(
                text=f"Good ({data['good']})",
                callback_data=FirstMessageCallbackData(spam=False, message_id=callback_data.message_id, user_id=callback_data.user_id).pack()
            )
        ]])

        # Редактируем сообщение с новыми кнопками
        await bot.edit_message_reply_markup(chat_id=query.message.chat.id, message_id=query.message.message_id, reply_markup=kb_reply)
        await query.answer('Your vote has been counted.', show_alert=True)



