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
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import (Message, FSInputFile, ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton,
                           ReactionTypeEmoji, User, LoginUrl, ChatMemberUpdated)
from loguru import logger
from sentry_sdk.integrations import aiohttp
from sqlalchemy.orm import Session

from other.config_reader import config
from db.requests import db_get_messages_without_summary, db_add_summary, db_get_summary
from other.aiogram_tools import is_admin, cmd_delete_later, cmd_sleep_and_delete
from other.open_ai_tools import talk_get_summary
from other.global_data import MTLChats, is_skynet_admin, global_data, BotValueTypes, update_command_info
from other.gspread_tools import gs_find_user, gs_get_all_mtlap, gs_get_update_mtlap_skynet_row
from other.mtl_tools import check_consul_mtla_chats
from other.pyro_tools import get_group_members, remove_deleted_users, pyro_test
from other.stellar_tools import send_by_list
from other.timedelta import parse_timedelta_from_message

router = Router()


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
        global_data.reboot = True
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


@router.message(Command(commands=["ping_piro"]))
async def cmd_log(message: Message, state: FSMContext):
    if not is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return False
    await pyro_test()


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


async def check_membership(bot: Bot, chat_id: str, user_id: int) -> (bool, User):
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        is_member = member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR]
        return is_member, member.user

    except TelegramBadRequest as e:
        return False, None


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

    chat_list = (
        (MTLChats.MonteliberoChanel, "канал Montelibero ru"),
        (MTLChats.MTLAAgoraGroup, "MTLAAgoraGroup"),
        (-1001429770534, "chat Montelibero ru"),
    )

    for chat_id, chat_name in chat_list:
        is_member, user = await check_membership(bot, chat_id, int(user_id))
        if is_member:
            messages.append(f"Пользователь @{user.username} подписан на {chat_name}")
        else:
            messages.append(f"Пользователь не подписан на {chat_name}")
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

    # print(type(file_data), file_data)

    hasher = hashlib.sha1()
    hasher.update(file_bytes)

    # Get the SHA-1 hash and convert it into bytes
    sha1_hash = hasher.hexdigest()  # .encode('utf-8')
    # print(sha1_hash, sha1_hash)

    # Encode the bytes to BASE64
    base64_hash = base64.b64encode(hasher.digest()).decode('utf-8')
    # print(sha1_hash, base64_hash)

    # sha256
    sha256_hasher = hashlib.sha256()
    sha256_hasher.update(file_bytes)
    sha256_hash = sha256_hasher.hexdigest()

    # print(f"SHA-256: {sha256_hash}")

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
async def cmd_send_me(message: Message, bot: Bot):
    if not await is_admin(message):
        await message.reply('You are not admin.')
        return

    if message.reply_to_message is None:
        await message.reply('Please send for reply message to get it')
        return

    if message.reply_to_message:
        if message.reply_to_message.text or message.reply_to_message.caption:
            await bot.send_message(chat_id=message.from_user.id,
                                   text=message.reply_to_message.html_text or message.reply_to_message.caption)

        if message.reply_to_message.photo:
            photo = message.reply_to_message.photo[-1]
            await bot.send_photo(chat_id=message.from_user.id, photo=photo.file_id,
                                 caption=message.reply_to_message.caption)

        elif message.reply_to_message.video:
            video = message.reply_to_message.video
            await bot.send_video(chat_id=message.from_user.id, video=video.file_id,
                                 caption=message.reply_to_message.caption)


@update_command_info("/alert_me", "Делает подписку на упоминания и сообщает об упоминаниях в личку(alarm)", 3,
                     "alert_me")
