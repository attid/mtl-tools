import asyncio
import base64
import hashlib
import json
import os
import re
import uuid
from contextlib import suppress
from datetime import datetime

from aiogram import Router, Bot, F
from aiogram.enums import ChatType, ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import (Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton,
                           LoginUrl, User)
from loguru import logger
from sqlalchemy.orm import Session

from db.repositories import MessageRepository
from other.aiogram_tools import is_admin
from other.grist_tools import grist_manager, MTLGrist
from other.open_ai_tools import talk_get_summary
from other.global_data import MTLChats, is_skynet_admin, global_data, BotValueTypes, update_command_info
from other.gspread_tools import gs_find_user, gs_get_all_mtlap, gs_get_update_mtlap_skynet_row
from other.mtl_tools import check_consul_mtla_chats
from other.pyro_tools import get_group_members, pyro_test
from other.stellar_tools import send_by_list

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
async def cmd_log(message: Message):
    if not is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return False
    await cmd_send_file(message, 'skynet.log')


@router.message(Command(commands=["ping_piro"]))
async def cmd_ping_piro(message: Message, app_context=None):
    if not is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return False
    if app_context:
        await app_context.group_service.ping_piro()
    else:
        await pyro_test()


async def cmd_send_file(message: Message, filename):
    try:
        if not os.path.isfile(filename):
            await message.reply(f'Файл {filename} не найден')
            return
        
        if os.path.getsize(filename) == 0:
            await message.reply(f'Файл {filename} пуст')
            return
            
        await message.reply_document(FSInputFile(filename))
    except Exception as e:
        logger.error(f"Ошибка при отправке файла {filename}: {e}")
        await message.reply(f'Произошла ошибка при отправке файла {filename}')


@router.message(Command(commands=["summary"]))
async def cmd_get_summary(message: Message, session: Session):
    if not is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return False

    if message.chat.id not in global_data.listen:
        await message.reply('No messages 1')
        return

    try:
        data = MessageRepository(session).get_messages_without_summary(chat_id=message.chat.id,
                                             thread_id=message.message_thread_id if message.is_topic_message else None)

        if not data:
            await message.reply('Нет новых сообщений для обработки')
            return

        text = ''
        summary = MessageRepository(session).add_summary(text=text)
        session.flush()

        try:
            for record in data:
                new_text = text + f'{record.username}: {record.text} \n\n'
                if len(new_text) < 16000:
                    text = new_text
                    record.summary_id = summary.id
                    session.flush()
                else:
                    summary.text = await talk_get_summary(text)
                    session.flush()
                    summary = MessageRepository(session).add_summary(text='')
                    session.flush()
                    text = record.username + ': ' + record.text + '\n\n'
                    record.summary_id = summary.id
                    session.flush()
            
            if text:  # Обработка оставшегося текста
                summary.text = await talk_get_summary(text)
                session.flush()

            summaries = MessageRepository(session).get_summary(chat_id=message.chat.id,
                                     thread_id=message.message_thread_id if message.is_topic_message else None)

            if not summaries:
                await message.reply('Не удалось получить сводку сообщений')
                return

            for record in summaries:
                if record.text:
                    await message.reply(record.text[:4000])
                else:
                    logger.warning(f"Empty summary text for record {record.id}")

            session.commit()

        except Exception as e:
            session.rollback()
            logger.error(f"Error processing messages for summary: {e}")
            await message.reply('Произошла ошибка при обработке сообщений')
            return

    except Exception as e:
        logger.error(f"Database error in cmd_get_summary: {e}")
        await message.reply('Произошла ошибка при работе с базой данных')
        return


@router.message(F.document, F.chat.type == ChatType.PRIVATE)
async def cmd_get_sha1(message: Message, bot: Bot):
    document = message.document
    file_data = await bot.download(document)
    file_bytes = file_data.read()

    hasher = hashlib.sha1()
    hasher.update(file_bytes)
    sha1_hash = hasher.hexdigest()
    base64_hash = base64.b64encode(hasher.digest()).decode('utf-8')

    sha256_hasher = hashlib.sha256()
    sha256_hasher.update(file_bytes)
    sha256_hash = sha256_hasher.hexdigest()

    await message.reply(f'SHA-1: <code>{sha1_hash}</code>\n'
                        f'BASE64: <code>{base64_hash}</code>\n\n'
                        f'SHA-256: <code>{sha256_hash}</code>')


@router.message(Command(commands=["sha256"]))
async def cmd_sha256(message: Message):
    sha256_hasher = hashlib.sha256()
    sha256_hasher.update(message.text[8:].encode('utf-8'))
    sha256_hash = sha256_hasher.hexdigest()
    await message.reply(f'SHA-256: <code>{sha256_hash}</code>')


@update_command_info("/sync", "Синхронизирует сообщение в чате с постом в канале")
@router.message(Command(commands=["sync"]))
async def cmd_sync_post(message: Message, bot: Bot):
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
async def cmd_edited_channel_post(message: Message, bot: Bot):
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


