from datetime import datetime, timedelta
from aiogram import Router, types, Bot
from aiogram import F
import re
import asyncio
from loguru import logger

from other.global_data import global_data, MTLChats

router = Router()
router.message.filter(F.chat.id == MTLChats.BotsChanel)

PING_INTERVAL = 60  # seconds
PING_TIMEOUT = 100  # seconds

@router.channel_post(F.text.regexp(r'^\s*#skynet'))
async def handle_skynet_message(message: types.Message):
    text = message.text or message.caption
    if not text:
        return
        
    # Check for #skynet #mmwb command=pong pattern
    if re.search(r'#skynet\s+#mmwb\s+command=pong', text, re.IGNORECASE):
        global_data.last_pong_response = datetime.now()
        logger.debug(f"Updated last pong response time: {global_data.last_pong_response}")

async def check_ping_responses(bot: Bot):
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
        if global_data.last_pong_response:
            time_since_last = (datetime.now() - global_data.last_pong_response).total_seconds()
            if time_since_last > PING_TIMEOUT:
                try:
                    await bot.send_message(chat_id=MTLChats.ITolstov,
                                           text=f"⚠️ MMWB No pong response for {int(time_since_last)//60} minutes!")
                except Exception as e:
                    logger.error(f"Failed to notify admin : {e}")

def register_handlers(dp, bot):
    dp.include_router(router)
    asyncio.create_task(check_ping_responses(bot))