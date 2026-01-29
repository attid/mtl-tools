# routers/admin_panel.py
"""Admin panel for chat management in private messages and admin reload in groups."""

import json
from contextlib import suppress
from typing import Optional

from aiogram import Router, Bot, F
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from loguru import logger
from sqlalchemy.orm import Session

from db.repositories import ConfigRepository
from other.constants import BotValueTypes
from services.command_registry_service import update_command_info
from services.app_context import AppContext
from services.feature_flags import FeatureFlagsService

router = Router()


# ============ Callback Data ============

class AdminCallback(CallbackData, prefix="adm"):
    """Callback data for admin panel navigation."""
    action: str           # list, menu, flags, welcome, toggle, edit, del
    chat_id: int = 0
    param: str = ""


# ============ FSM States ============

class AdminPanelStates(StatesGroup):
    """FSM states for admin panel text input."""
    waiting_welcome_message = State()
    waiting_welcome_button = State()


# ============ Feature Flag Labels ============

FEATURE_LABELS = {
    "captcha": "Captcha",
    "moderate": "Moderate",
    "no_first_link": "No First Link",
    "reply_only": "Reply Only",
    "listen": "Listen",
    "auto_all": "Auto All",
    "save_last_message_date": "Save Last Msg Date",
    "join_request_captcha": "Join Request Captcha",
    "full_data": "Full Data",
    "first_vote": "First Vote",
    "need_decode": "Need Decode",
    "delete_income": "Delete Income",
    "entry_channel": "Entry Channel",
}


def get_feature_description(feature_key: str, app_context: AppContext) -> str:
    """Get feature description from command_registry by cmd_list."""
    if not app_context or not app_context.command_registry:
        return ''

    for cmd in app_context.command_registry.get_all_commands().values():
        if feature_key in cmd.cmd_list:
            return cmd.description
    return ''


# ============ Chat Title Cache ============

_chat_titles: dict[int, str] = {}
_inaccessible_chats: set[int] = set()


# ============ Helper Functions ============

def mark_chat_inaccessible(chat_id: int, session: Session = None) -> None:
    """Mark chat as inaccessible. Optionally save to DB."""
    _inaccessible_chats.add(chat_id)
    if session:
        try:
            # Save to DB as JSON list
            ConfigRepository(session).save_bot_value(
                0, BotValueTypes.Inaccessible,
                json.dumps(list(_inaccessible_chats))
            )
        except Exception as e:
            logger.error(f"Failed to save inaccessible chats: {e}")


def is_chat_accessible(chat_id: int) -> bool:
    """Check if chat is accessible (not in inaccessible list)."""
    return chat_id not in _inaccessible_chats


def unmark_chat_accessible(chat_id: int, session: Session = None) -> None:
    """Remove chat from inaccessible list (it's accessible now)."""
    if chat_id not in _inaccessible_chats:
        return
    _inaccessible_chats.discard(chat_id)
    if session:
        try:
            ConfigRepository(session).save_bot_value(
                0, BotValueTypes.Inaccessible,
                json.dumps(list(_inaccessible_chats))
            )
        except Exception as e:
            logger.error(f"Failed to save inaccessible chats: {e}")


def load_inaccessible_chats(chat_ids: list[int]) -> None:
    """Load inaccessible chats from DB (called at startup)."""
    _inaccessible_chats.clear()
    _inaccessible_chats.update(chat_ids)


async def get_chat_title(chat_id: int, bot: Bot, session: Session = None) -> str | None:
    """Get chat title from cache or API. Returns None if chat inaccessible."""
    # Skip inaccessible chats
    if chat_id in _inaccessible_chats:
        return None

    if chat_id in _chat_titles:
        return _chat_titles[chat_id]

    try:
        chat = await bot.get_chat(chat_id)
        title = chat.title or str(chat_id)
        _chat_titles[chat_id] = title
        return title
    except TelegramBadRequest:
        mark_chat_inaccessible(chat_id, session)
        return None


