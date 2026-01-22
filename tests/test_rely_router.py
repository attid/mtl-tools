
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from decimal import Decimal
from aiogram import Bot, types, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.dispatcher.middlewares.base import BaseMiddleware
import datetime

from routers.rely_router import (
    router as rely_router, 
    Deal, 
    DealParticipantEntry, 
    Holder,
    RELY_DEAL_CHAT_ID
)
from tests.conftest import TEST_BOT_TOKEN

class MockDbMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        data["session"] = MagicMock()
        return await handler(event, data)

@pytest.fixture(autouse=True)
async def cleanup_router():
    yield
    if rely_router.parent_router:
         rely_router._parent_router = None

@pytest.mark.asyncio
async def test_deal_command(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(rely_router)
    
    # Mock Repositories
    with patch("routers.rely_router.GristDealRepository") as MockDealRepo, \
         patch("routers.rely_router.GristDealParticipantRepository") as MockParticipantRepo, \
         patch("routers.rely_router.GristHolderRepository") as MockHolderRepo:
        
        # Setup mocks
        deal_repo = MockDealRepo.return_value
        participant_repo = MockParticipantRepo.return_value
        holder_repo = MockHolderRepo.return_value
        
        # Mock deal creation/retrieval
        deal_repo.get_or_create_deal = AsyncMock(return_value=(
            Deal(id=101, url="https://t.me/c/123/456", checked=False), 
            True # is_new
        ))
        
        # Mock holder
        holder_repo.get_or_create_holder = AsyncMock(return_value=Holder(id=202, tg_username="@user"))
        
        # Mock participant entry
        participant_repo.add_participant_entry = AsyncMock(return_value=DealParticipantEntry(
            id=303, deal_id=101, holder_id=202, amount=Decimal("0.5")
        ))
        
        # Create message structure: A reply to another message
        reply_to = types.Message(
            message_id=5,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='supergroup', username="group"),
            from_user=types.User(id=999, is_bot=False, first_name="OrigUser", username="origuser"),
            text="Original offer"
        )
        
        user = types.User(id=789, is_bot=False, first_name="Investor", username="investor")
        
        update = types.Update(
            update_id=1,
            message=types.Message(
                message_id=6,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup', username="group"),
                from_user=user,
                text="/deal 0.5",
                reply_to_message=reply_to
            )
        )
        
        await dp.feed_update(bot=bot, update=update)
        
        # Verify interactions
        deal_repo.get_or_create_deal.assert_called_once()
        holder_repo.get_or_create_holder.assert_called_once_with("investor", 789)
        participant_repo.add_participant_entry.assert_called_once()
        
        # Verify notification sent to rely chat (msg to RELY_DEAL_CHAT_ID)
        # Note: logic sends notification if is_new=True
        req = next((r for r in mock_server if r["method"] == "sendMessage" and str(r["data"]["chat_id"]) == str(RELY_DEAL_CHAT_ID)), None)
        assert req is not None
        assert "Создана новая сделка #101" in req["data"]["text"]
        
        # Verify rely to user
        user_reply = next((r for r in mock_server if r["method"] == "sendMessage" and str(r["data"]["chat_id"]) == "123" and "успешно обработана" in r["data"]["text"]), None)
        assert user_reply is not None

    await bot.session.close()

@pytest.mark.asyncio
async def test_resolve_command(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(rely_router)

    with patch("routers.rely_router.DealService") as MockService:
        service_instance = MockService.return_value
        service_instance.process_resolve = AsyncMock()
        
        update = types.Update(
            update_id=2,
            message=types.Message(
                message_id=10,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup', username="group"),
                from_user=types.User(id=999, is_bot=False, first_name="Admin", username="admin"),
                text="/resolve Done",
                reply_to_message=types.Message(
                    message_id=5,
                    date=datetime.datetime.now(),
                    chat=types.Chat(id=123, type='supergroup', username="group"),
                    text="Deal msg"
                )
            )
        )
        
        await dp.feed_update(bot=bot, update=update)
        
        # Verify service call
        service_instance.process_resolve.assert_called_once()
        call_args = service_instance.process_resolve.call_args[1]
        assert call_args["user_display"] == "@admin"
        assert call_args["additional_text"] == "Done"

    await bot.session.close()
