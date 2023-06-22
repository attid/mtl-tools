import json
import os

from aiogram import Router, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, FSInputFile
from sqlalchemy.orm import Session

from db.requests import cmd_save_bot_value
from utils.global_data import MTLChats, is_skynet_admin, global_data, BotValueTypes
from utils.stellar_utils import send_by_list

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
        cmd_save_bot_value(session, 0, BotValueTypes.SkynetAdmins, json.dumps(global_data.skynet_admins))

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
        cmd_save_bot_value(session, 0, BotValueTypes.SkynetAdmins, json.dumps(global_data.skynet_admins))
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
