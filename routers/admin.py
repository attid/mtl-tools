import asyncio
import base64
import hashlib
import json
import os
import re
from contextlib import suppress

from aiogram import Router, Bot, F
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, FSInputFile, ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, \
    ReactionTypeEmoji, ReplyParameters
from loguru import logger
from sentry_sdk.integrations import aiohttp
from sqlalchemy.orm import Session

from config_reader import config
from db.requests import db_save_bot_value, db_get_messages_without_summary, db_add_summary, db_get_summary
from middlewares.sentry_error_handler import sentry_error_handler
from utils.aiogram_utils import is_admin, cmd_delete_later, cmd_sleep_and_delete
from utils.dialog import talk_get_summary
from utils.global_data import MTLChats, is_skynet_admin, global_data, BotValueTypes, update_command_info
from utils.gspread_tools import gs_find_user, gs_get_all_mtlap, gs_get_update_mtlap_skynet_row
from utils.stellar_utils import send_by_list
from utils.timedelta import parse_timedelta_from_message

router = Router()
router.error()(sentry_error_handler)


@router.message(Command(commands=["exit"]))
@router.message(Command(commands=["restart"]))
async def cmd_exit(message: Message, state: FSMContext):
    if not is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return False

    data = await state.get_data()
    my_state = data.get('MyState')

    if my_state == 'StateExit':
        await state.update_data(MyState=None)
        await message.reply(":[[[ ушла в закат =(")
        exit()
    else:
        await state.update_data(MyState='StateExit')
        await message.reply(":'[ боюсь")


@router.message(Command(commands=["err"]))
async def cmd_log_err(message: Message):
    if not is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return False
    await cmd_send_file(message, 'skynet.err')


@router.message(Command(commands=["log"]))
async def cmd_log(message: Message, state: FSMContext):
    if not is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return False
    await cmd_send_file(message, 'skynet.log')


async def cmd_send_file(message: Message, filename):
    if os.path.isfile(filename):
        await message.reply_document(FSInputFile(filename))


@update_command_info("/push", "Отправить сообщение в личку. Только для админов скайнета")
@router.message(Command(commands=["push"]))
async def cmd_push(message: Message, bot: Bot):
    if not is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return

    if message.reply_to_message is None:
        await message.reply('Команду надо посылать в ответ на список логинов')
        return

    if message.reply_to_message.text.find('@') == -1:
        await message.reply('Нет не одной собаки. Команда работает в ответ на список логинов')
        return

    all_users = message.reply_to_message.text.split()
    await send_by_list(bot, all_users, message)


async def check_membership(bot: Bot, chat_id: str, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR]
    except TelegramBadRequest:
        return False


@router.message(Command(commands=["get_info"]))
@router.message(Command(re.compile(r"get_info_(\d+)")))
async def cmd_get_info(message: Message, bot: Bot):
    if not is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return

    command_args = message.text.split()
    if command_args[0] == "get_info":
        if len(command_args) < 2 or not command_args[1].startswith("#ID"):
            await message.reply('Пришлите ID в формате #ID0000')
            return
        user_id = command_args[1][3:]  # убрать "#ID" из начала строки
    else:
        user_id = command_args[0].split('_')
        if len(user_id) == 3:
            user_id = user_id[2].split('@')[0]

    if not user_id.isdigit():
        await message.reply('ID должен быть числом.')
        return

    messages = []

    is_member = await check_membership(bot, MTLChats.MonteliberoChanel, int(user_id))
    if is_member:
        messages.append("Пользователь подписан на канал Montelibero")
    else:
        messages.append("Пользователь не подписан на канал")

    messages.extend(await gs_find_user(user_id))

    await message.reply('\n'.join(messages))


@router.message(F.text.startswith("!ro"))
async def cmd_set_ro(message: Message):
    if not await is_admin(message):
        await message.reply('You are not admin.')
        return False

    if message.reply_to_message is None:
        await message.reply('Please send for reply message to set ro')
        return

    delta = await parse_timedelta_from_message(message)
    await message.chat.restrict(message.reply_to_message.from_user.id,
                                permissions=ChatPermissions(can_send_messages=False,
                                                            can_send_media_messages=False,
                                                            can_send_other_messages=False),
                                until_date=delta)

    user = message.reply_to_message.from_user.username if message.reply_to_message.from_user.username else message.reply_to_message.from_user.full_name
    await message.reply(f'{user} was set ro for {delta}')