async def get_user_admin_chats(user_id: int, app_context: AppContext, bot: Bot, session: Session = None) -> list[tuple[int, str]]:
    """
    Get list of chats where user is an administrator.

    Uses admin_service cache for admin check, cached or parallel API calls for titles.
    Filters out inaccessible chats.
    Returns list of tuples: (chat_id, chat_title)
    """
    import asyncio

    if not app_context or not app_context.admin_service:
        return []

    # Get chats where user is admin from cache (fast)
    with app_context.admin_service._lock:
        all_chats = list(app_context.admin_service._admins.keys())

    # Filter out inaccessible chats early
    user_chats = [
        chat_id for chat_id in all_chats
        if app_context.admin_service.is_chat_admin(chat_id, user_id) and is_chat_accessible(chat_id)
    ]

    if not user_chats:
        return []

    # Fetch titles (from cache or API in parallel)
    async def get_chat_info(chat_id: int) -> tuple[int, str] | None:
        title = await get_chat_title(chat_id, bot, session)
        return (chat_id, title) if title else None

    results = await asyncio.gather(*[get_chat_info(cid) for cid in user_chats])
    return [r for r in results if r is not None]


async def verify_admin_via_api(user_id: int, chat_id: int, bot: Bot) -> bool:
    """Check if user is admin via Telegram API (real-time check)."""
    try:
        admins = await bot.get_chat_administrators(chat_id)
        return any(admin.user.id == user_id for admin in admins)
    except TelegramBadRequest:
        return False


# ============ Keyboard Builders ============

def chat_list_kb(chats: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    """Build keyboard with chat selection buttons."""
    buttons = []
    for chat_id, title in chats:
        # Truncate long titles
        display_title = title[:20] + "..." if len(title) > 20 else title
        buttons.append([
            InlineKeyboardButton(
                text=display_title,
                callback_data=AdminCallback(action="menu", chat_id=chat_id).pack()
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def chat_menu_kb(chat_id: int) -> InlineKeyboardMarkup:
    """Build main menu keyboard for a chat."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Feature Flags",
            callback_data=AdminCallback(action="flags", chat_id=chat_id).pack()
        )],
        [InlineKeyboardButton(
            text="Welcome Settings",
            callback_data=AdminCallback(action="welcome", chat_id=chat_id).pack()
        )],
        [InlineKeyboardButton(
            text="<< Back",
            callback_data=AdminCallback(action="list").pack()
        )]
    ])


def feature_flags_kb(chat_id: int, feature_flags: FeatureFlagsService) -> InlineKeyboardMarkup:
    """Build keyboard with feature toggle buttons."""
    buttons = []

    for feature_key, label in FEATURE_LABELS.items():
        is_enabled = feature_flags.is_enabled(chat_id, feature_key)
        status_icon = "ON" if is_enabled else "OFF"
        status_emoji = "+" if is_enabled else "-"

        buttons.append([
            InlineKeyboardButton(
                text=f"{status_emoji} {label}",
                callback_data=AdminCallback(action="info", chat_id=chat_id, param=feature_key).pack()
            ),
            InlineKeyboardButton(
                text=status_icon,
                callback_data=AdminCallback(action="toggle", chat_id=chat_id, param=feature_key).pack()
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="<< Back",
            callback_data=AdminCallback(action="menu", chat_id=chat_id).pack()
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def welcome_kb(chat_id: int) -> InlineKeyboardMarkup:
    """Build keyboard for welcome settings."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Edit Message",
                callback_data=AdminCallback(action="edit", chat_id=chat_id, param="msg").pack()
            ),
            InlineKeyboardButton(
                text="Edit Button",
                callback_data=AdminCallback(action="edit", chat_id=chat_id, param="btn").pack()
            )
        ],
        [InlineKeyboardButton(
            text="Delete Welcome",
            callback_data=AdminCallback(action="del", chat_id=chat_id, param="welcome").pack()
        )],
        [InlineKeyboardButton(
            text="<< Back",
            callback_data=AdminCallback(action="menu", chat_id=chat_id).pack()
        )]
    ])


