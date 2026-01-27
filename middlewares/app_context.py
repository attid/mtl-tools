from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from services.app_context import AppContext


class AppContextMiddleware(BaseMiddleware):
    def __init__(self, bot):
        self.app_context = AppContext.from_bot_session(bot)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        session = data.get("session")
        data["app_context"] = (
            AppContext.from_bot_session(data["bot"], session=session)
            if session
            else self.app_context
        )
        return await handler(event, data)