@router.message(Command(commands=["listen"]))
async def cmd_set_listen(message: Message, session: Session):
    if not is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return False

    if message.chat.id in global_data.listen:
        global_data.listen.remove(message.chat.id)
        db_save_bot_value(session, message.chat.id, BotValueTypes.Listen, None)
        msg = await message.reply('Removed')
    else:
        global_data.listen.append(message.chat.id)
        db_save_bot_value(session, message.chat.id, BotValueTypes.Listen, 1)
        msg = await message.reply('Added')

    cmd_delete_later(message, 1)
    cmd_delete_later(msg, 1)


@router.message(Command(commands=["summary"]))
async def cmd_get_summary(message: Message, session: Session):
    if not is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return False

    if not (message.chat.id in global_data.listen):
        await message.reply('No messages 1')
        return

    data = db_get_messages_without_summary(session, chat_id=message.chat.id,
                                           thread_id=message.message_thread_id if message.is_topic_message else None)

    if len(data) > 0:
        text = ''
        summary = db_add_summary(session=session, text=text)
        session.flush()  # обновляем базу данных, чтобы получить ID для summary

        for record in data:
            new_text = text + f'{record.username}: {record.text} \n\n'
            if len(new_text) < 16000:
                text = new_text
                record.summary_id = summary.id
                session.flush()  # обновляем базу данных с новым summary_id
            else:
                summary.text = await talk_get_summary(text)
                session.flush()  # обновляем базу данных с новым текстом для summary
                summary = db_add_summary(session=session, text='')
                session.flush()  # обновляем базу данных, чтобы получить новый ID для summary
                text = record.username + ': ' + record.text + '\n\n'
                record.summary_id = summary.id
                session.flush()  # обновляем базу данных с новым summary_id
        summary.text = await talk_get_summary(text)
        session.flush()  # обновляем базу данных с последним текстом для summary

    for record in db_get_summary(session=session, chat_id=message.chat.id,
                                 thread_id=message.message_thread_id if message.is_topic_message else None):
        await message.reply(record.text[:4000])

    session.commit()  # завершаем транзакцию


@router.message(F.document, F.chat.type == ChatType.PRIVATE)
async def cmd_get_sha1(message: Message, bot: Bot):
    document = message.document
    file_data = await bot.download(document)
    file_bytes = file_data.read()

    print(type(file_data), file_data)

    hasher = hashlib.sha1()
    hasher.update(file_bytes)

    # Get the SHA-1 hash and convert it into bytes
    sha1_hash = hasher.hexdigest()  # .encode('utf-8')
    print(sha1_hash, sha1_hash)

    # Encode the bytes to BASE64
    base64_hash = base64.b64encode(hasher.digest()).decode('utf-8')
    print(sha1_hash, base64_hash)

    # sha256
    sha256_hasher = hashlib.sha256()
    sha256_hasher.update(file_bytes)
    sha256_hash = sha256_hasher.hexdigest()

    print(f"SHA-256: {sha256_hash}")

    await message.reply(f'SHA-1: <code>{sha1_hash}</code>\n'
                        f'BASE64: <code>{base64_hash}</code>\n\n'
                        f'SHA-256: <code>{sha256_hash}</code>')
    # hex: 679cd49aec59cf2ccaf843ea4c484975d33dd18a
    # base64: Z5zUmuxZzyzK+EPqTEhJddM90Yo=
    # Soz Nov 1982-11-14


@router.message(Command(commands=["sha256"]))
async def cmd_get_info(message: Message, bot: Bot):
    sha256_hasher = hashlib.sha256()
    print(message.text[8:])
    sha256_hasher.update(message.text[8:].encode('utf-8'))
    sha256_hash = sha256_hasher.hexdigest()
    print(sha256_hash)
    await message.reply(f'SHA-256: <code>{sha256_hash}</code>')


@router.message(Command(commands=["s"]))
@router.message(Command(commands=["send_me"]))
async def cmd_get_info(message: Message, bot: Bot):
    if not await is_admin(message):
        await message.reply('You are not admin.')
        return

    if message.reply_to_message is None:
        await message.reply('Please send for reply message to get it')
        return

    if message.reply_to_message:
        await bot.send_message(chat_id=message.from_user.id, text=message.reply_to_message.html_text)