@router.message(Command(commands=["grist"]))
@router.message(CommandStart(deep_link=True, magic=F.args == 'grist'), F.chat.type == "private")
async def cmd_grist(message: Message, app_context=None):
    user_id = message.from_user.id
    try:
        if app_context:
            access_records = await app_context.grist_service.load_table_data(MTLGrist.GRIST_access)
        else:
            access_records = await grist_manager.load_table_data(MTLGrist.GRIST_access)
            
        for r in access_records:
            print(r)

        user_record = next((r for r in access_records if r.get('user_id') == user_id), None)

        if not user_record:
            await message.answer("❌ У вас нет доступа к Grist.")
            return

        new_key = str(uuid.uuid4())

        update_data = {
            "records": [{
                "id": user_record['id'],
                "fields": {
                    "key": new_key,
                    "dt_update": datetime.now().isoformat()
                }
            }]
        }
        
        if app_context:
            await app_context.grist_service.patch_data(MTLGrist.GRIST_access, update_data)
        else:
            await grist_manager.patch_data(MTLGrist.GRIST_access, update_data)
        
        await message.answer(f"✅ Новый ключ доступа:\n<code>{new_key}</code>")

    except Exception as e:
        logger.error(f"Grist access error: {e}")
        await message.answer("⚠️ Произошла ошибка при обработке запроса. Попробуйте позже.")


@router.message(Command(commands=["update_mtlap"]))
async def cmd_update_mtlap(message: Message, bot: Bot, app_context=None):
    if not is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return

    if app_context:
        data = await app_context.gspread_service.get_all_mtlap()
    else:
        data = await gs_get_all_mtlap()

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
        except Exception:
            results.append(False)
        await asyncio.sleep(0.1)
    
    if app_context:
        await app_context.gspread_service.get_update_mtlap_skynet_row(results)
    else:
        await gs_get_update_mtlap_skynet_row(results)

    await message.reply("Готово 1")
    
    if app_context:
        result = await app_context.mtl_service.check_consul_mtla_chats(message.bot)
    else:
        result = await check_consul_mtla_chats(message.bot)

    if result:
        await message.reply('\n'.join(result))

    await message.reply("Готово 2")


@router.message(Command(commands=["update_chats_info"]))
async def cmd_chats_info(message: Message, app_context=None):
    if not is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return
    await message.answer(text="Обновление информации о чатах...")
    for chat_id in [MTLChats.DistributedGroup, -1001892843127]:
        if app_context:
            members = await app_context.group_service.get_members(chat_id)
        else:
            members = await get_group_members(chat_id)
        await global_data.mongo_config.update_chat_info(chat_id, members)
    await message.answer(text="Обновление информации о чатах... Done.")


async def check_membership(bot: Bot, chat_id: str, user_id: int) -> (bool, User):
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        is_member = member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR]
        return is_member, member.user

    except TelegramBadRequest:
        return False, None


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


@router.message(Command(commands=["get_info"]))
@router.message(Command(re.compile(r"get_info_(\d+)")))
async def cmd_get_info(message: Message, bot: Bot, app_context=None):
    if not is_skynet_admin(message):
        if message.chat.id != MTLChats.HelperChat:
            await message.reply('You are not my admin.')
            return

    command_args = (message.text or '').split()
    if not command_args:
        await message.reply('Пришлите числовой ID')
        return

    command_name = command_args[0].split('@')[0].lstrip('/')
    if command_name == "get_info":
        if len(command_args) < 2:
            await message.reply('Пришлите числовой ID')
            return
        raw_id = command_args[1].strip()
        if raw_id.upper().startswith("#ID"):
            raw_id = raw_id[3:]
        if not raw_id.isdigit():
            await message.reply('ID должен быть числом.')
            return
        user_id = raw_id
    else:
        match = re.match(r"get_info_(\d+)", command_name)
        if not match:
            await message.reply('Некорректная команда. Используйте /get_info <ID>')
            return
        user_id = match.group(1)

    messages = []

    chat_list = (
        (MTLChats.MonteliberoChanel, "канал Montelibero ru"),
        (MTLChats.MTLAAgoraGroup, "MTLAAgoraGroup"),
        (-1001429770534, "chat Montelibero ru"),
    )

    for chat_id, chat_name in chat_list:
        is_member, user = await check_membership(bot, chat_id, int(user_id))
        if is_member:
            if user and user.username:
                messages.append(f"Пользователь @{user.username} подписан на {chat_name}")
            else:
                messages.append(f"Пользователь подписан на {chat_name}")
                messages.append("<b>!Внимание: нет юзернейма</b>")
        else:
            messages.append(f"Пользователь не подписан на {chat_name}")
    
    #messages.extend(await gs_find_user(user_id))
    # if app_context:
    #      messages.extend(await app_context.gspread_service.find_user(user_id))
    # else:
    #      messages.extend(await gs_find_user(user_id))
          
    messages.append(f"Я больше не умею проверять на айдропы, гуглшит не работает")

    await message.reply('\n'.join(messages))


def register_handlers(dp, bot):
    dp.include_router(router)
    logger.info('router admin_system was loaded')
