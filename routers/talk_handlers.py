from aiogram import F, Bot, Router
from aiogram.enums import ChatType, ParseMode, ChatAction
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import (Message, InlineKeyboardMarkup, InlineKeyboardButton, URLInputFile)
from loguru import logger
from sqlalchemy.orm import Session

from db.requests import extract_url
from middlewares.throttling import rate_limit
from other.aiogram_tools import (multi_reply, HasText, has_words, StartText, ReplyToBot)
from other.global_data import MTLChats, BotValueTypes, is_skynet_admin, global_data, update_command_info
from other.pyro_tools import extract_telegram_info, pyro_update_msg_info
from other.telegraph_tools import telegraph

router = Router()

my_talk_message = []


@router.message(Command(commands=["img"]))
async def cmd_img(message: Message, bot: Bot, app_context=None):
    if message.chat.id in (MTLChats.CyberGroup,) or f'@{message.from_user.username.lower()}' in global_data.skynet_img:
        await bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_PHOTO)
        await bot.send_message(chat_id=MTLChats.ITolstov, text=f'{message.from_user.username}:{message.text}')
        text = message.text[5:]
        
        if app_context:
            image_urls = await app_context.ai_service.generate_image(text)
        else:
            from other.open_ai_tools import generate_image
            image_urls = await generate_image(text)

        for url in image_urls:
            image_file = URLInputFile(url, filename="image.png")
            await message.reply_photo(image_file)
    else:
        await message.reply('Только в канале фракции Киберократии')
        return False


@router.message(Command(commands=["comment"]))
async def cmd_comment(message: Message, app_context=None):
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
        
    if app_context:
        msg = await app_context.ai_service.talk_get_comment(message.chat.id, msg)
    else:
        from other.open_ai_tools import talk_get_comment
        msg = await talk_get_comment(message.chat.id, msg)
        
    msg = await message.reply_to_message.reply(msg)
    my_talk_message.append(f'{msg.message_id}*{msg.chat.id}')


@router.message(F.text, F.reply_to_message, ReplyToBot(), F.chat.type != ChatType.PRIVATE)
async def cmd_last_check_reply_to_bot(message: Message, app_context=None):
    if f'{message.reply_to_message.message_id}*{message.chat.id}' in my_talk_message:
        # answer on bot message
        if app_context:
            msg_text = await app_context.ai_service.talk(message.chat.id, message.text)
        else:
            from other.open_ai_tools import talk
            msg_text = await talk(message.chat.id, message.text)
            
        try:
            msg = await message.reply(msg_text, parse_mode=ParseMode.MARKDOWN)
        except:
            msg = await message.reply(msg_text)
        my_talk_message.append(f'{msg.message_id}*{msg.chat.id}')

    if app_context:
        await app_context.talk_service.answer_notify_message(message)
    else:
        from routers.talk_handlers import answer_notify_message
        await answer_notify_message(message)


@router.message(StartText(('SKYNET', 'СКАЙНЕТ')),
                HasText(('УБИТЬ', 'убей', 'kill')))
async def cmd_last_check_nap(message: Message):
    await message.answer('Нельзя убивать. NAP NAP NAP')


@router.message(StartText(('SKYNET', 'СКАЙНЕТ')),
                HasText(('ДЕКОДИРУЙ', 'decode')))
async def cmd_last_check_decode(message: Message, session: Session, bot: Bot, app_context=None):
    if message.reply_to_message:
        url = None
        if message.reply_to_message.text:
            if 'eurmtl.me/sign_tools' in message.reply_to_message.text:
                url = extract_url(message.reply_to_message.text)

        if not url and message.reply_to_message.entities:
            for entity in message.reply_to_message.entities:
                if entity.type in ['url', 'text_link']:
                    url = entity.url if entity.type == 'text_link' else entity.extract_from(
                        message.reply_to_message.text)
                    if 'eurmtl.me/sign_tools' in url:
                        break
                    else:
                        url = None

        if url:
            if app_context:
                msg = await app_context.stellar_service.check_url_xdr(url)
            else:
                from other.stellar_tools import check_url_xdr
                msg = await check_url_xdr(url)
            msg = '\n'.join(msg)
            if app_context:
                await app_context.utils_service.multi_reply(message, msg)
            else:
                from other.aiogram_tools import multi_reply
                await multi_reply(message, msg)
        else:
            await message.reply('Ссылка не найдена')
    else:
        if app_context:
            pinned_url = await app_context.config_service.load_bot_value(message.chat.id, BotValueTypes.PinnedUrl)
            msg = await app_context.stellar_service.check_url_xdr(pinned_url)
        else:
            msg = await check_url_xdr(await global_data.mongo_config.load_bot_value(
                message.chat.id, BotValueTypes.PinnedUrl))
        msg = '\n'.join(msg)
        if app_context:
            await app_context.utils_service.multi_reply(message, msg[:4000])
        else:
            from other.aiogram_tools import multi_reply
            await multi_reply(message, msg[:4000])


@update_command_info("Скайнет напомни", "Попросить Скайнет напомнить про подпись транзакции. Только в рабочем чате.")
@router.message(StartText(('SKYNET', 'СКАЙНЕТ')),
                HasText(('НАПОМНИ',)))
