from aiogram import types, F, Bot
import re, random

from aiogram.enums import ChatType, ParseMode, ChatAction
from loguru import logger
from aiogram import Router
from aiogram.filters import Command, Text
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ChatPermissions
from sqlalchemy.orm import Session

from db.requests import db_load_bot_value, db_save_url, extract_url, db_save_message
from scripts.update_report import update_guarantors_report, update_main_report, update_fire, update_donate_report, \
    update_mmwb_report, update_bim_data
from utils import dialog
from utils.aiogram_utils import multi_reply, HasText, has_words
from utils.dialog import talk_check_spam, add_task_to_google
from utils.global_data import MTLChats, BotValueTypes, is_skynet_admin, global_data
from utils.stellar_utils import check_url_xdr, cmd_alarm_url, send_by_list
from scripts.update_data import update_lab

router = Router()

my_talk_message = []


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


@router.message(Text(contains='eurmtl.me/sign_tools'))
async def cmd_tools(message: Message, bot: Bot, session: Session):
    if message.text.find('eurmtl.me/sign_tools') > -1:
        msg_id = db_load_bot_value(session, message.chat.id, BotValueTypes.PinnedId)
        try:
            await bot.unpin_chat_message(message.chat.id, msg_id)
        except:
            pass
        db_save_url(session, message.chat.id, message.message_id, message.text)
        await message.pin()
        if message.chat.id in (MTLChats.SignGroup, MTLChats.TestGroup, MTLChats.ShareholderGroup,
                               MTLChats.DefiGroup, MTLChats.LandLordGroup,
                               MTLChats.SignGroupForChanel):
            msg = check_url_xdr(
                db_load_bot_value(session, message.chat.id, BotValueTypes.PinnedUrl))
            msg = f'\n'.join(msg)
            await multi_reply(message, msg)

        # if message.chat.id in (MTLChats.SignGroup, MTLChats.SignGroupForChanel,):
        #    msg = db_load_bot_value(session, message.chat.id,
        #                             BotValueTypes.PinnedUrl) + '\nСмотрите закреп / Look at the pinned message'
        #    await message.reply(msg)


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


@router.message(F.reply_to_message.from_user.id == 2134695152)
async def cmd_last_check1(message: Message, session: Session, bot: Bot):
    if message.reply_to_message \
            and (f'{message.reply_to_message.message_id}*{message.chat.id}' in my_talk_message):
        # answer on bot message
        msg = await dialog.talk(message.chat.id, message.text)
        msg = await message.reply(msg)
        my_talk_message.append(f'{msg.message_id}*{msg.chat.id}')


@router.message(Text(startswith=('SKYNET', 'СКАЙНЕТ'), ignore_case=True),
                HasText(('УБИТЬ', 'убей', 'kill')))
async def cmd_last_check_nap(message: Message):
    await message.answer('Нельзя убивать. NAP NAP NAP')


@router.message(Text(startswith=('SKYNET', 'СКАЙНЕТ'), ignore_case=True),
                HasText(('ДЕКОДИРУЙ', 'decode')))
async def cmd_last_check_decode(message: Message, session: Session, bot: Bot):
    if message.reply_to_message:
        if message.reply_to_message.text.find('eurmtl.me/sign_tools') > -1:
            msg = check_url_xdr(extract_url(message.reply_to_message.text))
            msg = f'\n'.join(msg)
            await multi_reply(message, msg)
        else:
            await message.reply('Ссылка не найдена')
    else:
        msg = check_url_xdr(
            db_load_bot_value(session, message.chat.id, BotValueTypes.PinnedUrl))
        msg = f'\n'.join(msg)
        await multi_reply(message, msg[:4000])


@router.message(Text(startswith=('SKYNET', 'СКАЙНЕТ'), ignore_case=True),
                Text(contains=('НАПОМНИ',), ignore_case=True))
async def cmd_last_check_remind(message: Message, session: Session, bot: Bot):
    await remind(message, session, bot)


@router.message(Text(startswith=('SKYNET', 'СКАЙНЕТ'), ignore_case=True),
                Text(contains=('задач',), ignore_case=True))
async def cmd_last_check_task(message: Message, session: Session, bot: Bot):
    msg = message.text
    msg += f'\nсообщение от {message.from_user.username} ссылка на это сообщение {message.get_url()}'
    if message.reply_to_message:
        msg += f'\n\nсообщение отправлено в ответ на """{message.reply_to_message.text}"""'
        msg += f'\nсообщение от {message.reply_to_message.from_user.username} ссылка на это сообщение {message.reply_to_message.get_url()}'

    msg = await add_task_to_google(msg)
    await message.reply(msg)


@router.message(Text(startswith=('SKYNET', 'СКАЙНЕТ'), ignore_case=True),
                Text(contains=('гороскоп',), ignore_case=True))
async def cmd_last_check_horoscope(message: Message, session: Session, bot: Bot):
    await message.answer('\n'.join(dialog.get_horoscope()), parse_mode=ParseMode.MARKDOWN)


@router.message(Text(startswith=('SKYNET', 'СКАЙНЕТ'), ignore_case=True),
                Text(contains=('ОБНОВИ',), ignore_case=True))
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
@router.message(Text(startswith=('SKYNET', 'СКАЙНЕТ'), ignore_case=True))
@router.message(Command(commands=["skynet"]))
async def cmd_last_check_p(message: Message, session: Session, bot: Bot):
    msg = await dialog.talk(message.chat.id, message.text)
    msg = await message.reply(msg)
    if message.chat.type != ChatType.PRIVATE:
        # на случай вызова из /skynet
        my_talk_message.append(f'{msg.message_id}*{msg.chat.id}')


@router.message(F.chat.id.in_(global_data.reply_only), F.text)
async def cmd_check_reply_only(message: Message, session: Session):
    if message.reply_to_message or message.forward_from_chat:
        db_save_message(session=session, user_id=message.from_user.id, username=message.from_user.username,
                        thread_id=message.message_thread_id if message.is_topic_message else None,
                        text=message.text, chat_id=message.chat.id)
    else:
        await message.reply('Осуждаю ! Это сообщения не увидят в комментариях. Я удалю сообщение через 5 минут ! '
                            'Рекомендую удалить его, и повторить его с использованием функции «ответ». \n'
                            'Ещё проще, если переписываться из комментариев к исходному посту в канале.')
        return


@router.message(F.chat.id.in_(global_data.listen), F.text)
async def cmd_save_msg(message: Message, session: Session):
    db_save_message(session=session, user_id=message.from_user.id, username=message.from_user.username,
                    thread_id=message.message_thread_id if message.is_topic_message else None,
                    text=message.text, chat_id=message.chat.id)
