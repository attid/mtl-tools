from datetime import datetime
from aiogram import Router, types, Bot
from aiogram import F
import re
import asyncio
from loguru import logger

from other.config_reader import config
from other.global_data import MTLChats
from services.app_context import AppContext

router = Router()
router.message.filter(F.chat.id == MTLChats.BotsChanel)

PING_INTERVAL = 60  # seconds
PING_TIMEOUT = 100  # seconds

@router.channel_post(F.text.regexp(r'^\s*#skynet'))
async def handle_skynet_message(message: types.Message, app_context: AppContext):
    text = message.text or message.caption
    if not text:
        return

    # Check for #skynet #mmwb command=pong pattern
    if re.search(r'#skynet\s+#mmwb\s+command=pong', text, re.IGNORECASE):
        app_context.bot_state_service.update_last_pong()
        logger.debug(f"Updated last pong response time: {app_context.bot_state_service.get_last_pong()}")

async def check_ping_responses(bot: Bot, app_context: AppContext):
    while True:
        # Отправляем ping в канал
        try:
            await bot.send_message(
                chat_id=MTLChats.BotsChanel,
                text="#mmwb #skynet command=ping"
            )
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