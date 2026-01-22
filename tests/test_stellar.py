
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from aiogram import Bot, types, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.dispatcher.middlewares.base import BaseMiddleware
import datetime

from routers.stellar import router as stellar_router
from tests.conftest import TEST_BOT_TOKEN
from other.global_data import global_data

class MockDbMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        data["session"] = MagicMock()
        return await handler(event, data)

def build_bot(mock_server):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    return bot

@pytest.fixture(autouse=True)
async def cleanup_router():
    yield
    if stellar_router.parent_router:
         stellar_router._parent_router = None

@pytest.mark.asyncio
async def test_fee_command(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(stellar_router)
    
    with patch("routers.stellar.cmd_check_fee", return_value="100-200 stroops"):
        
        update = types.Update(
            update_id=1,
            message=types.Message(
                message_id=1,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup', title="Group"),
                from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                text="/fee"
            )
        )
        
        await dp.feed_update(bot=bot, update=update)
        
        req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
        assert req is not None
        assert "Комиссия" in req["data"]["text"]
        assert "100-200 stroops" in req["data"]["text"]

    await bot.session.close()

@pytest.mark.asyncio
async def test_balance_command(mock_server, dp):
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(mock_server.base_url)
    )
    bot = Bot(token=TEST_BOT_TOKEN, session=session)
    dp.include_router(stellar_router)
    
    # Mock image generation and FSInputFile
    with patch("routers.stellar.get_cash_balance", return_value="Balance info"), \
         patch("routers.stellar.create_image_with_text"), \
         patch("routers.stellar.FSInputFile") as MockFSFile:
        
        MockFSFile.return_value = "mock_file_id"
        
        update = types.Update(
            update_id=2,
            message=types.Message(
                message_id=2,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup', title="Group"),
                from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                text="/balance"
            )
        )
        
        await dp.feed_update(bot=bot, update=update)
        
        req = next((r for r in mock_server if r["method"] == "sendPhoto"), None)
        assert req is not None
        assert req["data"]["photo"] == "mock_file_id"

    await bot.session.close()

@pytest.mark.asyncio
async def test_decode_command(mock_server, dp):
    bot = build_bot(mock_server)
    dp.include_router(stellar_router)
    
    with patch("routers.stellar.decode_xdr", return_value=["Decoded", "XDR"]), \
         patch("routers.stellar.check_url_xdr", return_value=["Url", "XDR"]):
        
        # Test normal decode
        update = types.Update(
            update_id=3,
            message=types.Message(
                message_id=3,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup', title="Group"),
                from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                text="/decode AAAA..."
            )
        )
        
        await dp.feed_update(bot=bot, update=update)
        
        req = next((r for r in mock_server if r["method"] == "sendMessage" and "Decoded" in r["data"]["text"]), None)
        assert req is not None
        
        # Test url decode
        update_url = types.Update(
            update_id=4,
            message=types.Message(
                message_id=4,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup', title="Group"),
                from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                text="/decode https://eurmtl.me/tools?xdr=AAAA..."
            )
        )
        
        await dp.feed_update(bot=bot, update=update_url)
        
        req_url = next((r for r in mock_server if r["method"] == "sendMessage" and "Url" in r["data"]["text"]), None)
        assert req_url is not None

    await bot.session.close()

@pytest.mark.asyncio
async def test_show_bim_command(mock_server, dp):
    bot = build_bot(mock_server)
    dp.include_router(stellar_router)
    dp.message.middleware(MockDbMiddleware())

    with patch("routers.stellar.cmd_show_bim", new_callable=AsyncMock, return_value="BIM info"):
        update = types.Update(
            update_id=5,
            message=types.Message(
                message_id=5,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup', title="Group"),
                from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                text="/show_bim"
            )
        )

        await dp.feed_update(bot=bot, update=update)

        req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
        assert req is not None
        assert "BIM info" in req["data"]["text"]

    await bot.session.close()

@pytest.mark.asyncio
async def test_do_council_not_admin(mock_server, dp):
    bot = build_bot(mock_server)
    dp.include_router(stellar_router)
    dp.message.middleware(MockDbMiddleware())

    with patch("routers.stellar.is_skynet_admin", return_value=False):
        update = types.Update(
            update_id=6,
            message=types.Message(
                message_id=6,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup', title="Group"),
                from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                text="/do_council"
            )
        )

        await dp.feed_update(bot=bot, update=update)

        req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
        assert req is not None
        assert "You are not my admin" in req["data"]["text"]

    await bot.session.close()

@pytest.mark.asyncio
async def test_do_bim_not_admin(mock_server, dp):
    bot = build_bot(mock_server)
    dp.include_router(stellar_router)
    dp.message.middleware(MockDbMiddleware())

    with patch("routers.stellar.is_skynet_admin", return_value=False):
        update = types.Update(
            update_id=7,
            message=types.Message(
                message_id=7,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup', title="Group"),
                from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                text="/do_bim"
            )
        )

        await dp.feed_update(bot=bot, update=update)

        req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
        assert req is not None
        assert "You are not my admin" in req["data"]["text"]

    await bot.session.close()