@update_command_info("/alert_me", "Делает подписку на упоминания и сообщает об упоминаниях в личку(alarm)")
@router.message(Command(commands=["alert_me"]))
async def cmd_set_alert_me(message: Message, session: Session):
    if message.chat.id in global_data.alert_me and message.from_user.id in global_data.alert_me[message.chat.id]:
        global_data.alert_me[message.chat.id].remove(message.from_user.id)
        db_save_bot_value(session, message.chat.id, BotValueTypes.AlertMe,
                          json.dumps(global_data.alert_me[message.chat.id]))
        msg = await message.reply('Removed')
    else:
        if message.chat.id not in global_data.alert_me:
            global_data.alert_me[message.chat.id] = []
        global_data.alert_me[message.chat.id].append(message.from_user.id)
        db_save_bot_value(session, message.chat.id, BotValueTypes.AlertMe,
                          json.dumps(global_data.alert_me[message.chat.id]))
        msg = await message.reply('Added')

    cmd_delete_later(message, 1)
    cmd_delete_later(msg, 1)


@update_command_info("/sync", "Синхронизирует сообщение в чате с постом в канале")
@router.message(Command(commands=["sync"]))
async def cmd_sync_post(message: Message, session: Session, bot: Bot):
    if not await is_admin(message):
        await message.reply('You are not admin.')
        return

    if not message.reply_to_message or not message.reply_to_message.forward_from_chat:
        await message.reply('Могу синхронизировать только посты')
        return

    try:
        chat = await bot.get_chat(message.reply_to_message.forward_from_chat.id)
        post_id = message.reply_to_message.forward_from_message_id
        url = f'https://t.me/c/{str(chat.id)[4:]}/{message.reply_to_message.forward_from_message_id}'
        msg_text = message.reply_to_message.html_text
        reply_markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Edit', url=url),
                                                              InlineKeyboardButton(text='Edit', url=url)]])
        if msg_text[-1] == '*':
            msg_text = msg_text[:-1]
            reply_markup = None
        new_msg = await message.answer(msg_text, disable_web_page_preview=True,
                                       reply_markup=reply_markup)

        if chat.id not in global_data.sync:
            global_data.sync[chat.id] = {}

        if str(post_id) not in global_data.sync[chat.id]:
            global_data.sync[chat.id][str(post_id)] = []

        global_data.sync[chat.id][str(post_id)].append({'chat_id': message.chat.id,
                                                        'message_id': new_msg.message_id,
                                                        'url': url})

        db_save_bot_value(session, chat.id, BotValueTypes.Sync,
                          json.dumps(global_data.sync[chat.id]))

        with suppress(TelegramBadRequest):
            await message.reply_to_message.delete()
        await message.delete()

    except:
        await message.reply('Канал не найден, нужно быть админом в канале')
        return

    return


@router.edited_channel_post(F.text)
async def cmd_edited_channel_post(message: Message, session: Session, bot: Bot):
    # if message.chat.id in (-1001863399780, -1001652080456, -1001649743884):  # chat ids for reading
    #     msg_url = message.get_url(force_private=True)
    #     msg_text = message.text
    #
    #     headers = {
    #         "Authorization": f"Bearer {config.eurmtl_key}",
    #         "Content-Type": "application/json"
    #     }
    #
    #     data = {
    #         "msg_url": msg_url,
    #         "msg_text": msg_text
    #     }
    #
    #     # Отправка запроса на сервер
    #     async with aiohttp.ClientSession() as http_session:
    #         async with http_session.post("https://eurmtl.me/decision/update_text", headers=headers,
    #                                      data=json.dumps(data)) as response:
    #             # Запись ответа в лог
    #             logger.info(f"Status: {response.status}, Response: {await response.text()}")

    if message.chat.id in global_data.sync:
        if str(message.message_id) in global_data.sync[message.chat.id]:
            for data in global_data.sync[message.chat.id][str(message.message_id)]:
                with suppress(TelegramBadRequest):
                    msg_text = message.html_text
                    reply_markup = InlineKeyboardMarkup(
                        inline_keyboard=[[InlineKeyboardButton(text='Edit', url=data['url']),
                                          InlineKeyboardButton(text='Edit', url=data['url'])]])
                    if msg_text[-1] == '*':
                        msg_text = msg_text[:-1]
                        reply_markup = None
                    await bot.edit_message_text(text=msg_text, chat_id=data['chat_id'],
                                                message_id=data['message_id'], disable_web_page_preview=True,
                                                reply_markup=reply_markup)


@update_command_info("/web_pin", "Делает пост который можно потом редактировать в WebApp")
@update_command_info("/web_pin comment",
                     "В личке делает пост который можно потом редактировать в WebApp по ссылке для пересылки")