@router.message(Command(commands=["alert_me"]))
async def cmd_set_alert_me(message: Message, session: Session):
    if message.chat.id in global_data.alert_me and message.from_user.id in global_data.alert_me[message.chat.id]:
        global_data.alert_me[message.chat.id].remove(message.from_user.id)
        await global_data.mongo_config.save_bot_value(message.chat.id, BotValueTypes.AlertMe,
                                                      json.dumps(global_data.alert_me[message.chat.id]))
        msg = await message.reply('Removed')
    else:
        if message.chat.id not in global_data.alert_me:
            global_data.alert_me[message.chat.id] = []
        global_data.alert_me[message.chat.id].append(message.from_user.id)
        await global_data.mongo_config.save_bot_value(message.chat.id, BotValueTypes.AlertMe,
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
    except TelegramBadRequest:
        await message.reply('Канал не найден, нужно быть админом в канале')
        return
    except Exception as e:
        logger.error(f"Unexpected error while getting chat: {e}")
        await message.reply('Произошла непредвиденная ошибка при получении информации о канале')
        return

    try:
        post_id = message.reply_to_message.forward_from_message_id
        url = f'https://t.me/c/{str(chat.id)[4:]}/{post_id}'
        msg_text = message.reply_to_message.html_text
        reply_markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Edit', url=url),
                                                              InlineKeyboardButton(text='Edit', url=url)]])
        if msg_text and msg_text[-1] == '*':
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

        await global_data.mongo_config.save_bot_value(chat.id, BotValueTypes.Sync,
                                                      json.dumps(global_data.sync[chat.id]))

        with suppress(TelegramBadRequest):
            await message.reply_to_message.delete()
        with suppress(TelegramBadRequest):
            await message.delete()

    except Exception as e:
        logger.error(f"Error in cmd_sync_post: {e}")
        await message.reply('Произошла ошибка при синхронизации поста')