# ============ Command Handler ============

@update_command_info("/admin", "Admin panel for chat management (use in private chat)")
@router.message(Command(commands=["admin"]), F.chat.type == ChatType.PRIVATE)
async def cmd_admin(message: Message, session: Session, bot: Bot, app_context: AppContext):
    """Entry point for admin panel - shows list of chats where user is admin."""
    if not app_context or not app_context.admin_service:
        await message.answer("Service unavailable.")
        return

    user_id = message.from_user.id
    chats = await get_user_admin_chats(user_id, app_context, bot, session)

    if not chats:
        await message.answer("You are not an admin in any chats managed by this bot.")
        return

    await message.answer(
        "Select a chat to manage:",
        reply_markup=chat_list_kb(chats)
    )


@router.message(Command(commands=["admin"]), F.chat.type != ChatType.PRIVATE)
async def cmd_admin_reload(message: Message, session: Session, bot: Bot, app_context: AppContext):
    """Reload admin list for current chat (group command)."""
    if not app_context or not app_context.admin_service:
        return

    chat_id = message.chat.id

    try:
        members = await bot.get_chat_administrators(chat_id)
        new_admins = [member.user.id for member in members]

        # Update cache
        app_context.admin_service.set_chat_admins(chat_id, new_admins)

        # Save to DB
        ConfigRepository(session).save_bot_value(chat_id, BotValueTypes.Admins, json.dumps(new_admins))

        reply = await message.reply("OK")

        # Delete both messages after 5 seconds
        if app_context.utils_service:
            await app_context.utils_service.sleep_and_delete(message, 5)
            await app_context.utils_service.sleep_and_delete(reply, 5)

    except TelegramBadRequest as e:
        logger.error(f"Failed to reload admins for chat {chat_id}: {e}")


# ============ Navigation Callbacks ============

@router.callback_query(AdminCallback.filter(F.action == "list"))
async def cb_show_chat_list(query: CallbackQuery, session: Session, bot: Bot, app_context: AppContext):
    """Show list of chats where user is admin."""
    if not app_context or not app_context.admin_service:
        await query.answer("Service unavailable.", show_alert=True)
        return

    user_id = query.from_user.id
    chats = await get_user_admin_chats(user_id, app_context, bot, session)

    if not chats:
        await query.answer("You are not an admin in any chats.", show_alert=True)
        return

    with suppress(TelegramBadRequest):
        await query.message.edit_text(
            "Select a chat to manage:",
            reply_markup=chat_list_kb(chats)
        )
    await query.answer()


@router.callback_query(AdminCallback.filter(F.action == "menu"))
async def cb_show_chat_menu(query: CallbackQuery, callback_data: AdminCallback, session: Session, bot: Bot, app_context: AppContext):
    """Show main menu for selected chat."""
    chat_id = callback_data.chat_id
    user_id = query.from_user.id

    if not await verify_admin_via_api(user_id, chat_id, bot):
        await query.answer("You are not an admin of this chat.", show_alert=True)
        return

    title = await get_chat_title(chat_id, bot, session)
    if not title:
        await query.answer("Chat not accessible.", show_alert=True)
        return

    with suppress(TelegramBadRequest):
        await query.message.edit_text(
            f"Settings: {title}",
            reply_markup=chat_menu_kb(chat_id)
        )
    await query.answer()


# ============ Feature Flags Callbacks ============

@router.callback_query(AdminCallback.filter(F.action == "flags"))
async def cb_show_feature_flags(query: CallbackQuery, callback_data: AdminCallback, session: Session, bot: Bot, app_context: AppContext):
    """Show feature flags for selected chat."""
    if not app_context or not app_context.feature_flags:
        await query.answer("Service unavailable.", show_alert=True)
        return

    chat_id = callback_data.chat_id

    title = await get_chat_title(chat_id, bot, session)
    if not title:
        await query.answer("Chat not accessible.", show_alert=True)
        return

    with suppress(TelegramBadRequest):
        await query.message.edit_text(
            f"Feature Flags: {title}",
            reply_markup=feature_flags_kb(chat_id, app_context.feature_flags)
        )
    await query.answer()


