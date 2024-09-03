from aiogram import F, Bot, Router
from aiogram.enums import ChatType, ParseMode, ChatAction
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import (Message, InlineKeyboardMarkup, InlineKeyboardButton, URLInputFile)
from loguru import logger
from sqlalchemy.orm import Session

from db.requests import extract_url
from middlewares.throttling import rate_limit
from scripts.update_data import update_lab
from scripts.update_report import (update_guarantors_report, update_main_report, update_fire, update_donate_report,
                                   update_mmwb_report, update_bim_data)
from utils import dialog
from utils.aiogram_utils import (multi_reply, HasText, has_words, StartText, ReplyToBot)
from utils.dialog import add_task_to_google, generate_image
from utils.global_data import MTLChats, BotValueTypes, is_skynet_admin, global_data, update_command_info
from utils.pyro_tools import extract_telegram_info, pyro_update_msg_info
from utils.stellar_utils import check_url_xdr, cmd_alarm_url, send_by_list
from utils.telegraph_tools import telegraph

router = Router()

my_talk_message = []


########################################################################################################################
##########################################  functions  #################################################################
########################################################################################################################

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


########################################################################################################################
##########################################  handlers  ##################################################################
########################################################################################################################


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
