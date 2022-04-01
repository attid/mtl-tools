from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from settings import bot_key
import app_logger

# from aiogram.utils.markdown import bold, code, italic, text, link

# https://docs.aiogram.dev/en/latest/quick_start.html
# https://surik00.gitbooks.io/aiogram-lessons/content/chapter3.html

# Объект бота

bot = Bot(token=bot_key)
# Диспетчер для бота
dp = Dispatcher(bot, storage=MemoryStorage())
dp.middleware.setup(LoggingMiddleware())

scheduler = AsyncIOScheduler()

# Включаем логирование, чтобы не пропустить важные сообщения
logger = app_logger.get_logger("mtl_bot")
