import json
from copy import copy

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.orm import Session

from db.requests import cmd_load_bot_value, cmd_save_bot_value
from utils.aiogram_utils import is_admin
from utils.global_data import MTLChats, global_data, BotValueTypes

router = Router()


@router.message(Command(commands=["all"]))
async def cmd_all(message: Message, session: Session):
    if message.chat.id == MTLChats.SignGroup:
        members = copy(global_data.votes)
        members.remove("NEED")
        await message.reply(' '.join(members))
    # elif message.chat.id == MTLChats.Testdata = await state.get_data():
    #    await message.reply('@SomeoneAny @itolstov')
    # elif message.chat.id == MTLChats.DistributedGroupdata = await state.get_data():
    #    result = cmd_check_donate_list()
    #    await message.reply(' '.join(result))
    else:
        members = json.loads(cmd_load_bot_value(session, message.chat.id, BotValueTypes.All, '[]'))
        if members:
            await message.reply(' '.join(members))
        else:
            await message.reply('/all не настроен, используйте /add_all и /del_all')


@router.message(Command(commands=["add_all"]))
async def cmd_add_all(message: Message, session:Session):
    if not await is_admin(message):
        await message.reply('You are not admin.')
        return False

    if len(message.text.split()) > 1:
        members = json.loads(cmd_load_bot_value(session, message.chat.id, BotValueTypes.All, '[]'))
        arg = message.text.split()
        members.extend(arg[1:])
        cmd_save_bot_value(session, message.chat.id, BotValueTypes.All, json.dumps(members))

        await message.reply('Done')
    else:
        await message.reply('не указаны параметры кого добавить')


@router.message(Command(commands=["del_all"]))
async def cmd_del_all(message: Message, session: Session):
    if not await is_admin(message):
        await message.reply('You are not admin.')
        return False

    if len(message.text.split()) > 1:
        members = json.loads(cmd_load_bot_value(session, message.chat.id, BotValueTypes.All, '[]'))
        arg = message.text.split()[1:]
        for member in arg:
            if member in members:
                members.remove(member)
        cmd_save_bot_value(session, message.chat.id, BotValueTypes.All, json.dumps(members))
        await message.reply('Done')
    else:
        await message.reply('не указаны параметры кого добавить')


@router.message(Command(commands=["auto_all"]))
async def msg_save_all(message: Message, session:Session):
    if not await is_admin(message):
        await message.reply('You are not admin.')
        return False

    if message.chat.id in global_data.auto_all:
        global_data.auto_all.remove(message.chat.id)
        cmd_save_bot_value(session, message.chat.id, BotValueTypes.AutoAll, None)
        await message.reply('Removed')
    else:
        global_data.auto_all.append(message.chat.id)
        cmd_save_bot_value(session, message.chat.id, BotValueTypes.AutoAll, 1)
        await message.reply('Added')