@update_command_info("/resync", "Восстанавливает синхронизацию сообщения с постом в канале")
@router.message(Command(commands=["resync"]))
async def cmd_resync_post(message: Message, session: Session, bot: Bot):
    if not await is_admin(message):
        await message.reply('You are not admin.')
        return

    if not message.reply_to_message or not message.reply_to_message.from_user.id == bot.id:
        await message.reply('Нужно ответить на сообщение, отправленное ботом')
        return

    try:
        # Получаем клавиатуру из сообщения бота
        reply_markup = message.reply_to_message.reply_markup
        if not reply_markup or not isinstance(reply_markup, InlineKeyboardMarkup):
            await message.reply('Не найдена клавиатура с кнопкой редактирования')
            return

        # Извлекаем URL из кнопки Edit
        edit_button = next((button for row in reply_markup.inline_keyboard for button in row if button.text == 'Edit'),
                           None)
        if not edit_button:
            await message.reply('Не найдена кнопка Edit')
            return

        url = edit_button.url
        # Извлекаем chat_id и post_id из URL
        match = re.search(r'https://t\.me/c/(\d+)/(\d+)', url)
        if not match:
            await message.reply('Неверный формат URL')
            return

        chat_id, post_id = match.groups()
        chat_id = int(f"-100{chat_id}")

        # Проверяем, есть ли запись в БД
        if chat_id not in global_data.sync:
            global_data.sync[chat_id] = {}

        if post_id not in global_data.sync[chat_id]:
            global_data.sync[chat_id][post_id] = []

        # Проверяем, существует ли уже запись для данного чата и сообщения
        existing_record = next((record for record in global_data.sync[chat_id][post_id]
                                if record['chat_id'] == message.chat.id and
                                record['message_id'] == message.reply_to_message.message_id), None)

        if existing_record:
            await message.reply('Синхронизация для этого сообщения уже существует')
        else:
            # Добавляем новую запись, не затрагивая существующие
            global_data.sync[chat_id][post_id].append({
                'chat_id': message.chat.id,
                'message_id': message.reply_to_message.message_id,
                'url': url
            })

            # Сохраняем обновленные данные в БД
            await global_data.mongo_config.save_bot_value(chat_id, BotValueTypes.Sync,
                                                          json.dumps(global_data.sync[chat_id]))

            await message.reply('Синхронизация восстановлена')

    except Exception as e:
        logger.error(f"Error in cmd_resync_post: {e}")
        await message.reply('Произошла ошибка при восстановлении синхронизации')

    # Удаляем команду /resync
    with suppress(TelegramBadRequest):
        await message.delete()


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
    "set_reply_only": (global_data.reply_only, BotValueTypes.ReplyOnly, "toggle", "admin", 1),
    "delete_income": (global_data.delete_income, BotValueTypes.DeleteIncome, "toggle", "admin", 1),
    "set_no_first_link": (global_data.no_first_link, BotValueTypes.NoFirstLink, "toggle", "admin", 1),
    # full_data - чаты с полной расшифровкой по адресу
    "full_data": (global_data.full_data, BotValueTypes.FullData, "toggle", "skynet_admin", 1),
    "need_decode": (global_data.need_decode, BotValueTypes.NeedDecode, "toggle", "admin", 1),
    "save_last_message_date": (global_data.save_last_message_date, BotValueTypes.SaveLastMessageDate,
                               "toggle", "admin", 1),
    "set_first_vote": (global_data.first_vote, BotValueTypes.FirstVote, "toggle", "admin", 1),
    "notify_join_request": (global_data.notify_join, BotValueTypes.NotifyJoin, "toggle_chat", "admin", 1),
    "notify_message": (global_data.notify_message, BotValueTypes.NotifyMessage, "toggle_chat", "admin", 1),
    "join_request_captcha": (global_data.join_request_captcha, BotValueTypes.JoinRequestCaptcha, "toggle", "admin", 1),
    "auto_all": (global_data.auto_all, BotValueTypes.AutoAll, "toggle", "admin", 1),
    "set_listen": (global_data.listen, BotValueTypes.Listen, "toggle", "skynet_admin", 1),
    # ToDo need show to skyadmin in helpers
    "set_captcha": (global_data.captcha, BotValueTypes.Captcha, "toggle", "admin", 1),

    "add_skynet_img": (global_data.skynet_img, BotValueTypes.SkynetImg, "add_list", "skynet_admin", 3),
    "del_skynet_img": (global_data.skynet_img, BotValueTypes.SkynetImg, "del_list", "skynet_admin", 0),
    "show_skynet_img": (global_data.skynet_img, BotValueTypes.SkynetImg, "show_list", "skynet_admin", 0),
    "add_skynet_admin": (global_data.skynet_admins, BotValueTypes.SkynetAdmins, "add_list", "skynet_admin", 3),
    "del_skynet_admin": (global_data.skynet_admins, BotValueTypes.SkynetAdmins, "del_list", "skynet_admin", 0),
    "show_skynet_admin": (global_data.skynet_admins, BotValueTypes.SkynetAdmins, "show_list", "skynet_admin", 0),

}


async def command_config_loads(session: Session):
    for command in commands_info:
        global_data_field = commands_info[command][0]
        global_data_key = commands_info[command][1]
        load_type = commands_info[command][4]  # 0 none 1 - dict\list  3 - json

        if load_type == 1:
            if isinstance(global_data_field, dict):
                global_data_field.update(await global_data.mongo_config.get_chat_dict_by_key(global_data_key))
            else:
                global_data_field.extend(await global_data.mongo_config.get_chat_ids_by_key(global_data_key))

        if load_type == 3:
            if isinstance(global_data_field, dict):
                global_data_field.update(
                    json.loads(await global_data.mongo_config.load_bot_value(0, global_data_key, '{}')))
            else:
                global_data_field.extend(
                    json.loads(await global_data.mongo_config.load_bot_value(0, global_data_key, '[]')))

    global_data.votes = json.loads(await global_data.mongo_config.load_bot_value(0, BotValueTypes.Votes, '{}'))

    global_data.welcome_messages = await global_data.mongo_config.get_chat_dict_by_key(BotValueTypes.WelcomeMessage)
    global_data.welcome_button = await global_data.mongo_config.get_chat_dict_by_key(BotValueTypes.WelcomeButton)
    global_data.admins = await global_data.mongo_config.get_chat_dict_by_key(BotValueTypes.Admins, True)
    global_data.alert_me = await global_data.mongo_config.get_chat_dict_by_key(BotValueTypes.AlertMe, True)
    global_data.sync = await global_data.mongo_config.get_chat_dict_by_key(BotValueTypes.Sync, True)


