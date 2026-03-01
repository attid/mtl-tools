"""
Monitoring protocol notes (ping/pong) for bot-to-bot channel communication.

Canonical pattern:
1) Message header uses addressing order: ``#<to> #<from> command=<...>``.
2) Request/response pair is strict: ``ping -> pong``.

Current actors:
- SkyNet sends request:
  ``#mmwb #skynet command=ping``
- MTL Wallet (MMWB side) responds:
  ``#skynet #mmwb command=pong``

Operational rules:
- This router updates health state only on incoming ``pong``.
- ``ping`` is emitted by periodic task and is not treated as a health response.
- Unknown commands should be ignored to avoid feedback loops.
- Each side should process only counterpart request/response, not self-generated messages.
"""

from datetime import datetime
from aiogram import Router, types, Bot
from aiogram import F
import asyncio
from loguru import logger

from other.config_reader import config
from other.constants import MTLChats
from other.gspread_tools import gs_close_support, gs_save_new_support
from other.monitoring_contracts import is_helper_event, is_mmwb_pong, parse_helper_event
from services.app_context import AppContext

router = Router()
router.message.filter(F.chat.id == MTLChats.BotsChanel)

PING_INTERVAL = 60  # seconds
PING_TIMEOUT = 100  # seconds
HELPER_DEDUP_KEY = "__helper_events_processed__"


@router.channel_post(F.text.regexp(r"^\s*#skynet"))
async def handle_skynet_message(message: types.Message, app_context: AppContext):
    text = message.text or message.caption
    if not text:
        return
    if not app_context.bot_state_service:
        return

    # Check for #skynet #mmwb command=pong pattern
    if is_mmwb_pong(text):
        app_context.bot_state_service.update_last_pong()
        logger.debug(f"Updated last pong response time: {app_context.bot_state_service.get_last_pong()}")
        return

    if not is_helper_event(text):
        return

    try:
        event = parse_helper_event(text)
    except (KeyError, ValueError) as exc:
        logger.warning("monitoring.helper: invalid payload='{}' error={}", text, exc)
        return

    dedup_key = f"{event.command}:{event.url}"
    processed = app_context.bot_state_service.get_sync_state(HELPER_DEDUP_KEY, {})
    if not isinstance(processed, dict):
        processed = {}
    if dedup_key in processed:
        logger.debug("monitoring.helper: duplicate ignored key={}", dedup_key)
        await message.answer(f"#helper #skynet command=ack status=duplicate op={event.command} url={event.ack_url}")
        return

    try:
        if event.command == "taken":
            username = event.username
            if username is None:
                logger.warning("monitoring.helper: invalid taken payload without username payload='{}'", text)
                return
            await gs_save_new_support(
                user_id=event.user_id,
                username=username,
                agent_username=event.agent_username,
                url=event.url,
            )
            logger.info(
                "monitoring.helper: taken processed user_id={} username={} agent_username={} url={}",
                event.user_id,
                username,
                event.agent_username,
                event.url,
            )
        else:
            await gs_close_support(url=event.url)
            logger.info("monitoring.helper: closed processed url={}", event.url)
    except Exception as exc:
        logger.error("monitoring.helper: failed payload='{}' error={}", text, exc)
        return

    processed[dedup_key] = True
    app_context.bot_state_service.set_sync_state(HELPER_DEDUP_KEY, processed)
    await message.answer(f"#helper #skynet command=ack status=ok op={event.command} url={event.ack_url}")


async def check_ping_responses(bot: Bot, app_context: AppContext):
    if not app_context.bot_state_service:
        logger.warning("bot_state_service not available for monitoring ping checks")
        return
    while True:
        # Отправляем ping в канал
        try:
            await bot.send_message(chat_id=MTLChats.BotsChanel, text="#mmwb #skynet command=ping")
            app_context.bot_state_service.update_last_ping_sent()
            logger.debug("Sent ping message to channel")
        except Exception as e:
            logger.error(f"Failed to send ping message: {e}")

        # Ждем 1 минуту
        await asyncio.sleep(PING_INTERVAL)

        # Проверяем ответ
        last_pong = app_context.bot_state_service.get_last_pong()
        if last_pong:
            time_since_last = (datetime.now() - last_pong).total_seconds()
            if time_since_last > PING_TIMEOUT:
                try:
                    await bot.send_message(
                        chat_id=MTLChats.ITolstov,
                        text=f"⚠️ MMWB No pong response for {int(time_since_last) // 60} minutes!",
                    )
                except Exception as e:
                    logger.error(f"Failed to notify admin : {e}")


def register_handlers(dp, bot):
    if config.test_mode:
        return
    dp.include_router(router)
    app_context = dp.get("app_context")
    if app_context:
        asyncio.create_task(check_ping_responses(bot, app_context))
    else:
        logger.warning("app_context not available for monitoring router")
    logger.info("router monitoring was loaded")
