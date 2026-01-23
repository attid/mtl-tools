import asyncio
import json
from contextlib import suppress

from aiogram import Router, Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.types import (Message, ReactionTypeEmoji)
from loguru import logger

from other.config_reader import config
from other.global_data import MTLChats, BotValueTypes, update_command_info, global_data

router = Router()

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
    "set_moderate": (global_data.moderate, BotValueTypes.Moderate, "toggle", "admin", 1),
    "set_entry_channel": (global_data.entry_channel, BotValueTypes.EntryChannel, "toggle_entry_channel", "admin", 1),

    "add_skynet_img": (global_data.skynet_img, BotValueTypes.SkynetImg, "add_list", "skynet_admin", 3),
    "del_skynet_img": (global_data.skynet_img, BotValueTypes.SkynetImg, "del_list", "skynet_admin", 0),
    "show_skynet_img": (global_data.skynet_img, BotValueTypes.SkynetImg, "show_list", "skynet_admin", 0),
    "add_skynet_admin": (global_data.skynet_admins, BotValueTypes.SkynetAdmins, "add_list", "skynet_admin", 3),
    "del_skynet_admin": (global_data.skynet_admins, BotValueTypes.SkynetAdmins, "del_list", "skynet_admin", 0),
    "show_skynet_admin": (global_data.skynet_admins, BotValueTypes.SkynetAdmins, "show_list", "skynet_admin", 0),
    "add_topic_admin": (global_data.topic_admins, BotValueTypes.TopicAdmins, "add_list_topic", "admin", 3),
    "del_topic_admin": (global_data.topic_admins, BotValueTypes.TopicAdmins, "del_list_topic", "admin", 0),
    "show_topic_admin": (global_data.topic_admins, BotValueTypes.TopicAdmins, "show_list_topic", "admin", 0),
}


async def command_config_loads():
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
    global_data.topic_mute = json.loads(
        await global_data.mongo_config.load_bot_value(0, BotValueTypes.TopicMutes, '{}'))

    global_data.welcome_messages = await global_data.mongo_config.get_chat_dict_by_key(BotValueTypes.WelcomeMessage)
    global_data.welcome_button = await global_data.mongo_config.get_chat_dict_by_key(BotValueTypes.WelcomeButton)
    global_data.admins = await global_data.mongo_config.get_chat_dict_by_key(BotValueTypes.Admins, True)
    global_data.alert_me = await global_data.mongo_config.get_chat_dict_by_key(BotValueTypes.AlertMe, True)
    global_data.sync = await global_data.mongo_config.get_chat_dict_by_key(BotValueTypes.Sync, True)

    logger.info('finished command_config_loads task')



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
@update_command_info("/add_topic_admin", "Добавить админов топика. Использование: /add_topic_admin @user1 @user2")
@update_command_info("/del_topic_admin", "Удалить админов топика. Использование: /del_topic_admin @user1 @user2")
@update_command_info("/show_topic_admin", "Показать админов топика")
@update_command_info("/notify_join_request",
                     "Оповещать о новом участнике, требующем подтверждения для присоединения. "
                     "Если вторым параметром будет группа в виде -100123456 то оповещать будет в эту группу", 2,
                     "notify_join")
@update_command_info("/notify_message",
                     "Оповещать о новом сообщении в определенный чат"
                     "Чат указываем в виде -100123456 для обычного чата или -100123456:12345 для чата с топиками", 2,
                     "notify_message")
@update_command_info("/set_entry_channel",
                     "Ограничение входа только для подписчиков канала. Использование: /set_entry_channel -100123456",
                     2, "entry_channel")
@update_command_info("/join_request_captcha",
                     "Шлет пользователю капчу для подтверждения его человечности. "
                     "Работает только совместно с /notify_join_request")
