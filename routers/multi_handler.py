import asyncio
import json
from contextlib import suppress
from typing import Any, Optional

from aiogram import Router, Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.types import (Message, ReactionTypeEmoji)
from loguru import logger

from other.config_reader import config
from other.global_data import global_data, update_command_info
from other.constants import MTLChats, BotValueTypes
from db.repositories import ConfigRepository

router = Router()


# =============================================================================
# DI Service Access Helpers with global_data fallback
# =============================================================================

def _get_feature_flag_list(ctx, feature_name: str) -> list:
    """Get feature flag list from DI service. Raises error if ctx not available."""
    if not ctx or not ctx.feature_flags:
        raise ValueError("app_context with feature_flags required")
    return ctx.feature_flags.get_feature_list(feature_name)


def _get_feature_flag_dict(ctx, feature_name: str) -> dict:
    """Get feature flag dict from DI service. Raises error if ctx not available."""
    if not ctx or not ctx.feature_flags:
        raise ValueError("app_context with feature_flags required")
    return ctx.feature_flags.get_feature_dict(feature_name)


def _is_feature_enabled(ctx, chat_id: int, feature: str) -> bool:
    """Check if feature is enabled using DI. Raises error if ctx not available."""
    if not ctx or not ctx.feature_flags:
        raise ValueError("app_context with feature_flags required")
    return ctx.feature_flags.is_enabled(chat_id, feature)


def _get_delete_income(ctx, chat_id: int) -> Optional[Any]:
    """Get delete income config using DI. Raises error if ctx not available."""
    if not ctx or not ctx.config_service:
        raise ValueError("app_context with config_service required")
    return ctx.config_service.get_delete_income(chat_id)


def _needs_decode(ctx, chat_id: int) -> bool:
    """Check if chat needs decode using DI. Raises error if ctx not available."""
    if not ctx or not ctx.bot_state_service:
        raise ValueError("app_context with bot_state_service required")
    return ctx.bot_state_service.needs_decode(chat_id)


def _is_first_vote_enabled(ctx, chat_id: int) -> bool:
    """Check if first vote is enabled using DI. Raises error if ctx not available."""
    if not ctx or not ctx.voting_service:
        raise ValueError("app_context with voting_service required")
    return ctx.voting_service.is_first_vote_enabled(chat_id)


def _get_join_notify_config(ctx, chat_id: int) -> Optional[Any]:
    """Get join notify config using DI. Raises error if ctx not available."""
    if not ctx or not ctx.notification_service:
        raise ValueError("app_context with notification_service required")
    return ctx.notification_service.get_join_notify_config(chat_id)


def _get_message_notify_config(ctx, chat_id: int) -> Optional[Any]:
    """Get message notify config using DI. Raises error if ctx not available."""
    if not ctx or not ctx.notification_service:
        raise ValueError("app_context with notification_service required")
    return ctx.notification_service.get_message_notify_config(chat_id)


def _is_topic_admin(ctx, chat_id: int, thread_id: int, username: str) -> bool:
    """Check if user is topic admin using DI. Raises error if ctx not available."""
    if not ctx or not ctx.admin_service:
        raise ValueError("app_context with admin_service required")
    return ctx.admin_service.is_topic_admin(chat_id, thread_id, username)


def _is_topic_muted(ctx, chat_id: int, thread_id: int) -> bool:
    """Check if topic has mutes using DI. Raises error if ctx not available."""
    if not ctx or not ctx.admin_service:
        raise ValueError("app_context with admin_service required")
    return ctx.admin_service.has_topic_mutes(chat_id, thread_id)


def _is_skynet_admin(ctx, username: str) -> bool:
    """Check if user is skynet admin using DI. Raises error if ctx not available."""
    if not ctx or not ctx.admin_service:
        raise ValueError("app_context with admin_service required")
    return ctx.admin_service.is_skynet_admin(username)


def _get_entry_channel(ctx, chat_id: int) -> Optional[str]:
    """Get entry channel config using DI. Raises error if ctx not available."""
    if not ctx or not ctx.config_service:
        raise ValueError("app_context with config_service required")
    return ctx.config_service.load_value(chat_id, 'entry_channel')


# =============================================================================
# Commands Configuration
# Note: commands_info uses global_data references for backward compatibility
# with existing toggle logic. The helpers above provide DI access for reads.
# =============================================================================