@update_command_info("/set_reply_only", "Следить за сообщениями вне тренда и сообщать об этом.", 1, "reply_only")
@update_command_info("/set_first_vote", "Показывать ли голосованием о первом сообщении.", 1, "first_vote")
@update_command_info("/delete_income", "Разрешить боту удалять сообщения о входе и выходе участников чата", 2,
                     "delete_income")
@update_command_info("/set_no_first_link", "Защита от спама первого сообщения с ссылкой", 1, "no_first_link")
@update_command_info("/need_decode", "Нужно ли декодировать сообщения в чате.", 1, "need_decode")
@update_command_info("/save_last_message_date", "Сохранять ли время последнего сообщения в чате", 1,
                     "save_last_message_date")
@update_command_info("/add_skynet_img",
                     "Добавить пользователей в пользователи img. запуск с параметрами "
                     "/add_skynet_admin @user1 @user2 итд")
@update_command_info("/del_skynet_admin",
                     "Убрать пользователей из админов скайнета. запуск с параметрами "
                     "/del_skynet_admin @user1 @user2 итд")
@update_command_info("/add_skynet_admin",
                     "Добавить пользователей в админы скайнета. запуск с параметрами "
                     "/add_skynet_admin @user1 @user2 итд")
@update_command_info("/show_skynet_admin", "Показать админов скайнета")
@update_command_info("/notify_join_request",
                     "Оповещать о новом участнике, требующем подтверждения для присоединения. "
                     "Если вторым параметром будет группа в виде -100123456 то оповещать будет в эту группу", 2,
                     "notify_join")
@update_command_info("/notify_message",
                     "Оповещать о новом сообщении в определенный чат"
                     "Чат указываем в виде -100123456 для обычного чата или -100123456:12345 для чата с топиками", 2,
                     "notify_message")
@update_command_info("/join_request_captcha",
                     "Шлет пользователю капчу для подтверждения его человечности. "
                     "Работает только совместно с /notify_join_request")
@update_command_info("/auto_all", "Автоматически добавлять пользователей в /all при входе", 1, "auto_all")
@update_command_info("/set_captcha", "Включает\Выключает капчу", 1, "captcha")
@router.message(Command(commands=list(commands_info.keys())))
async def universal_command_handler(message: Message, bot: Bot):
    command = message.text.lower().split()[0][1:]
    command_arg = message.text.lower().split()[1] if len(message.text.lower().split()) > 1 else None
    command_info = commands_info[command]
    action_type = command_info[2]
    admin_check = command_info[3]

    if action_type == "ignore":
        await message.reply("Technical command. Ignore it.")
        return

    if admin_check == "skynet_admin" and not is_skynet_admin(message):
        await message.reply("You are not my admin.")
        return
    elif admin_check == "admin" and not await is_admin(message):
        await message.reply("You are not admin.")
        return

    if action_type == "toggle_chat" and command_arg and len(command_arg) > 5:
        dest_chat = command_arg.split(":")[0]
        dest_admin = await is_admin(message, dest_chat)
        if not dest_admin:
            await message.reply("Bad target chat. Or you are not admin.")
            return

    await bot.set_message_reaction(chat_id=message.chat.id, message_id=message.message_id,
                                   reaction=[ReactionTypeEmoji(emoji='👀')])

    if action_type in ["add_list", "del_list", "show_list"]:
        await list_command_handler(message, command_info)
    else:  # toggle
        await handle_command(message, command_info)


