import asyncio
import datetime
from unittest.mock import AsyncMock, patch

import pytest
from aiogram import Bot, Dispatcher, Router, types
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer

from middlewares.emoji_reaction import EmojiReactionMiddleware
from tests.conftest import MOCK_SERVER_URL, TEST_BOT_TOKEN, MockDbMiddleware


def _build_message(chat_id: int, text: str | None = None, photo=None) -> types.Message:
    return types.Message(
        message_id=1,
        date=datetime.datetime.now(),
        chat=types.Chat(id=chat_id, type="supergroup", title="Group"),
        from_user=types.User(id=123, is_bot=False, first_name="User"),
        text=text,
        photo=photo,
    )


async def _feed_message(dp: Dispatcher, bot: Bot, message: types.Message) -> None:
    update = types.Update(update_id=1, message=message)
    await dp.feed_update(bot=bot, update=update)
    await asyncio.sleep(0.01)


@pytest.mark.asyncio
async def test_reaction_in_allowed_chat(mock_server, dp):
    session = AiohttpSession(api=TelegramAPIServer.from_base(MOCK_SERVER_URL))
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    router = Router()

    @router.message()
    async def handle_message(message: types.Message):
        return message

    dp.include_router(router)
    dp.message.middleware(MockDbMiddleware())
    dp.message.middleware(EmojiReactionMiddleware())

    with patch("middlewares.emoji_reaction.classify_message", new_callable=AsyncMock) as mock_classify:
        mock_classify.return_value = "backseat"
        message = _build_message(chat_id=-1001908537713, text="Тебе надо сделать это по-другому")
        await _feed_message(dp, bot, message)

    reaction_req = next((r for r in mock_server if r["method"] == "setMessageReaction"), None)
    assert reaction_req is not None

    await bot.session.close()


@pytest.mark.asyncio
async def test_no_reaction_in_other_chat(mock_server, dp):
    session = AiohttpSession(api=TelegramAPIServer.from_base(MOCK_SERVER_URL))
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    router = Router()

    @router.message()
    async def handle_message(message: types.Message):
        return message

    dp.include_router(router)
    dp.message.middleware(MockDbMiddleware())
    dp.message.middleware(EmojiReactionMiddleware())

    with patch("middlewares.emoji_reaction.classify_message", new_callable=AsyncMock) as mock_classify:
        message = _build_message(chat_id=-1001908537999, text="Тебе надо сделать это по-другому")
        await _feed_message(dp, bot, message)
        mock_classify.assert_not_called()

    reaction_req = next((r for r in mock_server if r["method"] == "setMessageReaction"), None)
    assert reaction_req is None

    await bot.session.close()


@pytest.mark.asyncio
async def test_no_reaction_on_photo(mock_server, dp):
    session = AiohttpSession(api=TelegramAPIServer.from_base(MOCK_SERVER_URL))
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    router = Router()

    @router.message()
    async def handle_message(message: types.Message):
        return message

    dp.include_router(router)
    dp.message.middleware(MockDbMiddleware())
    dp.message.middleware(EmojiReactionMiddleware())

    with patch("middlewares.emoji_reaction.classify_message", new_callable=AsyncMock) as mock_classify:
        photo = [types.PhotoSize(file_id="1", file_unique_id="1", width=1, height=1)]
        message = _build_message(chat_id=-1001908537713, text=None, photo=photo)
        await _feed_message(dp, bot, message)
        mock_classify.assert_not_called()

    reaction_req = next((r for r in mock_server if r["method"] == "setMessageReaction"), None)
    assert reaction_req is None

    await bot.session.close()