@router.message(Command(commands=["web_pin"]))
async def cmd_web_pin(message: Message, command: CommandObject):
    text = command.args
    if not text:
        text = 'new text'

    if message.chat.type == ChatType.PRIVATE:
        headers = {
            "Authorization": f"Bearer {config.eurmtl_key}",
            "Content-Type": "application/json"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get("https://eurmtl.me/remote/get_new_pin_id", headers=headers) as response:
                return_json = await response.json()
        message_uuid = return_json['uuid']
        edit_button_url = f'https://t.me/myMTLbot/WebEditor?startapp=0_{message_uuid}'
        reply_markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='Edit', url=edit_button_url)]
        ])
        await message.answer(text, reply_markup=reply_markup)
        return

    # else

    sent_message = await message.answer(text)

    # Получаем chat_id и message_id отправленного сообщения
    chat_id = message.chat.shifted_id
    message_id = sent_message.message_id

    # Формируем URL для кнопки с учетом chat_id и message_id
    edit_button_url = f'https://t.me/myMTLbot/WebEditor?startapp={chat_id}_{message_id}'

    # Создаем клавиатуру с кнопками
    reply_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Edit', url=edit_button_url),
         InlineKeyboardButton(text='Edit', url=edit_button_url)]
    ])

    # Обновляем сообщение, добавляя клавиатуру
    await sent_message.edit_reply_markup(reply_markup=reply_markup)


commands_info = {
    "set_reply_only": (global_data.reply_only, BotValueTypes.ReplyOnly, "toggle", "admin"),
    "delete_income": (global_data.delete_income, BotValueTypes.DeleteIncome, "toggle", "admin"),
    "set_no_first_link": (global_data.no_first_link, BotValueTypes.NoFirstLink, "toggle", "admin"),
    # full_data - чаты с полной расшифровкой по адресу
    "full_data": (global_data.full_data, BotValueTypes.FullData, "toggle", "skynet_admin"),
    "need_decode": (global_data.need_decode, BotValueTypes.NeedDecode, "toggle", "admin"),
    "save_last_message_date": (global_data.save_last_message_date, BotValueTypes.SaveLastMessageDate,
                               "toggle", "admin"),
    "notify_join_request": (global_data.notify_join, BotValueTypes.NotifyJoin, "toggle_chat", "admin"),
    "notify_message": (global_data.notify_message, BotValueTypes.NotifyMessage, "toggle_chat", "admin"),

    "add_skynet_img": (global_data.skynet_img, BotValueTypes.SkynetImg, "add_list", "skynet_admin"),
    "del_skynet_img": (global_data.skynet_img, BotValueTypes.SkynetImg, "del_list", "skynet_admin"),
    "show_skynet_img": (global_data.skynet_img, BotValueTypes.SkynetImg, "show_list", "skynet_admin"),
    "add_skynet_admin": (global_data.skynet_admins, BotValueTypes.SkynetAdmins, "add_list", "skynet_admin"),
    "del_skynet_admin": (global_data.skynet_admins, BotValueTypes.SkynetAdmins, "del_list", "skynet_admin"),
    "show_skynet_admin": (global_data.skynet_admins, BotValueTypes.SkynetAdmins, "show_list", "skynet_admin"),

}


@update_command_info("/set_reply_only", "Следить за сообщениями вне тренда и сообщать об этом.")
@update_command_info("/delete_income", "Разрешить боту удалять сообщения о входе и выходе участников чата")
@update_command_info("/set_no_first_link", "Защита от спама первого сообщения с ссылкой")
@update_command_info("/need_decode", "Нужно ли декодировать сообщения в чате.")
@update_command_info("/save_last_message_date", "Сохранять ли время последнего сообщения в чате")
@update_command_info("/add_skynet_img",
                     "Добавить пользователей в пользователи img. запуск с параметрами /add_skynet_admin @user1 @user2 итд")
@update_command_info("/del_skynet_admin",
                     "Убрать пользователей из админов скайнета. запуск с параметрами /del_skynet_admin @user1 @user2 итд")
@update_command_info("/add_skynet_admin",
                     "Добавить пользователей в админы скайнета. запуск с параметрами /add_skynet_admin @user1 @user2 итд")
@update_command_info("/show_skynet_admin", "Показать админов скайнета")
@update_command_info("/notify_join_request",
                     "Оповещать о новом участнике, требующем подтверждения для присоединения. "
                     "Если вторым параметром будет группа в виде -100123456 то оповещать будет в эту группу")