async def handle_command(message: Message, command_info):
    chat_id = message.chat.id
    global_data_field = command_info[0]
    db_value_type = command_info[1]

    command_args = message.text.split()[1:]  # Список аргументов после команды

    if chat_id in global_data_field:
        if isinstance(global_data_field, dict):
            global_data_field.pop(chat_id)
        else:
            global_data_field.remove(chat_id)
        await global_data.mongo_config.save_bot_value(chat_id, db_value_type, None)
        info_message = await message.reply('Removed')
    else:
        value_to_set = command_args[0] if command_args else '1'
        if isinstance(global_data_field, dict):
            global_data_field[chat_id] = value_to_set
        else:
            global_data_field.append(chat_id)

        await global_data.mongo_config.save_bot_value(chat_id, db_value_type, value_to_set)
        info_message = await message.reply('Added')

    await cmd_sleep_and_delete(info_message, 5)

    with suppress(TelegramBadRequest):
        await asyncio.sleep(1)
        await message.delete()


async def list_command_handler(message: Message, command_info):
    global_data_field = command_info[0]
    db_value_type = command_info[1]
    action_type = command_info[2]

    command_args = message.text.lower().split()[1:]  # аргументы после команды

    if action_type == "add_list":
        if not command_args:
            await message.reply("Необходимо указать аргументы.")
        else:
            global_data_field.extend(command_args)
            await global_data.mongo_config.save_bot_value(0, db_value_type, json.dumps(global_data_field))
            await message.reply(f'Added: {" ".join(command_args)}')

    elif action_type == "del_list":
        if not command_args:
            await message.reply("Необходимо указать аргументы.")
        else:
            for arg in command_args:
                if arg in global_data_field:
                    global_data_field.remove(arg)
            await global_data.mongo_config.save_bot_value(0, db_value_type, json.dumps(global_data_field))
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

    await message.reply("Готово 1")

    result = await check_consul_mtla_chats(message.bot)

    if result:
        await message.reply('\n'.join(result))

    await message.reply("Готово 2")


# @rate_limit(5, 'test')
# @router.message(Command(commands=["test"]))
# async def cmd_test(message: Message, state: FSMContext):
#     await state.update_data(state_my_test=1)
#     await message.reply('test')


async def cmd_kill(bot: Bot):
    j = []
    for item in j:
        try:
            print(int(item['actor_id']))
            await bot.ban_chat_member(chat_id=-1001413354948, user_id=int(item['actor_id']))
            await asyncio.sleep(0.1)  # https://t.me/MTL_city -1001536819420
        except Exception as ex:
            print(ex)


@router.message(Command(commands=["topic"]))
async def cmd_create_topic(message: Message):
    # Проверяем, является ли пользователь администратором
    if not await is_admin(message):
        await message.reply("You are not an admin.")
        return

    # Проверяем, включены ли топики в чате
    if not message.chat.is_forum:
        await message.reply("Topics are not enabled in this chat.")
        return

    # Проверяем правильность формата команды
    command_parts = message.text.split(maxsplit=2)
    if len(command_parts) != 3:
        await message.reply("Incorrect command format. Use: /topic 🔵 Topic Name")
        return

    emoji, topic_name = command_parts[1], command_parts[2]

    # Создаем новый топик
    try:
        new_topic = await message.bot.create_forum_topic(name=topic_name, icon_custom_emoji_id=emoji,
                                                         chat_id=message.chat.id)
        await message.reply(f"New topic '{topic_name}' created successfully with ID: {new_topic.message_thread_id}")
    except TelegramBadRequest as e:
        if "CHAT_NOT_MODIFIED" in str(e):
            await message.reply("Failed to create topic. Make sure the emoji is valid and the topic name is unique.")
        else:
            await message.reply(f"An error occurred while creating the topic: {str(e)}")


@router.message(Command(commands=["eurmtl"]))
@router.message(CommandStart(deep_link=True, magic=F.args == 'eurmtl'), F.chat.type == "private")
async def cmd_eurmtl(message: Message):
    url1 = LoginUrl(url='https://eurmtl.me/authorize')
    url2 = LoginUrl(url='https://eurmtl.me/tables/authorize')
    await message.answer("Click the button below to log in EURMTL.me:", reply_markup=InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Main", login_url=url1)],
            [InlineKeyboardButton(text="Tables", login_url=url2)],
        ]
    ))


