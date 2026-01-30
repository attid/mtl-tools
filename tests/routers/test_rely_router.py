import pytest
from aiogram import types
import datetime

from routers.rely_router import router as rely_router
from tests.conftest import RouterTestMiddleware
from other.grist_tools import grist_manager

@pytest.fixture(autouse=True)
async def cleanup_router():
    yield
    if rely_router.parent_router:
         rely_router._parent_router = None

@pytest.fixture(autouse=True)
async def reset_grist_session():
    # Close existing session if any to avoid event loop mismatch
    if grist_manager.session_manager.session:
        if not grist_manager.session_manager.session.closed:
            await grist_manager.session_manager.session.close()
        grist_manager.session_manager.session = None
    yield
    if grist_manager.session_manager.session:
        if not grist_manager.session_manager.session.closed:
            await grist_manager.session_manager.session.close()
        grist_manager.session_manager.session = None

@pytest.mark.asyncio
async def test_deal_command(mock_telegram, router_app_context, mock_grist, grist_server_config, monkeypatch):
    # Redirect Grist calls to the mock server with correct path prefix
    monkeypatch.setattr("routers.rely_router.GRIST_BASE_URL", f"{grist_server_config['url']}/api/docs")

    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(rely_router)
    
    # Setup initial data in mock_grist if needed (none needed for new deal creation)
    
    # Use a proper supergroup ID so get_url() works natively
    chat_id = -1001234567890
    chat_url_id = 1234567890 # what appears in t.me/c/... links
    
    reply_to = types.Message(
        message_id=5,
        date=datetime.datetime.now(),
        chat=types.Chat(id=chat_id, type='supergroup', title="Group"),
        from_user=types.User(id=999, is_bot=False, first_name="Orig"),
        text="Offer"
    )
    # No need to mock get_url, aiogram computes it from chat_id/message_id
    expected_url = f"https://t.me/c/{chat_url_id}/5"

    update = types.Update(
        update_id=1,
        message=types.Message(
            message_id=6,
            date=datetime.datetime.now(),
            chat=types.Chat(id=chat_id, type='supergroup', title="Group"),
            from_user=types.User(id=789, is_bot=False, first_name="User", username="user"),
            text="/deal 0.5",
            reply_to_message=reply_to
        )
    )
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    # Verify records were created in mock_grist
    # Deals table: "Deals"
    assert "Deals" in mock_grist.records
    assert len(mock_grist.records["Deals"]) == 1
    assert mock_grist.records["Deals"][0]["fields"]["Message"] == expected_url
    
    # Holders table: "Holders"
    assert "Holders" in mock_grist.records
    assert len(mock_grist.records["Holders"]) == 1
    assert mock_grist.records["Holders"][0]["fields"]["Telegram"] == "@user"
    
    # Conditions table: "Conditions"
    assert "Conditions" in mock_grist.records
    assert len(mock_grist.records["Conditions"]) == 1
    assert str(mock_grist.records["Conditions"][0]["fields"]["Amount"]) == "0.5"

    requests = mock_telegram.get_requests()
    assert any(r["method"] == "setMessageReaction" for r in requests)

@pytest.mark.asyncio
async def test_resolve_command(mock_telegram, router_app_context, mock_grist, grist_server_config, monkeypatch):
    monkeypatch.setattr("routers.rely_router.GRIST_BASE_URL", f"{grist_server_config['url']}/api/docs")

    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(rely_router)

    chat_id = -1001234567890
    chat_url_id = 1234567890
    expected_deal_url = f"https://t.me/c/{chat_url_id}/5"

    # Pre-populate a deal to resolve
    mock_grist.records["Deals"] = [{
        "id": 101,
        "fields": {
            "Message": expected_deal_url,
            "Checked": False
        }
    }]
    
    update = types.Update(
        update_id=2,
        message=types.Message(
            message_id=10,
            date=datetime.datetime.now(),
            chat=types.Chat(id=chat_id, type='supergroup', title="Group"),
            from_user=types.User(id=999, is_bot=False, first_name="Admin", username="admin"),
            text="/resolve Done",
            reply_to_message=types.Message(
                message_id=5,
                date=datetime.datetime.now(),
                chat=types.Chat(id=chat_id, type='supergroup', title="Group"),
                text="Deal"
            )
        )
    )
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    # Check that notification was sent (sendMessage to RELY_DEAL_CHAT_ID)
    requests = mock_telegram.get_requests()
    # Looking for sendMessage with text containing "#101"
    resolve_notifications = [
        r for r in requests 
        if r["method"] == "sendMessage" and "#101" in r["data"]["text"]
    ]
    assert len(resolve_notifications) > 0
    assert any(r["method"] == "setMessageReaction" for r in requests)
