"""Middleware for resolving user_id from channel links.

When admins send commands from a channel (sender_chat), this middleware
resolves the real user_id by looking up channel-to-user mappings.
"""
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware, Bot
from aiogram.types import TelegramObject, Message, CallbackQuery

from services.app_context import AppContext
from services.skyuser import SkyUser
from other.constants import MTLChats
from loguru import logger


class UserResolverMiddleware(BaseMiddleware):
    """Resolves user_id and puts it in data['skyuser'].

    Resolution logic:
    1. If event.from_user exists -> use from_user.id
    2. If event.sender_chat exists (message from channel):
       - Check channel_link_service.get_user_for_channel(sender_chat.id)
       - If link exists -> return owner_id
       - If no link -> return None
    """

    def __init__(self, app_context: AppContext, bot: Bot):
        self.app_context = app_context
        self.bot = bot

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        skyuser = self._resolve_user(event)
        data["skyuser"] = skyuser
        return await handler(event, data)

    def _resolve_user(self, event: TelegramObject) -> SkyUser:
        """Resolve SkyUser from the event.

        Args:
            event: The Telegram event (Message or CallbackQuery).

        Returns:
            The resolved SkyUser.
        """
        user_id = None
        username = None
        chat_id = None
        sender_chat_id = None

        if isinstance(event, Message):
            chat_id = event.chat.id if event.chat else None
            if event.from_user:
                if event.from_user.id == MTLChats.Channel_Bot and event.sender_chat:
                    sender_chat_id = event.sender_chat.id
                    user_id = self._resolve_from_channel(sender_chat_id)
                    username = self._resolve_username_from_channel(sender_chat_id)
                    logger.debug(
                        "skyuser.resolve: channel_bot sender_chat id={} -> user_id={} username={} chat_id={}",
                        sender_chat_id,
                        user_id,
                        username,
                        chat_id,
                    )
                else:
                    user_id = event.from_user.id
                    username = event.from_user.username
                    logger.debug(
                        "skyuser.resolve: from_user id={} username={} chat_id={} sender_chat_id={}",
                        user_id,
                        username,
                        chat_id,
                        event.sender_chat.id if event.sender_chat else None,
                    )
            elif event.sender_chat:
                sender_chat_id = event.sender_chat.id
                user_id = self._resolve_from_channel(sender_chat_id)
                username = self._resolve_username_from_channel(sender_chat_id)
                logger.debug(
                    "skyuser.resolve: sender_chat id={} -> user_id={} username={} chat_id={}",
                    sender_chat_id,
                    user_id,
                    username,
                    chat_id,
                )
        elif isinstance(event, CallbackQuery):
            if event.message and event.message.chat:
                chat_id = event.message.chat.id
            if event.from_user:
                user_id = event.from_user.id
                username = event.from_user.username
                logger.debug(
                    "skyuser.resolve: callback from_user id={} username={} chat_id={}",
                    user_id,
                    username,
                    chat_id,
                )
        else:
            if hasattr(event, "from_user") and event.from_user:
                user_id = event.from_user.id
                username = event.from_user.username
                logger.debug(
                    "skyuser.resolve: generic from_user id={} username={}",
                    user_id,
                    username,
                )
            if hasattr(event, "message") and event.message and event.message.chat:
                chat_id = event.message.chat.id
            if hasattr(event, "chat") and event.chat:
                chat_id = event.chat.id

        return SkyUser(
            user_id=user_id,
            username=username,
            chat_id=chat_id,
            sender_chat_id=sender_chat_id,
            bot=self.bot,
            app_context=self.app_context,
        )

    def _resolve_from_channel(self, channel_id: int) -> int | None:
        """Resolve user_id from channel link.

        Args:
            channel_id: The channel ID to look up.

        Returns:
            The linked user_id if found, None otherwise.
        """
        if not self.app_context.channel_link_service:
            return None
        return self.app_context.channel_link_service.get_user_for_channel(channel_id)

    def _resolve_username_from_channel(self, channel_id: int) -> str | None:
        """Resolve username from channel link, if available."""
        if not self.app_context.channel_link_service:
            return None
        return self.app_context.channel_link_service.get_username_for_channel(channel_id)