@update_command_info("/auto_all", "Автоматически добавлять пользователей в /all при входе", 1, "auto_all")
@update_command_info("/set_captcha", "Включает\Выключает капчу", 1, "captcha")
@update_command_info("/set_moderate", "Включает\Выключает режим модерации по топикам/topic", 1, "moderate")
@router.message(Command(commands=list(commands_info.keys())))
async def universal_command_handler(message: Message, bot: Bot, app_context=None):
    command = message.text.lower().split()[0][1:]
    command_arg = message.text.lower().split()[1] if len(message.text.lower().split()) > 1 else None
    command_info = commands_info[command]
    action_type = command_info[2]
    admin_check = command_info[3]

    if action_type == "ignore":
        await message.reply("Technical command. Ignore it.")
        return

    if admin_check == "skynet_admin" and not app_context.utils_service.is_skynet_admin(message):
        await message.reply("You are not my admin.")
        return
    elif admin_check == "admin":
        if not await app_context.utils_service.is_admin(message):
            await message.reply("You are not admin.")
            return

    if action_type == "toggle_chat" and command_arg and len(command_arg) > 5:
        dest_chat = command_arg.split(":")[0]
        if not await app_context.utils_service.is_admin(message, dest_chat):
            await message.reply("Bad target chat. Or you are not admin.")
            return

    await bot.set_message_reaction(chat_id=message.chat.id, message_id=message.message_id,
                                   reaction=[ReactionTypeEmoji(emoji='👀')])

    if action_type in ["add_list", "del_list", "show_list"]:
        await list_command_handler(message, command_info, app_context=app_context)

    if action_type in ["add_list_topic", "del_list_topic", "show_list_topic"]:
        if not message.message_thread_id:
            await message.reply("Run this command in thread.")
            return
        await list_command_handler_topic(message, command_info, app_context=app_context)

    if action_type == "toggle_chat":
        await handle_command(message, command_info, app_context=app_context)
        return

    if action_type == "toggle_entry_channel":
        await handle_entry_channel_toggle(message, command_info, app_context=app_context)
        return

    if action_type == "toggle":
        await handle_command(message, command_info, app_context=app_context)


async def handle_command(message: Message, command_info, app_context=None):
    chat_id = message.chat.id
    global_data_field = command_info[0]
    db_value_type = command_info[1]

    command_args = message.text.split()[1:]  # Список аргументов после команды

    if chat_id in global_data_field:
        if isinstance(global_data_field, dict):
            global_data_field.pop(chat_id)
        else:
            global_data_field.remove(chat_id)
            
        await app_context.config_service.save_bot_value(chat_id, db_value_type, None)
            
        info_message = await message.reply('Removed')
    else:
        value_to_set = command_args[0] if command_args else '1'
        if isinstance(global_data_field, dict):
            global_data_field[chat_id] = value_to_set
        else:
            global_data_field.append(chat_id)

        await app_context.config_service.save_bot_value(chat_id, db_value_type, value_to_set)
            
        info_message = await message.reply('Added')

    await app_context.utils_service.sleep_and_delete(info_message, 5)

    with suppress(TelegramBadRequest):
        await asyncio.sleep(1)
        await message.delete()


async def handle_entry_channel_toggle(message: Message, command_info, app_context=None):
    chat_id = message.chat.id
    global_data_field = command_info[0]

    if chat_id not in global_data_field:
        command_args = message.text.split()[1:]
        if not command_args:
            info_message = await message.reply('Необходимо указать канал или чат в формате -100123456 или @channel.')
            await app_context.utils_service.sleep_and_delete(info_message, 10)
            with suppress(TelegramBadRequest):
                await asyncio.sleep(1)
                await message.delete()
            return

    await handle_command(message, command_info, app_context=app_context)


async def enforce_entry_channel(bot: Bot, chat_id: int, user_id: int, required_channel: str, app_context=None) -> tuple[bool, bool]:
    is_member, _ = await app_context.group_service.check_membership(bot, required_channel, user_id)
        
    if is_member:
        return True, False

    try:
        await bot.unban_chat_member(chat_id, user_id)
        await asyncio.sleep(0.2)
        return False, True
    except (TelegramBadRequest, TelegramForbiddenError) as exc:
        logger.warning(f'enforce_entry_channel failed for user {user_id} in chat {chat_id}: {exc}')
        return False, False