commands_info = {
    "set_reply_only": (global_data.reply_only, BotValueTypes.ReplyOnly, "toggle", "admin", 1),
    "delete_income": (global_data.delete_income, BotValueTypes.DeleteIncome, "toggle", "admin", 1),
    "set_no_first_link": (global_data.no_first_link, BotValueTypes.NoFirstLink, "toggle", "admin", 1),
    # full_data - chats with full address decoding
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


def command_config_loads(app_context):
    """
    Load configuration from database directly into DI services.

    Args:
        app_context: AppContext with DI services
    """
    from db.session import create_session

    with create_session() as session:
        repo = ConfigRepository(session)

        for command in commands_info:
            global_data_field = commands_info[command][0]
            global_data_key = commands_info[command][1]
            load_type = commands_info[command][4]  # 0 none 1 - dict\list  3 - json

            if load_type == 1:
                if isinstance(global_data_field, dict):
                    global_data_field.update(repo.get_chat_dict_by_key(global_data_key))
                else:
                    global_data_field.extend(repo.get_chat_ids_by_key(global_data_key))

            if load_type == 3:
                if isinstance(global_data_field, dict):
                    global_data_field.update(
                        json.loads(repo.load_bot_value(0, global_data_key, '{}')))
                else:
                    global_data_field.extend(
                        json.loads(repo.load_bot_value(0, global_data_key, '[]')))

        global_data.votes = json.loads(repo.load_bot_value(0, BotValueTypes.Votes, '{}'))
        global_data.topic_mute = json.loads(repo.load_bot_value(0, BotValueTypes.TopicMutes, '{}'))

        global_data.welcome_messages = repo.get_chat_dict_by_key(BotValueTypes.WelcomeMessage)
        global_data.welcome_button = repo.get_chat_dict_by_key(BotValueTypes.WelcomeButton)
        global_data.admins = repo.get_chat_dict_by_key(BotValueTypes.Admins, True)
        global_data.alert_me = repo.get_chat_dict_by_key(BotValueTypes.AlertMe, True)
        global_data.sync = repo.get_chat_dict_by_key(BotValueTypes.Sync, True)

    # Sync loaded data to DI services
    _sync_to_di_services(app_context)

    # Log loaded feature flags statistics
    _log_feature_flags_stats()

    logger.info('finished command_config_loads task')


def _log_feature_flags_stats():
    """Log statistics of loaded feature flags for startup validation."""
    stats = [
        f"no_first_link: {len(global_data.no_first_link)} chats",
        f"moderate: {len(global_data.moderate)} chats",
        f"captcha: {len(global_data.captcha)} chats",
        f"reply_only: {len(global_data.reply_only)} chats",
        f"listen: {len(global_data.listen)} chats",
        f"auto_all: {len(global_data.auto_all)} chats",
        f"save_last_message_date: {len(global_data.save_last_message_date)} chats",
        f"join_request_captcha: {len(global_data.join_request_captcha)} chats",
        f"full_data: {len(global_data.full_data)} chats",
        f"first_vote: {len(global_data.first_vote)} chats",
        f"need_decode: {len(global_data.need_decode)} chats",
        f"notify_join: {len(global_data.notify_join)} chats",
        f"notify_message: {len(global_data.notify_message)} chats",
        f"entry_channel: {len(global_data.entry_channel)} chats",
        f"welcome_messages: {len(global_data.welcome_messages)} chats",
        f"admins: {len(global_data.admins)} chats",
        f"skynet_admins: {len(global_data.skynet_admins)} users",
        f"users_list: {len(global_data.users_list)} users",
        f"sync: {len(global_data.sync)} channels",
    ]
    logger.info("Feature flags loaded:\n  " + "\n  ".join(stats))


def _sync_to_di_services(ctx):
    """Sync loaded global_data to DI services for consistent state."""
    # Sync voting service
    if ctx.voting_service:
        ctx.voting_service.load_votes(global_data.votes)
        ctx.voting_service.load_first_vote(global_data.first_vote)

    # Sync admin service
    if ctx.admin_service:
        ctx.admin_service.load_topic_admins(global_data.topic_admins)
        ctx.admin_service.load_topic_mutes(global_data.topic_mute)
        ctx.admin_service.set_skynet_admins(global_data.skynet_admins)
        ctx.admin_service.set_skynet_img_users(global_data.skynet_img)
        ctx.admin_service.load_admins(global_data.admins)

    # Sync notification service
    if ctx.notification_service:
        ctx.notification_service.load_notify_join(global_data.notify_join)
        ctx.notification_service.load_notify_message(global_data.notify_message)
        ctx.notification_service.load_alert_me(global_data.alert_me)

    # Sync config service
    if ctx.config_service:
        ctx.config_service.load_welcome_messages(global_data.welcome_messages)
        ctx.config_service.load_welcome_buttons(global_data.welcome_button)
        ctx.config_service.load_delete_income(global_data.delete_income)

    # Sync bot state service
    if ctx.bot_state_service:
        for chat_id in global_data.need_decode:
            ctx.bot_state_service.mark_needs_decode(chat_id)
        # Sync channel sync states
        for channel_id, sync_data in global_data.sync.items():
            ctx.bot_state_service.set_sync_state(str(channel_id), sync_data)

    # Sync feature flags
    if ctx.feature_flags:
        # List-based features
        for chat_id in global_data.captcha:
            ctx.feature_flags.enable(chat_id, "captcha")
        for chat_id in global_data.moderate:
            ctx.feature_flags.enable(chat_id, "moderate")
        for chat_id in global_data.listen:
            ctx.feature_flags.enable(chat_id, "listen")
        for chat_id in global_data.no_first_link:
            ctx.feature_flags.enable(chat_id, "no_first_link")
        for chat_id in global_data.reply_only:
            ctx.feature_flags.enable(chat_id, "reply_only")
        for chat_id in global_data.auto_all:
            ctx.feature_flags.enable(chat_id, "auto_all")
        for chat_id in global_data.save_last_message_date:
            ctx.feature_flags.enable(chat_id, "save_last_message_date")
        for chat_id in global_data.join_request_captcha:
            ctx.feature_flags.enable(chat_id, "join_request_captcha")
        for chat_id in global_data.full_data:
            ctx.feature_flags.enable(chat_id, "full_data")
        for chat_id in global_data.first_vote:
            ctx.feature_flags.enable(chat_id, "first_vote")
        for chat_id in global_data.need_decode:
            ctx.feature_flags.enable(chat_id, "need_decode")
        # Dict-based features (entry_channel, delete_income)
        for chat_id in global_data.delete_income:
            ctx.feature_flags.enable(chat_id, "delete_income")
        for chat_id in global_data.entry_channel:
            ctx.feature_flags.enable(chat_id, "entry_channel")


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
async def universal_command_handler(message: Message, bot: Bot, session, app_context=None):
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
        await list_command_handler(message, command_info, session, app_context=app_context)

    if action_type in ["add_list_topic", "del_list_topic", "show_list_topic"]:
        if not message.message_thread_id:
            await message.reply("Run this command in thread.")
            return
        await list_command_handler_topic(message, command_info, session, app_context=app_context)

    if action_type == "toggle_chat":
        await handle_command(message, command_info, session, app_context=app_context)
        return

    if action_type == "toggle_entry_channel":
        await handle_entry_channel_toggle(message, command_info, session, app_context=app_context)
        return

    if action_type == "toggle":
        await handle_command(message, command_info, session, app_context=app_context)


async def handle_command(message: Message, command_info, session, app_context=None):
    chat_id = message.chat.id
    global_data_field = command_info[0]
    db_value_type = command_info[1]

    command_args = message.text.split()[1:]  # Список аргументов после команды

    if chat_id in global_data_field:
        if isinstance(global_data_field, dict):
            global_data_field.pop(chat_id)
        else:
            global_data_field.remove(chat_id)

        ConfigRepository(session).save_bot_value(chat_id, db_value_type, None)

        # Sync removal to DI services
        _sync_toggle_removal(app_context, db_value_type, chat_id)

        info_message = await message.reply('Removed')
    else:
        value_to_set = command_args[0] if command_args else '1'
        if isinstance(global_data_field, dict):
            global_data_field[chat_id] = value_to_set
        else:
            global_data_field.append(chat_id)

        ConfigRepository(session).save_bot_value(chat_id, db_value_type, value_to_set)

        # Sync addition to DI services
        _sync_toggle_addition(app_context, db_value_type, chat_id, value_to_set)

        info_message = await message.reply('Added')

    await app_context.utils_service.sleep_and_delete(info_message, 5)

    with suppress(TelegramBadRequest):
        await asyncio.sleep(1)
        await message.delete()


def _sync_toggle_removal(ctx, db_value_type: BotValueTypes, chat_id: int):
    """Sync toggle removal to DI services."""
    if not ctx:
        return

    if db_value_type == BotValueTypes.FirstVote and ctx.voting_service:
        ctx.voting_service.disable_first_vote(chat_id)
    elif db_value_type == BotValueTypes.NeedDecode and ctx.bot_state_service:
        ctx.bot_state_service.clear_needs_decode(chat_id)
    elif db_value_type == BotValueTypes.NotifyJoin and ctx.notification_service:
        ctx.notification_service.disable_join_notify(chat_id)
    elif db_value_type == BotValueTypes.NotifyMessage and ctx.notification_service:
        ctx.notification_service.disable_message_notify(chat_id)
    elif db_value_type == BotValueTypes.DeleteIncome and ctx.config_service:
        ctx.config_service.remove_delete_income(chat_id)


def _sync_toggle_addition(ctx, db_value_type: BotValueTypes, chat_id: int, value: str):
    """Sync toggle addition to DI services."""
    if not ctx:
        return

    if db_value_type == BotValueTypes.FirstVote and ctx.voting_service:
        ctx.voting_service.enable_first_vote(chat_id)
    elif db_value_type == BotValueTypes.NeedDecode and ctx.bot_state_service:
        ctx.bot_state_service.mark_needs_decode(chat_id)
    elif db_value_type == BotValueTypes.NotifyJoin and ctx.notification_service:
        ctx.notification_service.set_join_notify(chat_id, value)
    elif db_value_type == BotValueTypes.NotifyMessage and ctx.notification_service:
        ctx.notification_service.set_message_notify(chat_id, value)
    elif db_value_type == BotValueTypes.DeleteIncome and ctx.config_service:
        ctx.config_service.set_delete_income(chat_id, value)


async def handle_entry_channel_toggle(message: Message, command_info, session, app_context=None):
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

    await handle_command(message, command_info, session, app_context=app_context)


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
    required_channel = _get_entry_channel(app_context, chat_id)
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


async def list_command_handler(message: Message, command_info, session, app_context=None):
    global_data_field = command_info[0]
    db_value_type = command_info[1]
    action_type = command_info[2]

    command_args = message.text.lower().split()[1:]  # аргументы после команды

    if action_type == "add_list":
        if not command_args:
            await message.reply("Необходимо указать аргументы.")
        else:
            global_data_field.extend(command_args)
            ConfigRepository(session).save_bot_value(0, db_value_type, json.dumps(global_data_field))
            # Sync to DI services
            _sync_list_update(app_context, db_value_type, global_data_field)
            await message.reply(f'Added: {" ".join(command_args)}')

    elif action_type == "del_list":
        if not command_args:
            await message.reply("Необходимо указать аргументы.")
        else:
            for arg in command_args:
                if arg in global_data_field:
                    global_data_field.remove(arg)
            ConfigRepository(session).save_bot_value(0, db_value_type, json.dumps(global_data_field))
            # Sync to DI services
            _sync_list_update(app_context, db_value_type, global_data_field)
            await message.reply(f'Removed: {" ".join(command_args)}')

    elif action_type == "show_list":
        if global_data_field:
            await message.reply(' '.join(global_data_field))
        else:
            await message.reply('The list is empty.')


def _sync_list_update(ctx, db_value_type: BotValueTypes, data: list):
    """Sync list updates to DI services."""
    if not ctx:
        return

    if db_value_type == BotValueTypes.SkynetAdmins and ctx.admin_service:
        ctx.admin_service.set_skynet_admins(data)
    elif db_value_type == BotValueTypes.SkynetImg and ctx.admin_service:
        ctx.admin_service.set_skynet_img_users(data)


async def list_command_handler_topic(message: Message, command_info, session, app_context=None):
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
            ConfigRepository(session).save_bot_value(0, db_value_type, json.dumps(global_data_field))
            # Sync to DI services
            _sync_topic_list_update(app_context, db_value_type, global_data_field)
            await message.reply(f'Added at this thread: {" ".join(command_args)}')

    elif action_type == "del_list_topic":
        if not command_args:
            await message.reply("Необходимо указать аргументы.")
        else:
            if chat_thread_key in global_data_field:
                for arg in command_args:
                    if arg in global_data_field[chat_thread_key]:
                        global_data_field[chat_thread_key].remove(arg)
                ConfigRepository(session).save_bot_value(0, db_value_type, json.dumps(global_data_field))
                # Sync to DI services
                _sync_topic_list_update(app_context, db_value_type, global_data_field)
                await message.reply(f'Removed from this thread: {" ".join(command_args)}')
            else:
                await message.reply('This thread has no items in the list.')

    elif action_type == "show_list_topic":
        if chat_thread_key in global_data_field and global_data_field[chat_thread_key]:
            await message.reply(f'Items in this thread: {" ".join(global_data_field[chat_thread_key])}')
        else:
            await message.reply('The list for this thread is empty.')


def _sync_topic_list_update(ctx, db_value_type: BotValueTypes, data: dict):
    """Sync topic list updates to DI services."""
    if not ctx:
        return

    if db_value_type == BotValueTypes.TopicAdmins and ctx.admin_service:
        ctx.admin_service.load_topic_admins(data)


@router.startup()
async def on_startup(dispatcher):
    app_context = dispatcher.get('app_context') if hasattr(dispatcher, 'get') else None
    if app_context:
        command_config_loads(app_context)


def register_handlers(dp, bot):
    dp.include_router(router)
    logger.info('router admin was loaded')


if __name__ == "__main__":
    pass
