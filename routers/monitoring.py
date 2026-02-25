from datetime import datetime
from aiogram import Router, types, Bot
from aiogram import F
import re
import asyncio
from urllib.parse import quote, unquote
from loguru import logger

from other.config_reader import config
from other.constants import MTLChats
from other.gspread_tools import gs_close_support, gs_save_new_support
from services.app_context import AppContext

router = Router()
router.message.filter(F.chat.id == MTLChats.BotsChanel)

PING_INTERVAL = 60  # seconds
PING_TIMEOUT = 100  # seconds
HELPER_DEDUP_KEY = "__helper_events_processed__"


def _parse_kv_payload(text: str) -> dict[str, str]:
    pairs = re.findall(r"([a-zA-Z_][a-zA-Z0-9_]*)=([^\s]+)", text)
    return {k: v for k, v in pairs}

@router.channel_post(F.text.regexp(r'^\s*#skynet'))
async def handle_skynet_message(message: types.Message, app_context: AppContext):
    text = message.text or message.caption
    if not text:
        return
    if not app_context.bot_state_service:
        return

    # Check for #skynet #mmwb command=pong pattern
    if re.search(r'#skynet\s+#mmwb\s+command=pong', text, re.IGNORECASE):
        app_context.bot_state_service.update_last_pong()
        logger.debug(f"Updated last pong response time: {app_context.bot_state_service.get_last_pong()}")
        return

    if not re.search(r'#skynet\s+#helper\b', text, re.IGNORECASE):
        return

    payload = _parse_kv_payload(text)
    command = payload.get("command", "").lower()
    url_raw = payload.get("url")
    if command not in {"taken", "closed"}:
        logger.warning("monitoring.helper: unknown command payload='{}'", text)
        await message.answer("#skynet #helper command=error reason=unknown_command")
        return
    if not url_raw:
        logger.warning("monitoring.helper: missing url payload='{}'", text)
        await message.answer("#skynet #helper command=error reason=missing_url")
        return
    url = unquote(url_raw)
    ack_url = quote(url, safe="")

    dedup_key = f"{command}:{url}"
    processed = app_context.bot_state_service.get_sync_state(HELPER_DEDUP_KEY, {})
    if not isinstance(processed, dict):
        processed = {}
    if dedup_key in processed:
        logger.debug("monitoring.helper: duplicate ignored key={}", dedup_key)
        await message.answer(f"#skynet #helper command=ack status=duplicate op={command} url={ack_url}")
        return

    try:
        if command == "taken":
            user_id = int(payload["user_id"])
            username = payload["username"]
            agent_username = payload["agent_username"]
            await gs_save_new_support(
                user_id=user_id,
                username=username,
                agent_username=agent_username,
                url=url,
            )
            logger.info(
                "monitoring.helper: taken processed user_id={} username={} agent_username={} url={}",
                user_id,
                username,
                agent_username,
                url,
            )
        else:
            if payload.get("closed", "").lower() != "true":
                logger.warning("monitoring.helper: closed command without closed=true payload='{}'", text)
                return
            _ = int(payload["user_id"])
            _ = payload["agent_username"]
            await gs_close_support(url=url)
            logger.info("monitoring.helper: closed processed url={}", url)
    except (KeyError, ValueError) as exc:
        logger.warning("monitoring.helper: invalid payload='{}' error={}", text, exc)
        await message.answer("#skynet #helper command=error reason=invalid_payload")
        return
    except Exception as exc:
        logger.error("monitoring.helper: failed payload='{}' error={}", text, exc)
        await message.answer("#skynet #helper command=error reason=processing_failed")
        return

    processed[dedup_key] = True
    app_context.bot_state_service.set_sync_state(HELPER_DEDUP_KEY, processed)
    await message.answer(f"#skynet #helper command=ack status=ok op={command} url={ack_url}")

async def check_ping_responses(bot: Bot, app_context: AppContext):
    if not app_context.bot_state_service:
        logger.warning("bot_state_service not available for monitoring ping checks")
        return
    while True:
        # Отправляем ping в канал
        try:
            await bot.send_message(
                chat_id=MTLChats.BotsChanel,
                text="#mmwb #skynet command=ping"
            )
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
                    await bot.send_message(chat_id=MTLChats.ITolstov,
                                           text=f"⚠️ MMWB No pong response for {int(time_since_last)//60} minutes!")
                except Exception as e:
                    logger.error(f"Failed to notify admin : {e}")

def register_handlers(dp, bot):
    if config.test_mode:
        return
    dp.include_router(router)
    app_context = dp.get('app_context')
    if app_context:
        asyncio.create_task(check_ping_responses(bot, app_context))
    else:
        logger.warning('app_context not available for monitoring router')
    logger.info('router monitoring was loaded')
