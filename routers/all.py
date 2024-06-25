import json
from copy import copy
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.orm import Session
from utils.aiogram_utils import is_admin
from utils.global_data import MTLChats, global_data, BotValueTypes, update_command_info

router = Router()



@update_command_info("/all", "тегнуть всех пользователей. работает зависимо от чата. и только в рабочих чатах")
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
        members = json.loads(await global_data.json_config.load_bot_value(message.chat.id, BotValueTypes.All, '[]'))
        if members:
            await message.reply(' '.join(members))
        else:
            await message.reply('/all не настроен, используйте /add_all и /del_all')


@update_command_info("/add_all", "Добавить пользователей в /all. запуск с параметрами /add_all @user1 @user2 итд")
@router.message(Command(commands=["add_all"]))
async def cmd_add_all(message: Message, session:Session):
    if not await is_admin(message):
        await message.reply('You are not admin.')
        return False

    if len(message.text.split()) > 1:
        members = json.loads(await global_data.json_config.load_bot_value(message.chat.id, BotValueTypes.All, '[]'))
        arg = message.text.split()
        members.extend(arg[1:])
        await global_data.json_config.save_bot_value(message.chat.id, BotValueTypes.All, json.dumps(members))

        await message.reply('Done')
    else:
        await message.reply('не указаны параметры кого добавить')


@update_command_info("/del_all", "Убрать пользователей в /all. запуск с параметрами /del_all @user1 @user2 итд")
@router.message(Command(commands=["del_all"]))
async def cmd_del_all(message: Message, session: Session):
    if not await is_admin(message):
        await message.reply('You are not admin.')
        return False

    if len(message.text.split()) > 1:
        members = json.loads(await global_data.json_config.load_bot_value(message.chat.id, BotValueTypes.All, '[]'))
        arg = message.text.split()[1:]
        for member in arg:
            if member in members:
                members.remove(member)
        await global_data.json_config.save_bot_value(message.chat.id, BotValueTypes.All, json.dumps(members))
        await message.reply('Done')
    else:
        await message.reply('не указаны параметры кого добавить')


@update_command_info("/auto_all", "Автоматически добавлять пользователей в /all при входе")
@router.message(Command(commands=["auto_all"]))
async def msg_save_all(message: Message, session:Session):
    if not await is_admin(message):
        await message.reply('You are not admin.')
        return False

    if message.chat.id in global_data.auto_all:
        global_data.auto_all.remove(message.chat.id)
        await global_data.json_config.save_bot_value(message.chat.id, BotValueTypes.AutoAll, None)
        await message.reply('Removed')
    else:
        global_data.auto_all.append(message.chat.id)
        await global_data.json_config.save_bot_value(message.chat.id, BotValueTypes.AutoAll, 1)
        await message.reply('Added')
