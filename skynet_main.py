import json
from enum import IntEnum

from aiogram import Bot, Dispatcher, types
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
logger = app_logger.get_logger("skynet")


class MTLChats(IntEnum):
    TestGroup = -1001767165598  # тестовая группа
    SignGroup = -1001239694752  # подписанты
    GuarantorGroup = -1001169382324  # Guarantors EURMTL
    DistributedGroup = -1001798357244  # distributed government
    ShareholderGroup = -1001269297637
    

async def multi_reply(message: types.Message, text: str):
    while len(text) > 0:
        await message.reply(text[:4000])
        text = text[4000:]


async def multi_answer(message: types.Message, text: str):
    while len(text) > 0:
        await message.answer(text[:4000])
        text = text[4000:]


delete_income = []
try:
    with open("polls/delete_income.json", "r") as fp:
        delete_income = json.load(fp)
except Exception as ex:
    logger.info(ex)


def cmd_save_delete_income():
    with open("polls/delete_income.json", "w") as fp:
        json.dump(delete_income, fp)


welcome_message = {}
try:
    with open("polls/welcome_message.json", "r") as fp:
        welcome_message = json.load(fp)
except Exception as ex:
    logger.info(ex)


def cmd_save_welcome_message():
    with open("polls/welcome_message.json", "w") as fp:
        json.dump(welcome_message, fp)


async def is_admin(message: types.Message):
    members = await message.chat.get_administrators()
    try:
        chat_member = next(filter(lambda member: member.user.id == message.from_user.id, members))
    except StopIteration:
        return False
    return True


async def is_skynet_admin(message: types.Message):
    all_file = f'polls/skynet_admins'
    from os.path import isfile
    if isfile(all_file):
        with open(all_file, "r") as fp:
            members = list(json.load(fp))
        return f'@{message.from_user.username}' in members
    else:
        return False