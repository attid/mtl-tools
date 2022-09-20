import json
import sys
from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
# from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.fsm_storage.redis import RedisStorage2
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import fb
from settings import MyMTLWallet_key, MyMTLWalletTest_key
import app_logger

# from aiogram.utils.markdown import bold, code, italic, text, link

# https://docs.aiogram.dev/en/latest/quick_start.html
# https://surik00.gitbooks.io/aiogram-lessons/content/chapter3.html

# Объект бота

if 'test' in sys.argv:
    bot = Bot(token=MyMTLWalletTest_key)
    # Диспетчер для бота
    dp = Dispatcher(bot, storage=MemoryStorage())
    print('start test')
else:
    bot = Bot(token=MyMTLWallet_key)
    # Диспетчер для бота
    storage = RedisStorage2('localhost', 6379, db=5, pool_size=10, prefix='my_fsm_key')
    dp = Dispatcher(bot, storage=storage)

dp.middleware.setup(LoggingMiddleware())

scheduler = AsyncIOScheduler()

# Включаем логирование, чтобы не пропустить важные сообщения
logger = app_logger.get_logger("MyMTLWallet_bot")

user_lang_dic = {}
lang_dict = {}

with open("jsons/en.json", "r") as fp:
    lang_dict['en'] = json.load(fp)

with open("jsons/ru.json", "r") as fp:
    lang_dict['ru'] = json.load(fp)


def get_user_lang(user_id: int):
    try:
        return fb.execsql1(f"select first 1 m.lang from mymtlwalletbot m where m.user_id = ?", (user_id,), 'en')
    except Exception as ex:
        return 'en'


def change_user_lang(user_id: int):
    lang = fb.execsql1(f"select first 1 m.lang from mymtlwalletbot m where m.user_id = ?", (user_id,), 'en')
    if lang == 'en':
        lang = 'ru'
    else:
        lang = 'en'
    fb.execsql("update mymtlwalletbot m set m.lang = ? where m.user_id = ?", (lang, user_id,))
    user_lang_dic[user_id] = lang


def my_gettext(user_id, text) -> str:
    if user_id in user_lang_dic:
        lang = user_lang_dic[user_id]
    else:
        lang = get_user_lang(user_id)
        user_lang_dic[user_id] = lang

    return lang_dict[lang].get(text, f'{text} 0_0')