@router.callback_query(AdminCallback.filter(F.action == "toggle"))
async def cb_toggle_feature(query: CallbackQuery, callback_data: AdminCallback, session: Session, bot: Bot, app_context: AppContext):
    """Toggle a feature flag."""
    if not app_context or not app_context.feature_flags:
        await query.answer("Service unavailable.", show_alert=True)
        return

    chat_id = callback_data.chat_id
    feature = callback_data.param

    # Toggle the feature
    new_state = app_context.feature_flags.toggle(chat_id, feature)

    title = await get_chat_title(chat_id, bot, session) or str(chat_id)

    # Update keyboard
    with suppress(TelegramBadRequest):
        await query.message.edit_text(
            f"Feature Flags: {title}",
            reply_markup=feature_flags_kb(chat_id, app_context.feature_flags)
        )

    label = FEATURE_LABELS.get(feature, feature)
    status = "enabled" if new_state else "disabled"
    await query.answer(f"{label} {status}")


@router.callback_query(AdminCallback.filter(F.action == "info"))
async def cb_feature_info(query: CallbackQuery, callback_data: AdminCallback, app_context: AppContext):
    """Show feature description in alert popup."""
    feature = callback_data.param
    label = FEATURE_LABELS.get(feature, feature)
    description = get_feature_description(feature, app_context)

    if description:
        text = f"{label}\n\n{description}"
    else:
        text = f"{label}\n\nОписание недоступно."

    await query.answer(text, show_alert=True)


# ============ Welcome Settings Callbacks ============

@router.callback_query(AdminCallback.filter(F.action == "welcome"))
async def cb_show_welcome_settings(query: CallbackQuery, callback_data: AdminCallback, session: Session, bot: Bot, app_context: AppContext):
    """Show welcome settings for selected chat."""
    logger.debug(f"cb_show_welcome_settings called, chat_id={callback_data.chat_id}")
    if not app_context or not app_context.config_service:
        logger.warning("cb_show_welcome_settings: app_context or config_service is None")
        await query.answer("Service unavailable.", show_alert=True)
        return

    chat_id = callback_data.chat_id

    title = await get_chat_title(chat_id, bot, session)
    if not title:
        logger.warning(f"cb_show_welcome_settings: chat {chat_id} not accessible")
        await query.answer("Chat not accessible.", show_alert=True)
        return

    # Get current welcome settings
    welcome_msg = app_context.config_service.get_welcome_message(chat_id)
    welcome_btn = app_context.config_service.get_welcome_button(chat_id)

    # Format display text
    msg_display = welcome_msg[:50] + "..." if welcome_msg and len(welcome_msg) > 50 else welcome_msg
    btn_display = str(welcome_btn)[:30] if welcome_btn else None

    text_parts = [f"Welcome Settings: {title}", ""]
    text_parts.append(f"Message: {msg_display or 'Not set'}")
    text_parts.append(f"Button: {btn_display or 'Not set'}")

    with suppress(TelegramBadRequest):
        await query.message.edit_text(
            "\n".join(text_parts),
            reply_markup=welcome_kb(chat_id)
        )
    await query.answer()


@router.callback_query(AdminCallback.filter(F.action == "edit"))
async def cb_edit_welcome(query: CallbackQuery, callback_data: AdminCallback, state: FSMContext, app_context: AppContext):
    """Start editing welcome message or button."""
    chat_id = callback_data.chat_id
    edit_type = callback_data.param  # "msg" or "btn"

    # Store chat_id in FSM state
    await state.update_data(edit_chat_id=chat_id)

    if edit_type == "msg":
        await state.set_state(AdminPanelStates.waiting_welcome_message)
        prompt = "Send the new welcome message.\n\nYou can use {name} for user's name.\n\nSend /cancel to cancel."
    else:  # btn
        await state.set_state(AdminPanelStates.waiting_welcome_button)
        prompt = "Send the button text.\n\nSend /cancel to cancel."

    with suppress(TelegramBadRequest):
        await query.message.edit_text(prompt)
    await query.answer()


