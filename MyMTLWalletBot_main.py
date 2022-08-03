from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.fsm_storage.redis import RedisStorage2
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from settings import MyMTLWallet_key
import app_logger

# from aiogram.utils.markdown import bold, code, italic, text, link

# https://docs.aiogram.dev/en/latest/quick_start.html
# https://surik00.gitbooks.io/aiogram-lessons/content/chapter3.html

# Объект бота

bot = Bot(token=MyMTLWallet_key)
# Диспетчер для бота

storage = RedisStorage2('localhost', 6379, db=5, pool_size=10, prefix='my_fsm_key')
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

scheduler = AsyncIOScheduler()

# Включаем логирование, чтобы не пропустить важные сообщения
logger = app_logger.get_logger("MyMTLWallet_bot")


def add_info_log(*args):
    msg = ''
    for s in args:
        msg += str(s) + ' '
    logger.info(msg)