@update_command_info("/notify_message",
                     "Оповещать о новом сообщении в определенный чат"
                     "Чат указываем в виде -100123456 для обычного чата или -100123456:12345 для чата с топиками")

@router.message(Command(commands=list(commands_info.keys())))
async def universal_command_handler(message: Message, session: Session, bot: Bot):
    command = message.text.lower().split()[0][1:]
    command_arg = message.text.lower().split()[1] if len(message.text.lower().split()) > 1 else None
    command_info = commands_info[command]
    action_type = command_info[2]
    admin_check = command_info[3]

    if admin_check == "skynet_admin" and not is_skynet_admin(message):
        await message.reply("You are not my admin.")
        return
    elif admin_check == "admin" and not await is_admin(message):
        await message.reply("You are not admin.")
        return

    if command_info[2] == "toggle_chat" and command_arg and len(command_arg) > 5:
        dest_chat = command_arg.split(":")[0]
        dest_admin = await is_admin(message, dest_chat)
        if not dest_admin:
            await message.reply("Bad target chat. Or you are not admin.")
            return

    await bot.set_message_reaction(chat_id=message.chat.id, message_id=message.message_id,
                                   reaction=[ReactionTypeEmoji(emoji='👀')])

    if action_type in ["add_list", "del_list", "show_list"]:
        await list_command_handler(message, session, command_info)
    else:
        await handle_command(message, session, command_info)


async def handle_command(message: Message, session: Session, command_info):
    chat_id = message.chat.id
    global_data_field, db_value_type, action, admin_check = command_info

    command_args = message.text.split()[1:]  # Список аргументов после команды

    if chat_id in global_data_field:
        if isinstance(global_data_field, dict):
            global_data_field.pop(chat_id)
        else:
            global_data_field.remove(chat_id)
        db_save_bot_value(session, chat_id, db_value_type, None)
        info_message = await message.reply('Removed')
    else:
        value_to_set = command_args[0] if command_args else '1'
        if isinstance(global_data_field, dict):
            global_data_field[chat_id] = value_to_set
        else:
            global_data_field.append(chat_id)

        db_save_bot_value(session, chat_id, db_value_type, value_to_set)
        info_message = await message.reply('Added')

    await cmd_sleep_and_delete(info_message, 5)

    with suppress(TelegramBadRequest):
        await asyncio.sleep(1)
        await message.delete()


async def list_command_handler(message: Message, session: Session, command_info):
    global_data_field, db_value_type, action_type, admin_check = command_info
    command_args = message.text.lower().split()[1:]  # аргументы после команды

    if action_type == "add_list":
        if not command_args:
            await message.reply("Необходимо указать аргументы.")
        else:
            global_data_field.extend(command_args)
            db_save_bot_value(session, 0, db_value_type, json.dumps(global_data_field))
            await message.reply(f'Added: {" ".join(command_args)}')

    elif action_type == "del_list":
        if not command_args:
            await message.reply("Необходимо указать аргументы.")
        else:
            for arg in command_args:
                if arg in global_data_field:
                    global_data_field.remove(arg)
            db_save_bot_value(session, 0, db_value_type, json.dumps(global_data_field))
            await message.reply(f'Removed: {" ".join(command_args)}')

    elif action_type == "show_list":
        if global_data_field:
            await message.reply(' '.join(global_data_field))
        else:
            await message.reply('The list is empty.')


@router.message(Command(commands=["update_mtlap"]))
async def cmd_update_mtlap(message: Message, bot: Bot):
    if not is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return

    data = await gs_get_all_mtlap()

    # Проверка заголовков
    if not data or len(data) < 1:
        await message.reply("Ошибка: таблица пуста или не найдены данные.")
        return

    headers = data[0]

    if len(headers) < 15 or headers[1] != "TGID" or headers[14] != "SkyNet":
        await message.reply("Ошибка: неверный формат таблицы. Проверьте наличие и позицию столбцов TGID и SkyNet.")
        return

    results = []
    user_id: int

    for row in data[1:]:
        if len(row[1]) < 3:
            break

        try:
            user_id = int(row[1])
            await bot.send_chat_action(user_id, action='typing')
            results.append(True)
        except Exception as e:
            results.append(False)
        await asyncio.sleep(0.1)

    await gs_get_update_mtlap_skynet_row(results)

    await message.reply("Готово.")