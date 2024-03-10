import re
from contextlib import suppress

import asyncio
from aiogram import F, Bot
from aiogram.enums import ChatType, ParseMode, ChatAction, MessageEntityType
from aiogram import Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.types import Message, ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, \
    URLInputFile
from sqlalchemy.orm import Session

from config_reader import config
from db.requests import db_load_bot_value, db_save_url, extract_url, db_save_message, db_load_user_id, \
    db_update_user_chat_date
from middlewares.sentry_error_handler import sentry_error_handler
from scripts.update_report import update_guarantors_report, update_main_report, update_fire, update_donate_report, \
    update_mmwb_report, update_bim_data
from skynet_start import add_bot_users
from utils import dialog
from utils.aiogram_utils import multi_reply, HasText, has_words, StartText, is_admin
from utils.dialog import talk_check_spam, add_task_to_google, generate_image
from utils.global_data import MTLChats, BotValueTypes, is_skynet_admin, global_data, update_command_info
from utils.stellar_utils import check_url_xdr, cmd_alarm_url, send_by_list
from scripts.update_data import update_lab

router = Router()
router.error()(sentry_error_handler)

my_talk_message = []


class SpamCheckCallbackData(CallbackData, prefix="SpamCheck"):
    message_id: int
    chat_id: int
    user_id: int
    good: bool
    new_message_id: int


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
        text = message.text[5:]
        image_urls = generate_image(text)

        for url in image_urls:
            image_file = URLInputFile(url, filename="image.png")
            await message.reply_photo(image_file)
    else:
        await message.reply('Только в канале фракции Киберократии')
        return False


@router.message(F.chat.id.in_(global_data.need_decode), F.text.contains('eurmtl.me/sign_tools'))
async def cmd_tools(message: Message, bot: Bot, session: Session):
    if message.text.find('eurmtl.me/sign_tools') > -1:
        msg_id = db_load_bot_value(session, message.chat.id, BotValueTypes.PinnedId)
        try:
            await bot.unpin_chat_message(message.chat.id, msg_id)
        except:
            pass
        db_save_url(session, message.chat.id, message.message_id, message.text)
        await message.pin()
        msg = await check_url_xdr(db_load_bot_value(session, message.chat.id, BotValueTypes.PinnedUrl))
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
        msg_id = db_load_bot_value(session, message.chat.id, BotValueTypes.PinnedId)
        msg = db_load_bot_value(session, message.chat.id,
                                BotValueTypes.PinnedUrl) + '\nСмотрите закреп / Look at the pinned message'
        await bot.send_message(message.chat.id, msg, reply_to_message_id=msg_id,
                               message_thread_id=message.message_thread_id)


@router.message(F.reply_to_message.from_user.id == config.bot_token.get_secret_value().split(':')[0])
async def cmd_last_check_reply_to_bot(message: Message):
    if message.reply_to_message \
            and (f'{message.reply_to_message.message_id}*{message.chat.id}' in my_talk_message):
        # answer on bot message
        msg = await dialog.talk(message.chat.id, message.text)
        msg = await message.reply(msg)
        my_talk_message.append(f'{msg.message_id}*{msg.chat.id}')


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
            db_load_bot_value(session, message.chat.id, BotValueTypes.PinnedUrl))
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


@router.message(F.chat.type == ChatType.PRIVATE)
@router.message(StartText(('SKYNET', 'СКАЙНЕТ', 'SKYNET4', 'СКАЙНЕТ4')))
@router.message(Command(commands=["skynet"]))
async def cmd_last_check_p(message: Message, session: Session, bot: Bot):
    gpt4 = False
    if message.text[7] == '4':
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
    msg = await message.reply(msg)
    if message.chat.type != ChatType.PRIVATE:
        # на случай вызова из /skynet
        my_talk_message.append(f'{msg.message_id}*{msg.chat.id}')


@router.message(F.chat.id.in_(global_data.reply_only), F.text)
async def cmd_check_reply_only(message: Message, session: Session, bot: Bot):
    if message.chat.id in global_data.save_last_message_date:
        await save_last(message, session)

    has_hashtag = False
    if message.entities:
        for entity in message.entities:
            if entity.type == MessageEntityType.HASHTAG:
                has_hashtag = True
                break

    if message.reply_to_message or message.forward_from_chat or has_hashtag:
        db_save_message(session=session, user_id=message.from_user.id, username=message.from_user.username,
                        thread_id=message.message_thread_id if message.is_topic_message else None,
                        text=message.text, chat_id=message.chat.id)
    else:
        msg = await message.reply(
            'Осуждаю ! Это сообщения не увидят в комментариях. Я удалю сообщение через 15 секунд ! '
            'Рекомендую повторить его с использованием функции «ответ» на нужное сообщение. \n'
            'Ещё проще, если переписываться из комментариев к исходному посту в канале.')

        await asyncio.sleep(15)
        try:
            await message.forward(chat_id=message.from_user.id)
            await bot.send_message(chat_id=message.chat.id, text='Сообщение переслано в личку')
        except TelegramBadRequest:
            await bot.send_message(chat_id=message.chat.id, text='Сообщение удалено')
        with suppress(TelegramBadRequest):
            await message.delete()
            await msg.delete()


