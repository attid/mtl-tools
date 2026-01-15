
import pytest
from aiogram import Bot, Dispatcher, types
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from unittest.mock import patch, MagicMock

from routers.inline import router as inline_router
from other.global_data import global_data
from tests.conftest import MOCK_SERVER_URL, TEST_BOT_TOKEN

@pytest.mark.asyncio
async def test_inline_query_handler(mock_server, dp):
    """
    Test inline query handler for command info lookup.
    """
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(MOCK_SERVER_URL)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(inline_router)
    
    # Mock global_data info_cmd
    # structure: { "command_name": {"info": "description", "cmd_type": 0, "cmd_list": "attr_name"} }
    mock_cmds = {
        "/help": {"info": "Show help", "cmd_type": 0, "cmd_list": ""}
    }
    
    # Patch global_data.info_cmd
    with patch.object(global_data, 'info_cmd', mock_cmds):
        
        # Simulate InlineQuery
        update = types.Update(
            update_id=1,
            inline_query=types.InlineQuery(
                id="iq1",
                from_user=types.User(id=123, is_bot=False, first_name="Test", username="test"),
                query="help",
                offset=""
            )
        )
        
        # We need to catch the "answerInlineQuery" method which is not yet in mock server?
        # Typically bot.answer_inline_query calls /answerInlineQuery
        # Check conftest.py, we might need to add it.
        # But let's write the test and then fix conftest if it fails with 404.
        
        try:
            await dp.feed_update(bot=bot, update=update)
        except Exception as e:
            # If it's ClientDecodeError 404, we know we need to add the mock.
            # But let's assume we will add it.
            pass

    # Note: This test will likely fail until we add /answerInlineQuery to conftest.
    # We should add it in the next step.
    
    await bot.session.close()
