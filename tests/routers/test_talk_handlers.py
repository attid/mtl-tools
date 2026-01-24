import pytest
import datetime
from aiogram import types

from routers.talk_handlers import router as talk_router, my_talk_message
from tests.conftest import RouterTestMiddleware
from other.global_data import global_data

@pytest.fixture(autouse=True)
async def cleanup_router():
    yield
    if talk_router.parent_router:
         talk_router._parent_router = None
    my_talk_message.clear()

@pytest.mark.asyncio
async def test_skynet_command(mock_telegram, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(talk_router)
    
    router_app_context.ai_service.talk.return_value = "I am Skynet"
    
    update = types.Update(
        update_id=1,
        message=types.Message(
            message_id=1,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='private'),
            from_user=types.User(id=123, is_bot=False, first_name="User", username="user"),
            text="/skynet hello"
        )
    )
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    assert router_app_context.ai_service.talk.called
    requests = mock_telegram.get_requests()
    assert any("I am Skynet" in r["data"]["text"] for r in requests if r["method"] == "sendMessage")

@pytest.mark.asyncio
async def test_img_command(mock_telegram, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(talk_router)
    
    global_data.skynet_img.clear()
    global_data.skynet_img.append("@user")
    
    file_bytes = b"img"
    mock_telegram.add_file("img1", file_bytes, file_path="files/img.png")
    image_url = f"{mock_telegram.base_url}/file/bot{router_app_context.bot.token}/files/img.png"
    router_app_context.ai_service.generate_image.return_value = [image_url]
    
    update = types.Update(
        update_id=2,
        message=types.Message(
            message_id=2,
            date=datetime.datetime.now(),
            chat=types.Chat(id=456, type='supergroup', title="Group"),
            from_user=types.User(id=123, is_bot=False, first_name="User", username="user"),
            text="/img cat"
        )
    )
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    assert router_app_context.ai_service.generate_image.called
    requests = mock_telegram.get_requests()
    assert any(r["method"] == "sendPhoto" for r in requests)

@pytest.mark.asyncio
async def test_comment_command(mock_telegram, router_app_context):
    dp = router_app_context.dispatcher
    dp.message.middleware(RouterTestMiddleware(router_app_context))
    dp.include_router(talk_router)
    
    router_app_context.ai_service.talk_get_comment.return_value = "Cool!"
    
    reply_msg = types.Message(
        message_id=5,
        date=datetime.datetime.now(),
        chat=types.Chat(id=456, type='supergroup', title="Group"),
        from_user=types.User(id=789, is_bot=False, first_name="Other", username="other"),
        text="Check this"
    )
    
    update = types.Update(
        update_id=3,
        message=types.Message(
            message_id=6,
            date=datetime.datetime.now(),
            chat=types.Chat(id=456, type='supergroup', title="Group"),
            from_user=types.User(id=123, is_bot=False, first_name="User", username="user"),
            text="/comment",
            reply_to_message=reply_msg
        )
    )
    
    await dp.feed_update(bot=router_app_context.bot, update=update)
    
    assert router_app_context.ai_service.talk_get_comment.called
    requests = mock_telegram.get_requests()
    assert any("Cool!" in r["data"]["text"] for r in requests if r["method"] == "sendMessage")