@router.message(F.chat.id.in_(global_data.listen), F.text)
async def cmd_save_msg(message: Message, session: Session):
    if message.chat.id in global_data.save_last_message_date:
        await save_last(message, session)

    db_save_message(session=session, user_id=message.from_user.id, username=message.from_user.username,
                    thread_id=message.message_thread_id if message.is_topic_message else None,
                    text=message.text, chat_id=message.chat.id)


@router.message(~F.entities, F.text)  # если текст без ссылок #точно не приватное, приватные выше остановились
async def cmd_save_good_user(message: Message, session: Session):
    if message.chat.id in global_data.save_last_message_date:
        await save_last(message, session)

    add_bot_users(session, message.from_user.id, message.from_user.username, 1)
    # [MessageEntity(type='url', offset=33, length=5, url=None, user=None, language=None, custom_emoji_id=None), MessageEntity(type='text_link', offset=41, length=4, url='http://xbet.org/', user=None, language=None, custom_emoji_id=None), MessageEntity(type='mention', offset=48, length=8, url=None, user=None, language=None, custom_emoji_id=None)]


def is_mixed_word(word):
    # Проверяем наличие русских букв
    contains_cyrillic = bool(re.search('[а-яА-Я]', word))
    # Проверяем наличие цифр
    contains_digit = bool(re.search('[0-9@]', word))
    # Проверяем наличие латинских букв
    contains_latin = bool(re.search('[a-zA-Z]', word))

    # Считаем слово "смешанным", если оно содержит русские буквы и (цифры или латинские буквы)
    return contains_cyrillic and (contains_digit or contains_latin)


spam_phrases = [
    "команду",
    "команда",
    "доход",
    "без опыта",
    "лс",
    "прибыль",
    "проект",
    "предложение",
    "тестирование",
    "день",
]


def contains_spam_phrases(text, phrases=None, threshold=3):
    if phrases is None:
        phrases = spam_phrases
    text = text.lower().split()
    count = sum(phrase in text for phrase in phrases)
    return count >= threshold


@router.message(F.entities, F.text)  # если текст с link # точно не приватное, приватные выше остановились
async def cmd_no_first_link(message: Message, session: Session, bot: Bot):
    await check_alert(bot, message, session)

    if message.chat.id in global_data.no_first_link:
        await check_spam(message, session)

    if message.chat.id in global_data.save_last_message_date:
        await save_last(message, session)


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


async def check_alert(bot, message, session):
    # if user need be alert
    if message.chat.id in global_data.alert_me:
        for entity in message.entities:
            if entity.type == 'mention':
                username = entity.extract_from(message.text)
                user_id = db_load_user_id(session, username[1:])
                if user_id > 0 and user_id in global_data.alert_me[message.chat.id]:
                    with suppress(TelegramBadRequest, TelegramForbiddenError):
                        alert_username = '@' + message.from_user.username if message.from_user.username else message.from_user.full_name
                        await bot.send_message(user_id, f'Вас упомянул {alert_username}\n'
                                                        f'В чате {message.chat.title}\n'
                                                        f'Ссылка на сообщение {message.get_url()}')


async def save_last(message, session):
    if message.chat.id in global_data.save_last_message_date:
        db_update_user_chat_date(session, message.from_user.id, message.chat.id)


@router.callback_query(SpamCheckCallbackData.filter())
async def cq_spam_check(query: CallbackQuery, callback_data: SpamCheckCallbackData, bot: Bot, session: Session):
    if not await is_admin(query.message):
        await query.answer('You are not admin.', show_alert=True)
        return False

    if callback_data.good:
        chat = await bot.get_chat(callback_data.chat_id)
        await bot.forward_message(callback_data.chat_id, query.message.chat.id, callback_data.new_message_id)
        await bot.restrict_chat_member(chat_id=callback_data.chat_id, user_id=callback_data.user_id,
                                       permissions=chat.permissions)
        await query.answer("Oops, bringing the message back!", show_alert=True)
    else:
        await query.answer("Сорьки, пока не умею !", show_alert=True)


if __name__ == '__main__':
    test = '''
Вcex пpивeтcтвyю!
Ищём тecтирoвщикa сeти.
Дoxoд cocтaвляeт 220$/дeнь.
Зapaбoтoк зaймeт нe бoлee 1 чaca eжeднeвнo.
Ищeм 3-4 чeлoвeкa для кoмaнды.
Вoзрaст oт 20 лeт, трeбyeтся знaниe pyssкoго языка. 
Пиши + в ЛС
'''

    print(contains_spam_phrases(test))

    mixed_count = sum(is_mixed_word(word) for word in test.split())
    print(mixed_count)