async def run_entry_channel_check(bot: Bot, chat_id: int, app_context=None) -> tuple[int, int]:
    required_channel = global_data.entry_channel.get(chat_id)
    if not required_channel:
        raise ValueError('entry_channel setting is not enabled for this chat')

    members = await app_context.group_service.get_members(chat_id)

    checked_count = 0
    action_count = 0

    for member in members:
        if member.is_bot or member.is_admin:
            continue

        checked_count += 1

        membership_ok, action_applied = await enforce_entry_channel(bot, chat_id, member.user_id, required_channel, app_context=app_context)
        if membership_ok:
            await asyncio.sleep(0.1)
            continue

        if action_applied:
            action_count += 1

        await asyncio.sleep(0.5)

    return checked_count, action_count


async def list_command_handler(message: Message, command_info, app_context=None):
    global_data_field = command_info[0]
    db_value_type = command_info[1]
    action_type = command_info[2]

    command_args = message.text.lower().split()[1:]  # аргументы после команды

    if action_type == "add_list":
        if not command_args:
            await message.reply("Необходимо указать аргументы.")
        else:
            global_data_field.extend(command_args)
            await app_context.config_service.save_bot_value(0, db_value_type, json.dumps(global_data_field))
            await message.reply(f'Added: {" ".join(command_args)}')

    elif action_type == "del_list":
        if not command_args:
            await message.reply("Необходимо указать аргументы.")
        else:
            for arg in command_args:
                if arg in global_data_field:
                    global_data_field.remove(arg)
            await app_context.config_service.save_bot_value(0, db_value_type, json.dumps(global_data_field))
            await message.reply(f'Removed: {" ".join(command_args)}')

    elif action_type == "show_list":
        if global_data_field:
            await message.reply(' '.join(global_data_field))
        else:
            await message.reply('The list is empty.')


async def list_command_handler_topic(message: Message, command_info, app_context=None):
    global_data_field = command_info[0]  # will be dict
    db_value_type = command_info[1]
    action_type = command_info[2]

    command_args = message.text.lower().split()[1:]  # аргументы после команды
    chat_thread_key = f"{message.chat.id}-{message.message_thread_id}"

    if action_type == "add_list_topic":
        if not command_args:
            await message.reply("Необходимо указать аргументы.")
        else:
            if chat_thread_key not in global_data_field:
                global_data_field[chat_thread_key] = []
            global_data_field[chat_thread_key].extend(command_args)
            await app_context.config_service.save_bot_value(0, db_value_type, json.dumps(global_data_field))
            await message.reply(f'Added at this thread: {" ".join(command_args)}')

    elif action_type == "del_list_topic":
        if not command_args:
            await message.reply("Необходимо указать аргументы.")
        else:
            if chat_thread_key in global_data_field:
                for arg in command_args:
                    if arg in global_data_field[chat_thread_key]:
                        global_data_field[chat_thread_key].remove(arg)
                await app_context.config_service.save_bot_value(0, db_value_type, json.dumps(global_data_field))
                await message.reply(f'Removed from this thread: {" ".join(command_args)}')
            else:
                await message.reply('This thread has no items in the list.')

    elif action_type == "show_list_topic":
        if chat_thread_key in global_data_field and global_data_field[chat_thread_key]:
            await message.reply(f'Items in this thread: {" ".join(global_data_field[chat_thread_key])}')
        else:
            await message.reply('The list for this thread is empty.')


@router.startup()
async def on_startup():
    asyncio.create_task(command_config_loads())


def register_handlers(dp, bot):
    dp.include_router(router)
    logger.info('router admin was loaded')


if __name__ == "__main__":
    pass
