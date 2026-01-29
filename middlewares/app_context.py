from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from services import app_context as app_context_module
from services.app_context import AppContext


class AppContextMiddleware(BaseMiddleware):
    def __init__(self, bot):
        self.app_context = AppContext.from_bot(bot)
        # Update singleton for backwards compatibility (used by add_bot_users, etc.)
        app_context_module.app_context = self.app_context

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        data["app_context"] = self.app_context
        return await handler(event, data)
