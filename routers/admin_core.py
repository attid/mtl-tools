import asyncio
import json
import re
from contextlib import suppress
from datetime import datetime

import aiohttp
from aiogram import Router, Bot, F
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ChatPermissions, ChatMemberUpdated, InlineKeyboardMarkup, InlineKeyboardButton
from loguru import logger
from sqlalchemy.orm import Session

from other.aiogram_tools import is_admin, cmd_delete_later, cmd_sleep_and_delete, ChatInOption, get_username_link
from other.config_reader import config
from other.global_data import global_data, BotValueTypes, update_command_info, is_topic_admin
from other.pyro_tools import get_group_members, remove_deleted_users
from other.timedelta import parse_timedelta_from_message

router = Router()


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


@router.message(Command(commands=["topic"]))
async def cmd_create_topic(message: Message):
    if not await is_admin(message):
        await message.reply("You are not an admin.")
        return

    if not message.chat.is_forum:
        await message.reply("Topics are not enabled in this chat.")
        return

    command_parts = message.text.split(maxsplit=2)
    if len(command_parts) != 3:
        await message.reply("Incorrect command format. Use: /topic 🔵 Topic Name")
        return

    emoji, topic_name = command_parts[1], command_parts[2]

    try:
        new_topic = await message.bot.create_forum_topic(name=topic_name, icon_custom_emoji_id=emoji,
                                                         chat_id=message.chat.id)
        await message.reply(f"New topic '{topic_name}' created successfully with ID: {new_topic.message_thread_id}")
    except TelegramBadRequest as e:
        if "CHAT_NOT_MODIFIED" in str(e):
            await message.reply("Failed to create topic. Make sure the emoji is valid and the topic name is unique.")
        else:
            await message.reply(f"An error occurred while creating the topic: {str(e)}")


@update_command_info("/all", "тегнуть всех пользователей. работает зависимо от чата. и только в рабочих чатах")
@router.message(Command(commands=["all"]))
async def cmd_all(message: Message):
    user_list = await get_group_members(message.chat.id)
    members = [f'@{user.username}' for user in user_list if not user.is_bot and user.username]
    await message.reply(' '.join(members))


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


@update_command_info("/mute", "Блокирует пользователя в текущей ветке")
@router.message(ChatInOption('moderate'), Command(commands=["mute"]))
async def cmd_mute(message: Message):
    chat_thread_key = f"{message.chat.id}-{message.message_thread_id}"
    if chat_thread_key not in global_data.topic_admins:
        await message.reply('Local admins not set yet')
        return False

    if not is_topic_admin(message):
        await message.reply('You are not local admin')
        return False

    if message.reply_to_message is None or message.reply_to_message.forum_topic_created:
        await message.reply('Please send for reply message to set mute')
        return

    delta = await parse_timedelta_from_message(message)
    user_id = message.reply_to_message.from_user.id
    end_time_str = (datetime.now() + delta).isoformat()

    if chat_thread_key not in global_data.topic_mute:
        global_data.topic_mute[chat_thread_key] = {}

    user = get_username_link(message.reply_to_message.from_user)
    global_data.topic_mute[chat_thread_key][user_id] = {"end_time": end_time_str, "user": user}
    await global_data.mongo_config.save_bot_value(0, BotValueTypes.TopicMutes, json.dumps(global_data.topic_mute))

    await message.reply(f'{user} was set mute for {delta} in topic {chat_thread_key}')


@update_command_info("/show_mute", "Показывает пользователей, которые заблокированы в текущей ветке")
@router.message(ChatInOption('moderate'), Command(commands=["show_mute"]))
async def cmd_show_mutes(message: Message):
    chat_thread_key = f"{message.chat.id}-{message.message_thread_id}"

    if chat_thread_key not in global_data.topic_admins:
        await message.reply('Local admins not set yet')
        return False

    if not is_topic_admin(message):
        await message.reply('You are not local admin')
        return False

    if chat_thread_key not in global_data.topic_mute or not global_data.topic_mute[chat_thread_key]:
        await message.reply('No users are currently muted in this topic')
        return

    current_time = datetime.now()
    muted_users = []
    users_to_remove = []

    mute_items = list(global_data.topic_mute[chat_thread_key].items())

    for user_id, mute_info in mute_items:
        try:
            end_time = datetime.fromisoformat(mute_info["end_time"])
            if end_time > current_time:
                remaining_time = end_time - current_time
                muted_users.append(f"{mute_info['user']} - {remaining_time}")
            else:
                users_to_remove.append(user_id)
        except (ValueError, KeyError):
            continue

    for user_id in users_to_remove:
        del global_data.topic_mute[chat_thread_key][user_id]

    if users_to_remove:
        await global_data.mongo_config.save_bot_value(0, BotValueTypes.TopicMutes,
                                                      json.dumps(global_data.topic_mute))

    if muted_users:
        mute_list = "\n".join(muted_users)
        await message.reply(f"Currently muted users in this topic:\n{mute_list}")
    else:
        await message.reply('No users are currently muted in this topic')


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


def register_handlers(dp, bot):
    dp.include_router(router)
    logger.info('router admin_core was loaded')