@pytest.mark.asyncio
async def test_do_resend_not_admin(mock_server, dp):
    bot = build_bot(mock_server)
    dp.include_router(stellar_router)
    dp.message.middleware(MockDbMiddleware())

    with patch("routers.stellar.is_skynet_admin", return_value=False):
        update = types.Update(
            update_id=8,
            message=types.Message(
                message_id=8,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup', title="Group"),
                from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                text="/do_resend 1"
            )
        )

        await dp.feed_update(bot=bot, update=update)

        req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
        assert req is not None
        assert "You are not my admin" in req["data"]["text"]

    await bot.session.close()

@pytest.mark.asyncio
async def test_do_all_not_admin(mock_server, dp):
    bot = build_bot(mock_server)
    dp.include_router(stellar_router)

    with patch("routers.stellar.is_skynet_admin", return_value=False):
        update = types.Update(
            update_id=9,
            message=types.Message(
                message_id=9,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup', title="Group"),
                from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                text="/do_all"
            )
        )

        await dp.feed_update(bot=bot, update=update)

        req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
        assert req is not None
        assert "You are not my admin" in req["data"]["text"]

    await bot.session.close()

@pytest.mark.asyncio
async def test_do_div_not_admin(mock_server, dp):
    bot = build_bot(mock_server)
    dp.include_router(stellar_router)
    dp.message.middleware(MockDbMiddleware())

    with patch("routers.stellar.is_skynet_admin", return_value=False):
        update = types.Update(
            update_id=10,
            message=types.Message(
                message_id=10,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup', title="Group"),
                from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                text="/do_div"
            )
        )

        await dp.feed_update(bot=bot, update=update)

        req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
        assert req is not None
        assert "You are not my admin" in req["data"]["text"]

    await bot.session.close()

@pytest.mark.asyncio
async def test_do_sats_div_not_admin(mock_server, dp):
    bot = build_bot(mock_server)
    dp.include_router(stellar_router)
    dp.message.middleware(MockDbMiddleware())

    with patch("routers.stellar.is_skynet_admin", return_value=False):
        update = types.Update(
            update_id=11,
            message=types.Message(
                message_id=11,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup', title="Group"),
                from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                text="/do_sats_div"
            )
        )

        await dp.feed_update(bot=bot, update=update)

        req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
        assert req is not None
        assert "You are not my admin" in req["data"]["text"]

    await bot.session.close()

@pytest.mark.asyncio
async def test_do_usdm_div_not_admin(mock_server, dp):
    bot = build_bot(mock_server)
    dp.include_router(stellar_router)
    dp.message.middleware(MockDbMiddleware())

    with patch("routers.stellar.is_skynet_admin", return_value=False):
        update = types.Update(
            update_id=12,
            message=types.Message(
                message_id=12,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup', title="Group"),
                from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                text="/do_usdm_div"
            )
        )

        await dp.feed_update(bot=bot, update=update)

        req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
        assert req is not None
        assert "You are not my admin" in req["data"]["text"]

    await bot.session.close()

@pytest.mark.asyncio
async def test_do_usdm_usdm_div_daily_not_admin(mock_server, dp):
    bot = build_bot(mock_server)
    dp.include_router(stellar_router)
    dp.message.middleware(MockDbMiddleware())

    with patch("routers.stellar.is_skynet_admin", return_value=False):
        update = types.Update(
            update_id=13,
            message=types.Message(
                message_id=13,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup', title="Group"),
                from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                text="/do_usdm_usdm_div_daily"
            )
        )

        await dp.feed_update(bot=bot, update=update)

        req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
        assert req is not None
        assert "You are not my admin" in req["data"]["text"]

    await bot.session.close()

@pytest.mark.asyncio
async def test_do_usdm_usdm_div_test_wrong_chat(mock_server, dp):
    bot = build_bot(mock_server)
    dp.include_router(stellar_router)
    dp.message.middleware(MockDbMiddleware())

    update = types.Update(
        update_id=14,
        message=types.Message(
            message_id=14,
            date=datetime.datetime.now(),
            chat=types.Chat(id=123, type='supergroup', title="Group"),
            from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
            text="/do_usdm_usdm_div_test 10"
        )
    )

    await dp.feed_update(bot=bot, update=update)

    req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
    assert req is not None
    assert "Wrong chat" in req["data"]["text"]

    await bot.session.close()

