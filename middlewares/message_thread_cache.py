from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject


class MessageThreadCacheMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Message):
            app_context = data.get("app_context")
            cache_service = getattr(app_context, "message_thread_cache_service", None) if app_context else None
            if cache_service and event.chat and event.message_thread_id:
                await cache_service.remember_message_context(
                    chat_id=event.chat.id,
                    message_id=event.message_id,
                    thread_id=event.message_thread_id,
                    user_id=event.from_user.id if event.from_user else None,
                    username=event.from_user.username if event.from_user else None,
                    full_name=event.from_user.full_name if event.from_user else None,
                    sender_chat_id=event.sender_chat.id if event.sender_chat else None,
                    sender_chat_title=event.sender_chat.title if event.sender_chat else None,
                )
        return await handler(event, data)
