import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram import Bot, types
import datetime

from routers.inline import router as inline_router
from tests.conftest import RouterTestMiddleware, TEST_BOT_TOKEN
from other.global_data import global_data

@pytest.fixture(autouse=True)
async def cleanup_router():
    yield
    if inline_router.parent_router:
         inline_router._parent_router = None

@pytest.mark.asyncio
async def test_inline_query_handler(mock_server, router_app_context):
    dp = router_app_context.dispatcher
    
    # Inline handler expects session, middleware provides it.
    # RouterTestMiddleware provides session=MagicMock()
    dp.inline_query.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(inline_router)
    
    # Mock global_data info_cmd
    mock_cmds = {
        "/help": {"info": "Show help", "cmd_type": 0, "cmd_list": ""}
    }
    # global_data is imported directly in router, so we patch it or modify it.
    # Since we can't patch easily without restarting module, we assume global_data is mutable.
    original_info_cmd = global_data.info_cmd
    global_data.info_cmd = mock_cmds
    
    try:
        update = types.Update(
            update_id=1,
            inline_query=types.InlineQuery(
                id="iq1",
                from_user=types.User(id=123, is_bot=False, first_name="Test", username="test"),
                query="help",
                offset=""
            )
        )
        
        await dp.feed_update(bot=router_app_context.bot, update=update)
        
        requests = mock_server.get_requests()
        ans_req = next((r for r in requests if r["method"] == "answerInlineQuery"), None)
        assert ans_req is not None
        assert len(ans_req["data"]["results"]) > 0
        
    finally:
        global_data.info_cmd = original_info_cmd