@router.message(Command(commands=["update_chats_info"]))
async def cmd_chats_info(message: Message):
    if not is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return
    await message.answer(text="Обновление информации о чатах...")
    for chat_id in [MTLChats.DistributedGroup, -1001892843127]:
        await global_data.mongo_config.update_chat_info(chat_id, await get_group_members(chat_id))
    await message.answer(text="Обновление информации о чатах... Done.")


@router.message(Command(commands=["delete_dead_members"]))
async def cmd_delete_dead_members(message: Message, state: FSMContext):
    if not await is_admin(message):
        await message.reply('You are not admin.')
        return

    parts = message.text.split()

    if len(parts) != 2:
        await message.reply("Please provide a chat ID or username. "
                            "Usage: /delete_dead_members -100xxxxxxxxx"
                            "or /delete_dead_members @username")
        return

    chat_id = parts[1]

    if not ((chat_id.startswith("-100") and chat_id[4:].isdigit()) or chat_id.startswith("@")):
        await message.reply(
            "Invalid chat ID format. It should start with -100 followed by numbers or @ followed by the channel username.")
        return

    if chat_id.startswith("@"):
        try:
            chat = await message.bot.get_chat(chat_id)
            chat_id = chat.id
        except TelegramBadRequest:
            await message.reply("Unable to find the chat. Make sure the bot is a member of the channel/group.")
            return
    else:
        chat_id = int(chat_id)

    if not await is_admin(message, chat_id=chat_id):
        await message.reply(f"You are not an admin of the chat {chat_id}.")
        return

    await message.reply("Starting to remove deleted users. This may take some time...")
    try:
        count = await remove_deleted_users(chat_id)
        await message.reply(f"Finished removing deleted users. \n Total deleted users: {count}")
    except Exception as e:
        logger.error(f"Error in cmd_delete_dead_members: {e}")
        await message.reply(f"An error occurred while removing deleted users: {str(e)}")


@router.my_chat_member()
async def on_my_chat_member(update: ChatMemberUpdated, bot: Bot):
    chat = update.chat
    old_status = update.old_chat_member.status
    new_status = update.new_chat_member.status

    if old_status != new_status:
        if new_status == ChatMemberStatus.MEMBER:
            logger.info(f"Bot was added to chat {chat.id}")
            if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
                await bot.send_message(chat.id, "Thanks for adding me to this chat!")

        elif new_status == ChatMemberStatus.LEFT:
            logger.info(f"Bot was removed from chat {chat.id}")

        elif new_status == ChatMemberStatus.ADMINISTRATOR:
            logger.info(f"Bot's permissions were updated in chat {chat.id}")
            if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
                await bot.send_message(chat.id, "Thanks for making me an admin!")

        elif new_status == ChatMemberStatus.RESTRICTED:
            logger.warning(f"Bot's permissions were restricted in chat {chat.id}")

        elif new_status == ChatMemberStatus.KICKED:
            logger.warning(f"Bot's permissions were kicked in chat {chat.id}")

        else:
            logger.info(f"Bot status changed in chat {chat.id} from {old_status} to {new_status}")

    # You can add more specific logic based on your needs

    # For example, you might want to update some global data:
    # if new_status == ChatMemberStatus.MEMBER or new_status == ChatMemberStatus.ADMINISTRATOR:
    #     if chat.id not in global_data.active_chats:
    #         global_data.active_chats.append(chat.id)
    # elif new_status == ChatMemberStatus.LEFT:
    #     if chat.id in global_data.active_chats:
    #         global_data.active_chats.remove(chat.id)


@router.message(F.migrate_to_chat_id)
async def on_migrate(message: Message, bot: Bot):
    old_chat_id = message.chat.id
    new_chat_id = message.migrate_to_chat_id
    logger.info(f"Chat {old_chat_id} migrated to {new_chat_id}")
    await message.bot.send_message(chat_id=new_chat_id,
                                   text=f"Chat {old_chat_id} migrated to {new_chat_id}")


