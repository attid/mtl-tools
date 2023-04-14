import json
import os
from enum import IntEnum

import tzlocal
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils.callback_data import CallbackData
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

import mystellar
from settings import bot_key
import logging

# from aiogram.utils.markdown import bold, code, italic, text, link

# https://docs.aiogram.dev/en/latest/quick_start.html
# https://surik00.gitbooks.io/aiogram-lessons/content/chapter3.html

# Объект бота

bot = Bot(token=bot_key)
# Диспетчер для бота
dp = Dispatcher(bot, storage=MemoryStorage())
dp.middleware.setup(LoggingMiddleware())

scheduler = AsyncIOScheduler(timezone=str(tzlocal.get_localzone()))
print(logging.Logger.manager.loggerDict)
logging.getLogger('apscheduler').setLevel(logging.WARNING)
logging.getLogger('aiogram.contrib.middlewares').setLevel(logging.WARNING)

# 'concurrent': <logging.PlaceHolder object at 0x7f3c28149910>,
# 'aiohttp': <logging.PlaceHolder object at 0x7f3c271cd970>,
# 'gunicorn.http': <logging.PlaceHolder object at 0x7f3c26231a60>,
# 'gunicorn': <logging.PlaceHolder object at 0x7f3c26231a00>,
# 'aiogram.dispatcher': <logging.PlaceHolder object at 0x7f3c25e3f910>,
# 'apscheduler': <logging.PlaceHolder object at 0x7f3c273ec550>,
# 'aiogram.contrib.middlewares': <logging.PlaceHolder object at 0x7f3c273c7850>,
# 'aiogram.contrib': <logging.PlaceHolder object at 0x7f3c273c7cd0>,


# Включаем логирование, чтобы не пропустить важные сообщения
logger.add("skynet.log", rotation="1 MB")


class MTLChats(IntEnum):
    TestGroup = -1001767165598  # тестовая группа
    SignGroup = -1001239694752  # подписанты
    GuarantorGroup = -1001169382324  # Guarantors EURMTL
    DistributedGroup = -1001798357244  # distributed government
    ShareholderGroup = -1001269297637
    GroupAnonymousBot = 1087968824
    SafeGroup = -1001876391583
    LandLordGroup = -1001757912662
    SignGroupForChanel = -1001784614029


cb_captcha = CallbackData("cb_captcha", "answer")


async def multi_reply(message: types.Message, text: str):
    while len(text) > 0:
        await message.reply(text[:4000])
        text = text[4000:]


async def multi_answer(message: types.Message, text: str):
    while len(text) > 0:
        await message.answer(text[:4000])
        text = text[4000:]


delete_income = []
save_all = []
reply_only = []


def cmd_save_delete_income():
    with open("polls/delete_income.json", "w") as fp:
        json.dump(delete_income, fp)


def cmd_save_save_all():
    with open("polls/save_all.json", "w") as fp:
        json.dump(save_all, fp)


def cmd_save_reply_only():
    with open("polls/reply_only.json", "w") as fp:
        json.dump(reply_only, fp)


# create files
if not os.path.isfile("polls/delete_income.json"):
    cmd_save_delete_income()

if not os.path.isfile("polls/save_all.json"):
    cmd_save_save_all()

if not os.path.isfile("polls/reply_only.json"):
    cmd_save_reply_only()

try:
    with open("polls/delete_income.json", "r") as fp:
        delete_income = json.load(fp)
    with open("polls/save_all.json", "r") as fp:
        save_all = json.load(fp)
    with open("polls/reply_only.json", "r") as fp:
        reply_only = json.load(fp)
except Exception as ex:
    logger.exception(ex)

welcome_message = {}
try:
    with open("polls/welcome_message.json", "r") as fp:
        welcome_message = json.load(fp)
    if 'captcha' in welcome_message:
        pass
    else:
        welcome_message['captcha'] = []
except Exception as ex:
    logger.exception(ex)


def cmd_save_welcome_message():
    with open("polls/welcome_message.json", "w") as fp:
        json.dump(welcome_message, fp)


async def is_admin(message: types.Message):
    members = await message.chat.get_administrators()
    if message.from_user.id == MTLChats.GroupAnonymousBot:
        return True
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


def add_text(lines, num_line, text):
    if len(lines) > num_line - 1:
        lines.pop(num_line - 1)
    lines.append(text)
    return "\n".join(lines)

async def send_by_list(all_users: list, message: types.Message, url=None):
    good_users = []
    bad_users = []
    if url is None:
        url = message.reply_to_message.url
    msg = f'@{message.from_user.username} call you here {url}'
    for user in all_users:
        if len(user) > 2 and user[0] == '@':
            try:
                chat_id = mystellar.cmd_load_user_id(user[1:])
                await message.bot.send_message(chat_id=chat_id, text=msg)
                good_users.append(user)
            except Exception as ex:
                bad_users.append(user)
                logger.info(ex)
                pass
    await message.reply(f'was send to {" ".join(good_users)} \n can`t send to {" ".join(bad_users)}')