@router.callback_query(AdminCallback.filter(F.action == "del"))
async def cb_delete_welcome(query: CallbackQuery, callback_data: AdminCallback, session: Session, bot: Bot, app_context: AppContext):
    """Delete welcome settings."""
    if not app_context or not app_context.config_service:
        await query.answer("Service unavailable.", show_alert=True)
        return

    chat_id = callback_data.chat_id

    # Delete welcome settings from cache and DB
    app_context.config_service.remove_welcome_message(chat_id)
    app_context.config_service.remove_welcome_button(chat_id)
    ConfigRepository(session).save_bot_value(chat_id, BotValueTypes.WelcomeMessage, None)
    ConfigRepository(session).save_bot_value(chat_id, BotValueTypes.WelcomeButton, None)

    await query.answer("Welcome settings deleted.")

    # Return to chat menu
    title = await get_chat_title(chat_id, bot, session) or str(chat_id)

    with suppress(TelegramBadRequest):
        await query.message.edit_text(
            f"Settings: {title}",
            reply_markup=chat_menu_kb(chat_id)
        )


# ============ FSM Handlers ============

@router.message(Command(commands=["cancel"]), F.chat.type == ChatType.PRIVATE)
async def cmd_cancel(message: Message, state: FSMContext):
    """Cancel current FSM operation."""
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Nothing to cancel.")
        return

    await state.clear()
    await message.answer("Cancelled. Use /admin to start again.")


@router.message(AdminPanelStates.waiting_welcome_message, F.chat.type == ChatType.PRIVATE)
async def process_welcome_message(message: Message, state: FSMContext, session: Session, bot: Bot, app_context: AppContext):
    """Process new welcome message input."""
    if not app_context or not app_context.config_service:
        await message.answer("Service unavailable.")
        await state.clear()
        return

    data = await state.get_data()
    chat_id = data.get("edit_chat_id")

    if not chat_id:
        await message.answer("Error: chat not found. Use /admin to start again.")
        await state.clear()
        return

    # Save welcome message to cache and DB
    new_message = message.text or message.caption or ""
    app_context.config_service.set_welcome_message(chat_id, new_message)
    ConfigRepository(session).save_bot_value(chat_id, BotValueTypes.WelcomeMessage, new_message)

    await state.clear()

    title = await get_chat_title(chat_id, bot, session) or str(chat_id)

    await message.answer(
        f"Welcome message updated for {title}.\n\nUse /admin to continue.",
    )


@router.message(AdminPanelStates.waiting_welcome_button, F.chat.type == ChatType.PRIVATE)
async def process_welcome_button(message: Message, state: FSMContext, session: Session, bot: Bot, app_context: AppContext):
    """Process new welcome button input."""
    if not app_context or not app_context.config_service:
        await message.answer("Service unavailable.")
        await state.clear()
        return

    data = await state.get_data()
    chat_id = data.get("edit_chat_id")

    if not chat_id:
        await message.answer("Error: chat not found. Use /admin to start again.")
        await state.clear()
        return

    button_text = (message.text or "").strip()

    if not button_text:
        await message.answer("Button text cannot be empty. Try again or send /cancel.")
        return

    # Save welcome button to cache and DB (stored as plain text)
    app_context.config_service.set_welcome_button(chat_id, button_text)
    ConfigRepository(session).save_bot_value(chat_id, BotValueTypes.WelcomeButton, button_text)

    await state.clear()

    title = await get_chat_title(chat_id, bot, session) or str(chat_id)

    await message.answer(
        f"Welcome button updated for {title}.\n\nUse /admin to continue.",
    )


# ============ Register Handlers ============

def register_handlers(dp, bot):
    dp.include_router(router)
    logger.info('router admin_panel was loaded')
