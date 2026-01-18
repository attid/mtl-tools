import asyncio
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, ReactionTypeEmoji
from loguru import logger

from other.openrouter_reactions import label_to_emoji
from other.openrouter_service import classify_message

ALLOWED_CHAT_IDS = {
    -1001908537713,
    -1001908537777,
}


class EmojiReactionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        if self._should_process(event):
            asyncio.create_task(self._handle_reaction(event))
        return await handler(event, data)

    @staticmethod
    def _should_process(message: Message) -> bool:
        if message.chat.id not in ALLOWED_CHAT_IDS:
            return False
        if not message.text:
            return False
        if message.from_user and message.from_user.is_bot:
            return False
        return True

    async def _handle_reaction(self, message: Message) -> None:
        label = await classify_message(message.text)
        emoji = label_to_emoji(label)
        if not emoji:
            return
        try:
            await message.react([ReactionTypeEmoji(emoji=emoji)])
        except Exception as exc:
            logger.warning(f"Failed to set reaction: {exc}")