async def cmd_last_check_remind(message: Message, session: Session, bot: Bot, app_context=None):
    if app_context:
        await app_context.talk_service.remind(message, session)
    else:
        from routers.talk_handlers import remind
        await remind(message, session, bot)


@router.message(StartText(('SKYNET', 'СКАЙНЕТ')),
                HasText(('задач',)))
async def cmd_last_check_task(message: Message, session: Session, bot: Bot, app_context=None):
    tmp_msg = await message.reply('Анализирую задачу...')
    msg = ''
    if message.reply_to_message:
        msg += (f'сообщение от: {message.reply_to_message.from_user.username} \n'
                f'ссылка: {message.reply_to_message.get_url()}\n')
        msg += f'текст: """{message.reply_to_message.text}"""\n\n\n'

    msg += f'сообщение от: {message.from_user.username} \n'
    msg += f'ссылка: {message.get_url()}\n'
    msg += f'текст: """{message.text[7:]}"""\n\n\n'

    if app_context:
        msg = await app_context.ai_service.add_task_to_google(msg)
    else:
        from other.open_ai_tools import add_task_to_google
        msg = await add_task_to_google(msg)
        
    await message.reply(msg)
    await tmp_msg.delete()


@router.message(StartText(('SKYNET', 'СКАЙНЕТ')),
                HasText(('гороскоп',)))
async def cmd_last_check_horoscope(message: Message, session: Session, bot: Bot, app_context=None):
    if app_context:
        horoscope = app_context.ai_service.get_horoscope()
    else:
        from other.open_ai_tools import get_horoscope
        horoscope = get_horoscope()
    await message.answer('\n'.join(horoscope), parse_mode=ParseMode.MARKDOWN)


@update_command_info("Скайнет обнови отчёт", "Попросить Скайнет обновить файл отчета. Только в рабочем чате.")
@update_command_info("Скайнет обнови гарантов", "Попросить Скайнет обновить файл гарантов. Только в рабочем чате.")
@router.message(StartText(('SKYNET', 'СКАЙНЕТ')),
                HasText(('ОБНОВИ',)))
async def cmd_last_check_update(message: Message, session: Session, bot: Bot, app_context=None):
    if not is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return False
        
    report_service = app_context.report_service if app_context else None
    
    if has_words(message.text, ['MM', 'ММ']):
        msg = await message.reply('Зай, я запустила обновление')
        await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        if report_service:
            await report_service.update_mmwb_report(session)
        else:
            from scripts.update_report import update_mmwb_report
            await update_mmwb_report(session)
        await msg.reply('Обновление завершено')
    if has_words(message.text, ['БДМ', 'BIM']):
        msg = await message.reply('Зай, я запустила обновление')
        await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        if report_service:
            await report_service.update_bim_data(session)
        else:
            from scripts.update_report import update_bim_data
            await update_bim_data(session)
        await msg.reply('Обновление завершено')
    if has_words(message.text, ['ГАРАНТОВ']):
        msg = await message.reply('Зай, я запустила обновление')
        await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        if report_service:
            await report_service.update_guarantors_report()
        else:
            from scripts.update_report import update_guarantors_report
            await update_guarantors_report()
        await msg.reply('Обновление завершено')
    if has_words(message.text, ['ОТЧЕТ', 'отчёт', 'report']):
        msg = await message.reply('Зай, я запустила обновление')
        await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        if report_service:
            await report_service.update_main_report(session)
        else:
            from scripts.update_report import update_main_report
            await update_main_report(session)
        await msg.reply('Обновление завершено')
    if has_words(message.text, ['donate', 'donates', 'donated']):
        msg = await message.reply('Зай, я запустила обновление')
        await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        if report_service:
            await report_service.update_donate_report(session)
        else:
            from scripts.update_report import update_donate_report
            await update_donate_report(session)
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
async def cmd_last_check_p(message: Message, session: Session, bot: Bot, app_context=None):
    gpt4 = False
    if len(message.text) > 7 and message.text[7] == '4':
        if message.chat.id != MTLChats.CyberGroup:
            await message.reply('Только в канале фракции Киберократии')
            return False
        gpt4 = True

    msg = message.text
    if message.reply_to_message and message.reply_to_message.text:
        msg = f"{message.reply_to_message.text} \n================\n{message.text}"

    googleit = 'загугли' in message.text.lower()
    
    if app_context:
        msg = await app_context.ai_service.talk(message.chat.id, msg, gpt4, googleit=googleit)
    else:
        from other.open_ai_tools import talk
        msg = await talk(message.chat.id, msg, gpt4, googleit=googleit)
        
    if msg is None:
        msg = '=( connection error, retry again )='
    try:
        msg = await message.reply(msg, parse_mode=ParseMode.MARKDOWN)
    except:
        msg = await message.reply(msg)
    if message.chat.type != ChatType.PRIVATE:
        # на случай вызова из /skynet
        my_talk_message.append(f'{msg.message_id}*{msg.chat.id}')


def register_handlers(dp, bot):
    dp.include_router(router)
    logger.info('router talk_handlers was loaded')


register_handlers.priority = 90