@update_command_info("/all", "тегнуть всех пользователей. работает зависимо от чата. и только в рабочих чатах")
@router.message(Command(commands=["all"]))
async def cmd_all(message: Message, session: Session):
    # [GroupMember(user_id=191153115, username='SomeoneAny', full_name='Антон Ехин', is_admin=True, is_bot=False), GroupMember(user_id=84131737, username='itolstov', full_name='Igor Tolstov', is_admin=True, is_bot=False), GroupMember(user_id=2134695152, username='myMTLbot', full_name='SkyNet', is_admin=True, is_bot=True), GroupMember(user_id=1365715447, username='DimaBuilder', full_name='Dmitriy Sergeevich', is_admin=False, is_bot=False), GroupMember(user_id=330418643, username='poutru', full_name='Valerij Utrosin', is_admin=True, is_bot=False), GroupMember(user_id=6613318, username='maximsivokon', full_name='Maxim V. Sivokoñ (@BadFoxLab)', is_admin=False, is_bot=False), GroupMember(user_id=821795233, username='bushnew', full_name='alex', is_admin=False, is_bot=False), GroupMember(user_id=7394698, username='KorbVV', full_name='Victor Korb', is_admin=True, is_bot=False), GroupMember(user_id=601751247, username='atkachuk', full_name='ALEKSEI T.', is_admin=True, is_bot=False), GroupMember(user_id=201496385, username='LisozTech', full_name='Lisoz Tech', is_admin=False, is_bot=False), GroupMember(user_id=5671789703, username='mtl_accelerator_bot', full_name='MABIZ', is_admin=True, is_bot=True), GroupMember(user_id=1005904185, username='lena_masterica', full_name='Elena Smirnova', is_admin=False, is_bot=False), GroupMember(user_id=1500022467, username='lss_me', full_name='Henrik Crna Gora(Montelibero)', is_admin=False, is_bot=False), GroupMember(user_id=988654481, username='Ageris', full_name='Agéris', is_admin=False, is_bot=False), GroupMember(user_id=376413542, username='ayr_san', full_name='Fox Malder', is_admin=False, is_bot=False), GroupMember(user_id=874520, username='AduchiMergen', full_name='☮️🦄 Artem Kanarev', is_admin=False, is_bot=False), GroupMember(user_id=24275128, username='petrov1c', full_name='dima petrov', is_admin=True, is_bot=False), GroupMember(user_id=1335526, username='Serregan', full_name='Serregan', is_admin=False, is_bot=False), GroupMember(user_id=129337418, username='AjayFSM', full_name='Flying Spaghetti Monster', is_admin=True, is_bot=False), GroupMember(user_id=62397851, username='sondreb', full_name='Sondre Bjellås', is_admin=False, is_bot=False), GroupMember(user_id=224228995, username='GoodJobMaster', full_name='Damir', is_admin=False, is_bot=False), GroupMember(user_id=636707173, username='Hthew', full_name='Htheu', is_admin=False, is_bot=False)]
    user_list = await get_group_members(message.chat.id)

    members = [f'@{user.username}' for user in user_list if not user.is_bot and user.username]
    await message.reply(' '.join(members))


@update_command_info("/calc", "Посчитать сообщения от ответного")
@router.message(Command(commands=["calc"]))
async def cmd_calc(message: Message):
    if not message.reply_to_message:
        await message.reply("This command must be used in reply to a message.")
        return

    current_message_id = message.message_id
    replied_message_id = message.reply_to_message.message_id
    difference = current_message_id - replied_message_id

    with suppress(TelegramBadRequest):
        await message.reply_to_message.reply(f"This message was {difference} messages ago.")
        await message.delete()


@router.message(Command(commands=["test2"]))
async def cmd_test(message: Message, session: Session):
    pass


if __name__ == "__main__":
    tmp_bot = Bot(token=config.bot_token.get_secret_value())
    a = asyncio.run(check_membership(tmp_bot, MTLChats.MonteliberoChanel, int(6822818006)))
    print(a)
