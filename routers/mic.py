import asyncio
import html
from dataclasses import dataclass

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from loguru import logger

from services.command_registry_service import update_command_info

router = Router()


class MicCallbackData(CallbackData, prefix="mic"):
    action: str  # "take" | "release"
    owner_id: int


@dataclass
class _MicSessionState:
    topic: str
    owner_id: int | None = None
    owner_label: str | None = None


def _session_key(message: Message) -> tuple[int, int, int]:
    topic_id = int(getattr(message, "message_thread_id", 0) or 0)
    return int(message.chat.id), topic_id, int(message.message_id)


def _format_user_label(user) -> str:
    if getattr(user, "username", None):
        return f"@{user.username}"
    # aiogram.User has .full_name
    return getattr(user, "full_name", None) or getattr(user, "first_name", None) or str(getattr(user, "id", ""))


def _extract_topic_from_text(text: str | None) -> str:
    if not text:
        return ""
    for line in text.splitlines():
        if line.startswith("Тема:"):
            return line[len("Тема:"):].strip()
    return ""


def _extract_owner_label_from_button(message: Message) -> str | None:
    try:
        rm = message.reply_markup
        if not rm or not rm.inline_keyboard:
            return None
        btn = rm.inline_keyboard[0][0]
        text = btn.text or ""
        prefix = "🔴 Взято:"
        if text.startswith(prefix):
            return text[len(prefix):].strip() or None
        return None
    except Exception:
        return None


def _render_text(topic: str, owner_label: str | None) -> str:
    topic = html.escape(topic.strip())
    owner_label = html.escape(owner_label) if owner_label else None
    lines = ["🎙 Микрофон", f"Тема: {topic}" if topic else "Тема: (без темы)"]
    if owner_label:
        lines.append(f"Статус: взято {owner_label}")
    else:
        lines.append("Статус: свободно")
    return "\n".join(lines)


def _render_keyboard_free() -> InlineKeyboardMarkup:
    cb = MicCallbackData(action="take", owner_id=0).pack()
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🟢 Взять", callback_data=cb)]]
    )


def _render_keyboard_taken(owner_id: int, owner_label: str) -> InlineKeyboardMarkup:
    # Keep label short to avoid oversized buttons.
    label = owner_label.strip()
    if len(label) > 32:
        label = label[:29] + "..."
    cb = MicCallbackData(action="release", owner_id=int(owner_id)).pack()
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=f"🔴 Взято: {label}", callback_data=cb)]]
    )


_locks: dict[tuple[int, int, int], asyncio.Lock] = {}
_sessions: dict[tuple[int, int, int], _MicSessionState] = {}


def _get_lock(key: tuple[int, int, int]) -> asyncio.Lock:
    lock = _locks.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _locks[key] = lock
    return lock


@update_command_info("/mic", "Создать микрофон-сессию: /mic <тема>")
@router.message(Command(commands=["mic"]))
async def cmd_mic(message: Message) -> None:
    text = message.text or ""
    parts = text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer("Формат: <code>/mic &lt;тема&gt;</code>")
        return

    topic = parts[1].strip()
    msg = await message.answer(_render_text(topic, owner_label=None), reply_markup=_render_keyboard_free())

    key = _session_key(msg)
    _sessions[key] = _MicSessionState(topic=topic, owner_id=None, owner_label=None)


@router.callback_query(MicCallbackData.filter())
async def cb_mic(callback: CallbackQuery, callback_data: MicCallbackData, bot: Bot) -> None:
    if not callback.message:
        await callback.answer()
        return

    key = _session_key(callback.message)
    lock = _get_lock(key)
    async with lock:
        state = _sessions.get(key)
        if state is None:
            # Best-effort recovery from the message itself (after restart).
            topic = _extract_topic_from_text(callback.message.text) or ""
            owner_id = int(callback_data.owner_id) if callback_data.action == "release" and callback_data.owner_id else None
            owner_label = _extract_owner_label_from_button(callback.message)
            state = _MicSessionState(topic=topic, owner_id=owner_id, owner_label=owner_label)
            _sessions[key] = state

        user = callback.from_user
        user_id = int(user.id)

        if callback_data.action == "take":
            if state.owner_id is not None:
                label = state.owner_label or str(state.owner_id)
                await callback.answer(f"Занято: {label}")
                return

            owner_label = _format_user_label(user)
            state.owner_id = user_id
            state.owner_label = owner_label

            text = _render_text(state.topic, owner_label=owner_label)
            kb = _render_keyboard_taken(owner_id=user_id, owner_label=owner_label)
            try:
                await bot.edit_message_text(
                    chat_id=callback.message.chat.id,
                    message_id=callback.message.message_id,
                    text=text,
                    reply_markup=kb,
                )
            except Exception as e:
                logger.warning(f"Failed to edit mic message on take: {e}")
            await callback.answer("Взято")
            return

        if callback_data.action == "release":
            if state.owner_id is None:
                await callback.answer("Уже свободно")
                return

            if user_id != state.owner_id:
                label = state.owner_label or str(state.owner_id)
                await callback.answer(f"Занято: {label}")
                return

            state.owner_id = None
            state.owner_label = None

            text = _render_text(state.topic, owner_label=None)
            kb = _render_keyboard_free()
            try:
                await bot.edit_message_text(
                    chat_id=callback.message.chat.id,
                    message_id=callback.message.message_id,
                    text=text,
                    reply_markup=kb,
                )
            except Exception as e:
                logger.warning(f"Failed to edit mic message on release: {e}")
            await callback.answer("Свободно")
            return

        await callback.answer()


def register_handlers(dp, bot):
    dp.include_router(router)