@pytest.mark.asyncio
async def test_get_vote_fund_xdr_with_arg(mock_server, dp):
    bot = build_bot(mock_server)
    dp.include_router(stellar_router)

    with patch("routers.stellar.cmd_get_new_vote_all_mtl", new_callable=AsyncMock, return_value=["XDR"]):
        update = types.Update(
            update_id=15,
            message=types.Message(
                message_id=15,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup', title="Group"),
                from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                text="/get_vote_fund_xdr SOMEKEY"
            )
        )

        await dp.feed_update(bot=bot, update=update)

        req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
        assert req is not None
        assert "XDR" in req["data"]["text"]

    await bot.session.close()

@pytest.mark.asyncio
async def test_get_btcmtl_xdr(mock_server, dp):
    bot = build_bot(mock_server)
    dp.include_router(stellar_router)

    with patch("routers.stellar.get_btcmtl_xdr", new_callable=AsyncMock, return_value="XDR"), \
         patch("routers.stellar.decode_xdr", new_callable=AsyncMock, return_value=["Decoded"]), \
         patch("routers.stellar.multi_answer", new_callable=AsyncMock) as mock_multi_answer:
        update = types.Update(
            update_id=16,
            message=types.Message(
                message_id=16,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup', title="Group"),
                from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                text="/get_btcmtl_xdr 0.1 GABCDEF"
            )
        )

        await dp.feed_update(bot=bot, update=update)

        mock_multi_answer.assert_called()

    await bot.session.close()

@pytest.mark.asyncio
async def test_get_damircoin_xdr(mock_server, dp):
    bot = build_bot(mock_server)
    dp.include_router(stellar_router)

    with patch("routers.stellar.get_damircoin_xdr", new_callable=AsyncMock, return_value="XDR"), \
         patch("routers.stellar.decode_xdr", new_callable=AsyncMock, return_value=["Decoded"]), \
         patch("routers.stellar.multi_answer", new_callable=AsyncMock) as mock_multi_answer:
        update = types.Update(
            update_id=17,
            message=types.Message(
                message_id=17,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup', title="Group"),
                from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                text="/get_damircoin_xdr 123"
            )
        )

        await dp.feed_update(bot=bot, update=update)

        mock_multi_answer.assert_called()

    await bot.session.close()

@pytest.mark.asyncio
async def test_get_agora_xdr(mock_server, dp):
    bot = build_bot(mock_server)
    dp.include_router(stellar_router)

    with patch("routers.stellar.get_agora_xdr", new_callable=AsyncMock, return_value="XDR"), \
         patch("routers.stellar.decode_xdr", new_callable=AsyncMock, return_value=["Decoded"]), \
         patch("routers.stellar.multi_answer", new_callable=AsyncMock) as mock_multi_answer:
        update = types.Update(
            update_id=18,
            message=types.Message(
                message_id=18,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup', title="Group"),
                from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                text="/get_agora_xdr"
            )
        )

        await dp.feed_update(bot=bot, update=update)

        mock_multi_answer.assert_called()

    await bot.session.close()

@pytest.mark.asyncio
async def test_get_chicago_xdr(mock_server, dp):
    bot = build_bot(mock_server)
    dp.include_router(stellar_router)

    with patch("routers.stellar.get_chicago_xdr", new_callable=AsyncMock, return_value=["Line1", "Line2", "XDR"]), \
         patch("routers.stellar.decode_xdr", new_callable=AsyncMock, return_value=["Decoded"]), \
         patch("routers.stellar.multi_answer", new_callable=AsyncMock) as mock_multi_answer:
        update = types.Update(
            update_id=19,
            message=types.Message(
                message_id=19,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup', title="Group"),
                from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                text="/get_chicago_xdr"
            )
        )

        await dp.feed_update(bot=bot, update=update)

        mock_multi_answer.assert_called()

    await bot.session.close()

@pytest.mark.asyncio
async def test_get_toc_xdr(mock_server, dp):
    bot = build_bot(mock_server)
    dp.include_router(stellar_router)

    with patch("routers.stellar.get_toc_xdr", new_callable=AsyncMock, return_value="XDR"), \
         patch("routers.stellar.decode_xdr", new_callable=AsyncMock, return_value=["Decoded"]), \
         patch("routers.stellar.multi_answer", new_callable=AsyncMock) as mock_multi_answer:
        update = types.Update(
            update_id=20,
            message=types.Message(
                message_id=20,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup', title="Group"),
                from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                text="/get_toc_xdr 123"
            )
        )

        await dp.feed_update(bot=bot, update=update)

        mock_multi_answer.assert_called()

    await bot.session.close()

