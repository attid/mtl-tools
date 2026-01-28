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
        if session:
            # Create new context with session but reuse stateful services
            ctx = AppContext.from_bot_session(data["bot"], session=session)
            # Reuse services that hold runtime state (loaded at startup)
            ctx.bot_state_service = self.app_context.bot_state_service
            ctx.voting_service = self.app_context.voting_service
            ctx.admin_service = self.app_context.admin_service
            ctx.notification_service = self.app_context.notification_service
            ctx.command_registry = self.app_context.command_registry
            data["app_context"] = ctx
        else:
            data["app_context"] = self.app_context
        return await handler(event, data)
