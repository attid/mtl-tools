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
from other.constants import MTLChats, BotValueTypes
from services.command_registry_service import update_command_info
from db.repositories import ConfigRepository
from routers.admin_panel import load_inaccessible_chats

router = Router()


# =============================================================================
# DI Service Access Helpers
# =============================================================================

def _get_feature_flag_list(ctx, feature_name: str) -> list:
    """Get feature flag list from DI service. Raises error if ctx not available."""
    if not ctx or not ctx.feature_flags:
        raise ValueError("app_context with feature_flags required")
    return ctx.feature_flags.get_feature_list(feature_name)


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
# Format: (db_value_type, action_type, admin_check, load_type, feature_flag_name)
# load_type: 0 = none, 1 = list/dict from DB by chat_id, 3 = json blob
# =============================================================================

commands_info = {
    "set_reply_only": (BotValueTypes.ReplyOnly, "toggle", "admin", 1, "reply_only"),
    "delete_income": (BotValueTypes.DeleteIncome, "toggle", "admin", 1, "delete_income"),
    "set_no_first_link": (BotValueTypes.NoFirstLink, "toggle", "admin", 1, "no_first_link"),
    # full_data - chats with full address decoding
    "full_data": (BotValueTypes.FullData, "toggle", "skynet_admin", 1, "full_data"),
    "need_decode": (BotValueTypes.NeedDecode, "toggle", "admin", 1, "need_decode"),
    "save_last_message_date": (BotValueTypes.SaveLastMessageDate, "toggle", "admin", 1, "save_last_message_date"),
    "set_first_vote": (BotValueTypes.FirstVote, "toggle", "admin", 1, "first_vote"),
    "notify_join_request": (BotValueTypes.NotifyJoin, "toggle_chat", "admin", 1, "notify_join"),
    "notify_message": (BotValueTypes.NotifyMessage, "toggle_chat", "admin", 1, "notify_message"),
    "join_request_captcha": (BotValueTypes.JoinRequestCaptcha, "toggle", "admin", 1, "join_request_captcha"),
    "auto_all": (BotValueTypes.AutoAll, "toggle", "admin", 1, "auto_all"),
    "set_listen": (BotValueTypes.Listen, "toggle", "skynet_admin", 1, "listen"),
    # ToDo need show to skyadmin in helpers
    "set_captcha": (BotValueTypes.Captcha, "toggle", "admin", 1, "captcha"),
    "set_moderate": (BotValueTypes.Moderate, "toggle", "admin", 1, "moderate"),
    "set_entry_channel": (BotValueTypes.EntryChannel, "toggle_entry_channel", "admin", 1, "entry_channel"),

    "add_skynet_img": (BotValueTypes.SkynetImg, "add_list", "skynet_admin", 3, "skynet_img"),
    "del_skynet_img": (BotValueTypes.SkynetImg, "del_list", "skynet_admin", 0, "skynet_img"),
    "show_skynet_img": (BotValueTypes.SkynetImg, "show_list", "skynet_admin", 0, "skynet_img"),
    "add_skynet_admin": (BotValueTypes.SkynetAdmins, "add_list", "skynet_admin", 3, "skynet_admins"),
    "del_skynet_admin": (BotValueTypes.SkynetAdmins, "del_list", "skynet_admin", 0, "skynet_admins"),
    "show_skynet_admin": (BotValueTypes.SkynetAdmins, "show_list", "skynet_admin", 0, "skynet_admins"),
    "add_topic_admin": (BotValueTypes.TopicAdmins, "add_list_topic", "admin", 3, "topic_admins"),
    "del_topic_admin": (BotValueTypes.TopicAdmins, "del_list_topic", "admin", 0, "topic_admins"),
    "show_topic_admin": (BotValueTypes.TopicAdmins, "show_list_topic", "admin", 0, "topic_admins"),
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

        # Load feature flags (list-based) directly into feature_flags service
        feature_flag_mappings = [
            (BotValueTypes.ReplyOnly, "reply_only"),
            (BotValueTypes.NoFirstLink, "no_first_link"),
            (BotValueTypes.FullData, "full_data"),
            (BotValueTypes.NeedDecode, "need_decode"),
            (BotValueTypes.SaveLastMessageDate, "save_last_message_date"),
            (BotValueTypes.FirstVote, "first_vote"),
            (BotValueTypes.JoinRequestCaptcha, "join_request_captcha"),
            (BotValueTypes.AutoAll, "auto_all"),
            (BotValueTypes.Listen, "listen"),
            (BotValueTypes.Captcha, "captcha"),
            (BotValueTypes.Moderate, "moderate"),
        ]

        for db_key, feature_name in feature_flag_mappings:
            for chat_id in repo.get_chat_ids_by_key(db_key):
                app_context.feature_flags.set_feature(chat_id, feature_name, True, persist=False)

        # Load dict-based features (notify_join, notify_message, delete_income, entry_channel)
        notify_join_data = repo.get_chat_dict_by_key(BotValueTypes.NotifyJoin)
        app_context.notification_service.load_notify_join(notify_join_data)
        for chat_id in notify_join_data:
            app_context.feature_flags.set_feature(chat_id, "notify_join", True, persist=False)

        notify_message_data = repo.get_chat_dict_by_key(BotValueTypes.NotifyMessage)
        app_context.notification_service.load_notify_message(notify_message_data)
        for chat_id in notify_message_data:
            app_context.feature_flags.set_feature(chat_id, "notify_message", True, persist=False)

        delete_income_data = repo.get_chat_dict_by_key(BotValueTypes.DeleteIncome)
        app_context.config_service.load_delete_income(delete_income_data)
        for chat_id in delete_income_data:
            app_context.feature_flags.set_feature(chat_id, "delete_income", True, persist=False)

        entry_channel_data = repo.get_chat_dict_by_key(BotValueTypes.EntryChannel)
        for chat_id in entry_channel_data:
            app_context.feature_flags.set_feature(chat_id, "entry_channel", True, persist=False)

        # Load JSON-based global lists (skynet_admins, skynet_img)
        skynet_admins = json.loads(repo.load_bot_value(0, BotValueTypes.SkynetAdmins, '[]'))
        app_context.admin_service.set_skynet_admins(skynet_admins)

        skynet_img = json.loads(repo.load_bot_value(0, BotValueTypes.SkynetImg, '[]'))
        app_context.admin_service.set_skynet_img_users(skynet_img)

        # Load topic admins (JSON dict)
        topic_admins = json.loads(repo.load_bot_value(0, BotValueTypes.TopicAdmins, '{}'))
        app_context.admin_service.load_topic_admins(topic_admins)

        # Load votes data
        votes = json.loads(repo.load_bot_value(0, BotValueTypes.Votes, '{}'))
        app_context.voting_service.load_votes(votes)

        # Load first_vote into voting service
        first_vote_chat_ids = repo.get_chat_ids_by_key(BotValueTypes.FirstVote)
        app_context.voting_service.load_first_vote(first_vote_chat_ids)

        # Load topic mutes
        topic_mute = json.loads(repo.load_bot_value(0, BotValueTypes.TopicMutes, '{}'))
        app_context.admin_service.load_topic_mutes(topic_mute)

        # Load inaccessible chats for admin panel
        inaccessible_chats = json.loads(repo.load_bot_value(0, BotValueTypes.Inaccessible, '[]'))
        load_inaccessible_chats(inaccessible_chats)

        # Load welcome messages and buttons
        welcome_messages = repo.get_chat_dict_by_key(BotValueTypes.WelcomeMessage)
        app_context.config_service.load_welcome_messages(welcome_messages)

        welcome_buttons = repo.get_chat_dict_by_key(BotValueTypes.WelcomeButton)
        app_context.config_service.load_welcome_buttons(welcome_buttons)

        # Load admins
        admins = repo.get_chat_dict_by_key(BotValueTypes.Admins, True)
        app_context.admin_service.load_admins(admins)

        # Load alert_me
        alert_me = repo.get_chat_dict_by_key(BotValueTypes.AlertMe, True)
        app_context.notification_service.load_alert_me(alert_me)

        # Load sync states
        sync_data = repo.get_chat_dict_by_key(BotValueTypes.Sync, True)
        for channel_id, sync_state in sync_data.items():
            app_context.bot_state_service.set_sync_state(str(channel_id), sync_state)

        # Mark need_decode in bot_state_service
        for chat_id in repo.get_chat_ids_by_key(BotValueTypes.NeedDecode):
            app_context.bot_state_service.mark_needs_decode(chat_id)

    # Log loaded feature flags statistics
    _log_feature_flags_stats(app_context)

    logger.info('finished command_config_loads task')


def _log_feature_flags_stats(app_context):
    """Log statistics of loaded feature flags for startup validation."""
    stats = [
        f"no_first_link: {len(app_context.feature_flags.get_feature_list('no_first_link'))} chats",
        f"moderate: {len(app_context.feature_flags.get_feature_list('moderate'))} chats",
        f"captcha: {len(app_context.feature_flags.get_feature_list('captcha'))} chats",
        f"reply_only: {len(app_context.feature_flags.get_feature_list('reply_only'))} chats",
        f"listen: {len(app_context.feature_flags.get_feature_list('listen'))} chats",
        f"auto_all: {len(app_context.feature_flags.get_feature_list('auto_all'))} chats",
        f"save_last_message_date: {len(app_context.feature_flags.get_feature_list('save_last_message_date'))} chats",
        f"join_request_captcha: {len(app_context.feature_flags.get_feature_list('join_request_captcha'))} chats",
        f"full_data: {len(app_context.feature_flags.get_feature_list('full_data'))} chats",
        f"first_vote: {len(app_context.feature_flags.get_feature_list('first_vote'))} chats",
        f"need_decode: {len(app_context.feature_flags.get_feature_list('need_decode'))} chats",
        f"notify_join: {len(app_context.notification_service.get_all_join_notify())} chats",
        f"notify_message: {len(app_context.notification_service.get_all_message_notify())} chats",
        f"entry_channel: {len(app_context.feature_flags.get_feature_list('entry_channel'))} chats",
        f"welcome_messages: {len(app_context.config_service._welcome_messages)} chats",
        f"admins: {len(app_context.admin_service._admins)} chats",
        f"skynet_admins: {len(app_context.admin_service.get_skynet_admins())} users",
        f"sync: {len(app_context.bot_state_service._sync)} channels",
    ]
    logger.info("Feature flags loaded:\n  " + "\n  ".join(stats))


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
    action_type = command_info[1]
    admin_check = command_info[2]

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
    """Handle toggle commands using feature_flags service."""
    chat_id = message.chat.id
    db_value_type = command_info[0]
    feature_name = command_info[4]

    command_args = message.text.split()[1:]  # List of arguments after command

    # Check current state using feature_flags service
    is_enabled = app_context.feature_flags.is_enabled(chat_id, feature_name)

    if is_enabled:
        # Disable the feature
        app_context.feature_flags.set_feature(chat_id, feature_name, False, persist=False)
        ConfigRepository(session).save_bot_value(chat_id, db_value_type, None)

        # Sync removal to specialized DI services
        _sync_toggle_removal(app_context, db_value_type, chat_id)

        info_message = await message.reply('Removed')
    else:
        # Enable the feature
        value_to_set = command_args[0] if command_args else '1'
        app_context.feature_flags.set_feature(chat_id, feature_name, True, persist=False)
        ConfigRepository(session).save_bot_value(chat_id, db_value_type, value_to_set)

        # Sync addition to specialized DI services
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
    feature_name = command_info[4]

    is_enabled = app_context.feature_flags.is_enabled(chat_id, feature_name)

    if not is_enabled:
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
    """Handle list commands (add/del/show) for skynet_admins and skynet_img using admin_service."""
    db_value_type = command_info[0]
    action_type = command_info[1]

    command_args = message.text.lower().split()[1:]  # arguments after command

    # Get current list from admin_service
    if db_value_type == BotValueTypes.SkynetAdmins:
        current_list = app_context.admin_service.get_skynet_admins()
    elif db_value_type == BotValueTypes.SkynetImg:
        current_list = app_context.admin_service.get_skynet_img_users()
    else:
        await message.reply("Unknown list type.")
        return

    if action_type == "add_list":
        if not command_args:
            await message.reply("Необходимо указать аргументы.")
        else:
            # Add to list
            for arg in command_args:
                if arg not in current_list:
                    current_list.append(arg)
            # Update service and persist
            if db_value_type == BotValueTypes.SkynetAdmins:
                app_context.admin_service.set_skynet_admins(current_list)
            else:
                app_context.admin_service.set_skynet_img_users(current_list)
            ConfigRepository(session).save_bot_value(0, db_value_type, json.dumps(current_list))
            await message.reply(f'Added: {" ".join(command_args)}')

    elif action_type == "del_list":
        if not command_args:
            await message.reply("Необходимо указать аргументы.")
        else:
            # Remove from list
            for arg in command_args:
                if arg in current_list:
                    current_list.remove(arg)
            # Update service and persist
            if db_value_type == BotValueTypes.SkynetAdmins:
                app_context.admin_service.set_skynet_admins(current_list)
            else:
                app_context.admin_service.set_skynet_img_users(current_list)
            ConfigRepository(session).save_bot_value(0, db_value_type, json.dumps(current_list))
            await message.reply(f'Removed: {" ".join(command_args)}')

    elif action_type == "show_list":
        if current_list:
            await message.reply(' '.join(current_list))
        else:
            await message.reply('The list is empty.')


async def list_command_handler_topic(message: Message, command_info, session, app_context=None):
    """Handle topic-specific list commands using admin_service."""
    db_value_type = command_info[0]
    action_type = command_info[1]

    command_args = message.text.lower().split()[1:]  # arguments after command
    chat_thread_key = f"{message.chat.id}-{message.message_thread_id}"

    # Get all topic admins from admin_service
    all_topic_admins = app_context.admin_service.get_all_topic_admins()

    if action_type == "add_list_topic":
        if not command_args:
            await message.reply("Необходимо указать аргументы.")
        else:
            if chat_thread_key not in all_topic_admins:
                all_topic_admins[chat_thread_key] = []
            all_topic_admins[chat_thread_key].extend(command_args)
            # Update service and persist
            app_context.admin_service.load_topic_admins(all_topic_admins)
            ConfigRepository(session).save_bot_value(0, db_value_type, json.dumps(all_topic_admins))
            await message.reply(f'Added at this thread: {" ".join(command_args)}')

    elif action_type == "del_list_topic":
        if not command_args:
            await message.reply("Необходимо указать аргументы.")
        else:
            if chat_thread_key in all_topic_admins:
                for arg in command_args:
                    if arg in all_topic_admins[chat_thread_key]:
                        all_topic_admins[chat_thread_key].remove(arg)
                # Update service and persist
                app_context.admin_service.load_topic_admins(all_topic_admins)
                ConfigRepository(session).save_bot_value(0, db_value_type, json.dumps(all_topic_admins))
                await message.reply(f'Removed from this thread: {" ".join(command_args)}')
            else:
                await message.reply('This thread has no items in the list.')

    elif action_type == "show_list_topic":
        if chat_thread_key in all_topic_admins and all_topic_admins[chat_thread_key]:
            await message.reply(f'Items in this thread: {" ".join(all_topic_admins[chat_thread_key])}')
        else:
            await message.reply('The list for this thread is empty.')


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