@pytest.mark.asyncio
async def test_update_airdrops_admin(mock_server, dp):
    bot = build_bot(mock_server)
    dp.include_router(stellar_router)

    with patch("routers.stellar.is_skynet_admin", return_value=True), \
         patch("routers.stellar.update_airdrop", new_callable=AsyncMock) as mock_update:
        update = types.Update(
            update_id=21,
            message=types.Message(
                message_id=21,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup', title="Group"),
                from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                text="/update_airdrops"
            )
        )

        await dp.feed_update(bot=bot, update=update)

        assert mock_update.called
        texts = [r["data"]["text"] for r in mock_server if r["method"] == "sendMessage"]
        assert any("Запускаю" in t for t in texts)
        assert any("Обновление завершено" in t for t in texts)

    await bot.session.close()

@pytest.mark.asyncio
async def test_update_fest(mock_server, dp):
    bot = build_bot(mock_server)
    dp.include_router(stellar_router)
    dp.message.middleware(MockDbMiddleware())

    with patch("routers.stellar.update_fest", new_callable=AsyncMock) as mock_update:
        update = types.Update(
            update_id=22,
            message=types.Message(
                message_id=22,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup', title="Group"),
                from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                text="/update_fest"
            )
        )

        await dp.feed_update(bot=bot, update=update)

        assert mock_update.called
        texts = [r["data"]["text"] for r in mock_server if r["method"] == "sendMessage"]
        assert any("Запускаю" in t for t in texts)
        assert any("Обновление завершено" in t for t in texts)

    await bot.session.close()

@pytest.mark.asyncio
async def test_show_data_with_arg(mock_server, dp):
    bot = build_bot(mock_server)
    dp.include_router(stellar_router)

    with patch("routers.stellar.cmd_show_data", new_callable=AsyncMock, return_value=["Line1"]), \
         patch("routers.stellar.multi_reply", new_callable=AsyncMock) as mock_multi_reply:
        update = types.Update(
            update_id=23,
            message=types.Message(
                message_id=23,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup', title="Group"),
                from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                text="/show_data GABCDEF"
            )
        )

        await dp.feed_update(bot=bot, update=update)

        mock_multi_reply.assert_called()

    await bot.session.close()

@pytest.mark.asyncio
async def test_update_bim1_admin(mock_server, dp):
    bot = build_bot(mock_server)
    dp.include_router(stellar_router)

    mock_wks = AsyncMock()
    mock_wks.get_all_values = AsyncMock(return_value=[
        ["h1", "h2", "h3", "h4"],
        ["h1", "h2", "h3", "h4"],
        ["v1", "v2", "v3", "123"]
    ])
    mock_wks.update = AsyncMock()
    mock_doc = AsyncMock()
    mock_doc.worksheet = AsyncMock(return_value=mock_wks)
    mock_agc = AsyncMock()
    mock_agc.open = AsyncMock(return_value=mock_doc)

    with patch("routers.stellar.is_skynet_admin", return_value=True), \
         patch("routers.stellar.agcm.authorize", new_callable=AsyncMock, return_value=mock_agc):
        with patch.object(bot, "get_chat_member", new_callable=AsyncMock, return_value=MagicMock(is_member=True)):
            update = types.Update(
                update_id=24,
                message=types.Message(
                    message_id=24,
                    date=datetime.datetime.now(),
                    chat=types.Chat(id=123, type='supergroup', title="Group"),
                    from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                    text="/update_bim1"
                )
            )

            await dp.feed_update(bot=bot, update=update)

            assert mock_wks.update.called
            req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
            assert req is not None
            assert "Done" in req["data"]["text"]

    await bot.session.close()

@pytest.mark.asyncio
async def test_check_bim_by_user(mock_server, dp):
    bot = build_bot(mock_server)
    dp.include_router(stellar_router)

    with patch("routers.stellar.gs_check_bim", new_callable=AsyncMock, return_value="OK"):
        update = types.Update(
            update_id=25,
            message=types.Message(
                message_id=25,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup', title="Group"),
                from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                text="/check_bim"
            )
        )

        await dp.feed_update(bot=bot, update=update)

        req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
        assert req is not None
        assert "OK" in req["data"]["text"]

    await bot.session.close()

@pytest.mark.asyncio
async def test_check_mtlap_admin(mock_server, dp):
    bot = build_bot(mock_server)
    dp.include_router(stellar_router)

    with patch("routers.stellar.is_skynet_admin", return_value=True), \
         patch("routers.stellar.find_stellar_public_key", return_value="GABCDEF"), \
         patch("routers.stellar.check_mtlap", new_callable=AsyncMock, return_value="MTLAP OK"):
        update = types.Update(
            update_id=26,
            message=types.Message(
                message_id=26,
                date=datetime.datetime.now(),
                chat=types.Chat(id=123, type='supergroup', title="Group"),
                from_user=types.User(id=999, is_bot=False, first_name="User", username="user"),
                text="/check_mtlap GABCDEF"
            )
        )

        await dp.feed_update(bot=bot, update=update)

        req = next((r for r in mock_server if r["method"] == "sendMessage"), None)
        assert req is not None
        assert "MTLAP OK" in req["data"]["text"]

    await bot.session.close()
