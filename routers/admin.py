import base64
import hashlib
import json
import os
import re
from aiogram import Router, Bot, F
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, FSInputFile, ChatPermissions
from sqlalchemy.orm import Session
from db.requests import db_save_bot_value, db_get_messages_without_summary, db_add_summary, db_get_summary
from utils.aiogram_utils import is_admin, cmd_delete_later
from utils.dialog import talk_get_summary
from utils.global_data import MTLChats, is_skynet_admin, global_data, BotValueTypes
from utils.gspread_tools import gs_find_user
from utils.stellar_utils import send_by_list
from aiogram.exceptions import TelegramBadRequest

from utils.timedelta import parse_timedelta_from_message

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


async def cmd_send_file(message: Message, filename):
    if os.path.isfile(filename):
        await message.reply_document(FSInputFile(filename))


@router.message(Command(commands=["add_skynet_admin"]))
async def cmd_add_skynet_admin(message: Message, session: Session):
    if not is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return False

    if len(message.text.split()) > 1:
        arg = message.text.split()
        global_data.skynet_admins.extend(arg[1:])
        db_save_bot_value(session, 0, BotValueTypes.SkynetAdmins, json.dumps(global_data.skynet_admins))

        await message.reply('Done')
    else:
        await message.reply('не указаны параметры кого добавить')


@router.message(Command(commands=["del_skynet_admin"]))
async def cmd_del_skynet_admin(message: Message, session: Session):
    if not is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return False

    if len(message.text.split()) > 1:
        arg = message.text.split()
        global_data.skynet_admins.extend(arg[1:])

        arg = message.text.split()
        for member in arg:
            if member in global_data.skynet_admins:
                global_data.skynet_admins.remove(member)
        db_save_bot_value(session, 0, BotValueTypes.SkynetAdmins, json.dumps(global_data.skynet_admins))
        await message.reply('Done')
    else:
        await message.reply('не указаны параметры кого добавить')


@router.message(Command(commands=["show_skynet_admin"]))
async def cmd_show_skynet_admin(message: Message):
    if not is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return False

    await message.reply(' '.join(global_data.skynet_admins))


# @router.message(Command(commands=["save_income_id"]))
# async def cmd_save_income_id(message: Message):
#     if not is_skynet_admin(message):
#         await message.reply('You are not my admin.')
#         return False
#
#     save_income_id_list = global_dict.get('save_income_id', [])
#     if message.chat.id in save_income_id_list:
#         save_income_id_list.remove(message.chat.id)
#         global_dict['save_income_id'] = save_income_id_list
#         global_dict[message.chat.id] = []
#         await message.reply('Removed')
#     else:
#         save_income_id_list.append(message.chat.id)
#         global_dict['save_income_id'] = save_income_id_list
#         await message.reply('Added')
#
#
# @router.message(Command(commands=["show_income_id"]))
# async def cmd_show_income_id(message: Message):
#     if not is_skynet_admin(message):
#         await message.reply('You are not my admin.')
#         return False
#
#     users_id = global_dict.get(message.chat.id, [])
#     await message.reply(str(users_id))
#
#
# @router.message(Command(commands=["delete_income_id"]))
# async def cmd_delete_income_id(message: Message):
#     if not is_skynet_admin(message):
#         await message.reply('You are not my admin.')
#         return False
#
#     users_id = global_dict.get(message.chat.id, [])
#     for user in users_id:
#         await message.chat.kick(user)
#     await message.reply(str(users_id))


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
    if not is_admin(message):
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


@router.message(Command(commands=["full_data"]))
async def cmd_set_listen(message: Message, session: Session):
    if not is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return False

    if message.chat.id in global_data.full_data:
        global_data.full_data.remove(message.chat.id)
        db_save_bot_value(session, message.chat.id, BotValueTypes.FullData, None)
        msg = await message.reply('Removed')
    else:
        global_data.full_data.append(message.chat.id)
        db_save_bot_value(session, message.chat.id, BotValueTypes.FullData, 1)
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
    sha1_hash = hasher.hexdigest()#.encode('utf-8')
    print(sha1_hash, sha1_hash)

    # Encode the bytes to BASE64
    base64_hash = base64.b64encode(hasher.digest()).decode('utf-8')
    print(sha1_hash, base64_hash)

    #sha256
    sha256_hasher = hashlib.sha256()
    sha256_hasher.update(file_bytes)
    sha256_hash = sha256_hasher.hexdigest()

    print(f"SHA-256: {sha256_hash}")


    await message.reply(f'SHA-1: <code>{sha1_hash}</code>\n'
                        f'BASE64: <code>{base64_hash}</code>\n\n'
                        f'SHA-256: <code>{sha256_hash}</code>')
    #hex: 679cd49aec59cf2ccaf843ea4c484975d33dd18a
    #base64: Z5zUmuxZzyzK+EPqTEhJddM90Yo=



@router.message(Command(commands=["s"]))
@router.message(Command(commands=["send_me"]))
async def cmd_get_info(message: Message, bot: Bot):
    if not is_admin(message):
        await message.reply('You are not admin.')
        return

    if message.reply_to_message is None:
        await message.reply('Please send for reply message to get it')
        return

    if message.reply_to_message :
        await bot.send_message(chat_id=message.from_user.id, text=message.reply_to_message.html_text)
