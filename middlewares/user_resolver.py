"""Middleware for resolving user_id from channel links.

When admins send commands from a channel (sender_chat), this middleware
resolves the real user_id by looking up channel-to-user mappings.
"""
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from services.app_context import AppContext


class UserResolverMiddleware(BaseMiddleware):
    """Resolves user_id and puts it in data['resolved_user_id'].

    Resolution logic:
    1. If event.from_user exists -> use from_user.id
    2. If event.sender_chat exists (message from channel):
       - Check channel_link_service.get_user_for_channel(sender_chat.id)
       - If link exists -> return owner_id
       - If no link -> return None
    """

    def __init__(self, app_context: AppContext):
        self.app_context = app_context

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        resolved_user_id = self._resolve_user_id(event)
        data["resolved_user_id"] = resolved_user_id
        return await handler(event, data)

    def _resolve_user_id(self, event: TelegramObject) -> int | None:
        """Resolve the user_id from the event.

        Args:
            event: The Telegram event (Message or CallbackQuery).

        Returns:
            The resolved user_id, or None if cannot be resolved.
        """
        # Handle Message events
        if isinstance(event, Message):
            # If from_user exists, use it directly
            if event.from_user:
                return event.from_user.id

            # If sender_chat exists (message sent as channel)
            if event.sender_chat:
                return self._resolve_from_channel(event.sender_chat.id)

            return None

        # Handle CallbackQuery events
        if isinstance(event, CallbackQuery):
            if event.from_user:
                return event.from_user.id
            return None

        # For other event types, try to get from_user attribute
        if hasattr(event, 'from_user') and event.from_user:
            return event.from_user.id

        return None

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
