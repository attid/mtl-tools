from aiogram import types, F, Bot
import re, random

from aiogram.enums import ChatType, ParseMode
from loguru import logger
from aiogram import Router
from aiogram.filters import Command, Text
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ChatPermissions
from sqlalchemy.orm import Session

from db.requests import cmd_load_bot_value, cmd_save_url, extract_url
from scripts.update_report import update_guarantors_report, update_main_report, update_fire, update_donate_report, \
    update_mmwb_report
from utils import dialog
from utils.aiogram_utils import multi_reply
from utils.dialog import talk_check_spam, add_task_to_google
from utils.global_data import MTLChats, BotValueTypes, is_skynet_admin, global_data
from utils.stellar_utils import check_url_xdr, cmd_alarm_url, send_by_list

router = Router()


def has_words(master, words_array):
    for word in words_array:
        if master.upper().find(word.upper()) > -1:
            return True
    return False


my_talk_message = []


@router.message(Command(commands=["skynet"]))
async def cmd_skynet(message: Message):
    await cmd_last_check(message)


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
        msg_id = cmd_load_bot_value(session, message.chat.id, BotValueTypes.PinnedId)
        try:
            await bot.unpin_chat_message(message.chat.id, msg_id)
        except:
            pass
        cmd_save_url(session, message.chat.id, message.message_id, message.text)
        await message.pin()
        if message.chat.id in (MTLChats.SignGroup, MTLChats.TestGroup, MTLChats.ShareholderGroup,
                               MTLChats.DefiGroup, MTLChats.LandLordGroup,
                               MTLChats.SignGroupForChanel):
            msg = check_url_xdr(
                cmd_load_bot_value(session, message.chat.id, BotValueTypes.PinnedUrl))
            msg = f'\n'.join(msg)
            await multi_reply(message, msg)

        if message.chat.id in (MTLChats.SignGroup, MTLChats.SignGroupForChanel,):
            msg = cmd_load_bot_value(session, message.chat.id,
                                     BotValueTypes.PinnedUrl) + '\nСмотрите закреп / Look at the pinned message'
            await message.reply(msg)


@router.message(F.chat.id.in_(global_data.reply_only))
async def cmd_check_reply_only(message: Message):
    if message.reply_to_message or message.forward_from_chat:
        pass
    else:
        await message.reply('Осуждаю ! Это сообщения не увидят в комментариях. Я удалю сообщение через 5 минут ! '
                            'Рекомендую удалить его, и повторить его с использованием функции «ответ». \n'
                            'Ещё проще, если переписываться из комментариев к исходному посту в канале.')
        return


@router.message(F.text)
async def cmd_last_check(message: Message, session: Session, bot: Bot):
    if message.text.upper()[:6] in ('SKYNET', 'СКАЙНЕ',):
        if has_words(message.text, ['УБИТЬ', 'убей', 'kill']):
            await message.answer('Нельзя убивать. NAP NAP NAP')

        elif has_words(message.text, ['ДЕКОДИРУЙ', 'decode']):
            if message.reply_to_message:
                if message.reply_to_message.text.find('eurmtl.me/sign_tools') > -1:
                    msg = check_url_xdr(extract_url(message.reply_to_message.text))
                    msg = f'\n'.join(msg)
                    await multi_reply(message, msg)
                else:
                    await message.reply('Ссылка не найдена')
            else:
                msg = check_url_xdr(
                    cmd_load_bot_value(session, message.chat.id, BotValueTypes.PinnedUrl))
                msg = f'\n'.join(msg)
                await multi_reply(message, msg[:4000])

        elif has_words(message.text, ['НАПОМНИ', 'remind']):
            await remind(message, session, bot)

        elif has_words(message.text, ['задача', 'задачу']):
            msg = message.text
            msg += f'\nсообщение от {message.from_user.username} ссылка на это сообщение {message.get_url()}'
            if message.reply_to_message:
                msg += f'\n\nсообщение отправлено в ответ на """{message.reply_to_message.text}"""'
                msg += f'\nсообщение от {message.reply_to_message.from_user.username} ссылка на это сообщение {message.reply_to_message.get_url()}'

            msg = await add_task_to_google(msg)
            await message.reply(msg)

        elif has_words(message.text, ['ОБНОВИ', 'update']):
            if not is_skynet_admin(message):
                await message.reply('You are not my admin.')
                return False
            if has_words(message.text, ['MM', 'ММ']):
                msg = await message.reply('Зай, я запустила обновление')
                await update_mmwb_report(session)
                await msg.reply('Обновление завершено')
            if has_words(message.text, ['ГАРАНТОВ']):
                msg = await message.reply('Зай, я запустила обновление')
                await update_guarantors_report()
                await msg.reply('Обновление завершено')
            if has_words(message.text, ['ОТЧЕТ', 'отчёт', 'report']):
                msg = await message.reply('Зай, я запустила обновление')
                await update_main_report()
                await update_fire()
                await msg.reply('Обновление завершено')
            if has_words(message.text, ['donate', 'donates', 'donated']):
                msg = await message.reply('Зай, я запустила обновление')
                await update_donate_report(session)
                await msg.reply('Обновление завершено')

        elif has_words(message.text, ['гороскоп']):
            await message.answer('\n'.join(dialog.get_horoscope()), parse_mode=ParseMode.MARKDOWN)

        # elif has_words(message.text, ['кто молчит', 'найди молчунов', 'найди безбилетника']):
        #     await skynet_poll_handlers.cmd_poll_check(message)

        else:
            msg = await dialog.talk(message.chat.id, message.text)
            msg = await message.reply(msg)
            my_talk_message.append(f'{msg.message_id}*{msg.chat.id}')

    elif message.chat.type == ChatType.PRIVATE:
        msg = await dialog.talk(message.chat.id, message.text)
        await message.reply(msg)

    else:
        if message.reply_to_message and (message.reply_to_message.from_user.id == 2134695152) \
                and (f'{message.reply_to_message.message_id}*{message.chat.id}' in my_talk_message):
            # answer on bot message
            msg = await dialog.talk(message.chat.id, message.text)
            msg = await message.reply(msg)
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
        msg_id = cmd_load_bot_value(session, message.chat.id, BotValueTypes.PinnedId)
        msg = cmd_load_bot_value(session, message.chat.id,
                                 BotValueTypes.PinnedUrl) + '\nСмотрите закреп / Look at the pinned message'
        await bot.send_message(message.chat.id, msg, reply_to_message_id=msg_id,
                               message_thread_id=message.message_thread_id)


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
