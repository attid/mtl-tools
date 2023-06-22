import asyncio
import json
import sys

import tzlocal
from aiogram import types, Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeChat
from aioredis import Redis
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from config_reader import config
from db.requests import cmd_load_bot_value, get_chat_ids_by_key, get_chat_dict_by_key
from middlewares.db import DbSessionMiddleware

from routers import (admin, all, inline, polls, start, stellar, talk_handlers, time_handlers, welcome)
from utils import aiogram_utils
from utils.global_data import global_data, BotValueTypes


async def set_commands(bot):
    commands_clear = []
    commands_admin = [
        BotCommand(
            command="start",
            description="Start or ReStart bot",
        ),
        BotCommand(
            command="restart",
            description="ReStart bot",
        ),
        BotCommand(
            command="fee",
            description="check fee",
        ),
    ]
    commands_private = [
        BotCommand(
            command="start",
            description="Start or ReStart bot",
        ),
    ]
    commands_treasury = [
        BotCommand(
            command="balance",
            description="Show balance",
        ),
    ]

    await bot.set_my_commands(commands=commands_private, scope=BotCommandScopeAllPrivateChats())
    await bot.set_my_commands(commands=commands_admin, scope=BotCommandScopeChat(chat_id=84131737))
    # await bot.set_my_commands(commands=commands_treasury, scope=BotCommandScopeChat(chat_id=-1001169382324))


def load_globals(session: Session):
    global_data.skynet_admins = json.loads(cmd_load_bot_value(session, 0, BotValueTypes.SkynetAdmins, '[]'))
    global_data.votes = json.loads(cmd_load_bot_value(session, 0, BotValueTypes.Votes, '{}'))
    global_data.auto_all = get_chat_ids_by_key(session, BotValueTypes.AutoAll)
    global_data.reply_only = get_chat_ids_by_key(session, BotValueTypes.ReplyOnly)
    global_data.captcha = get_chat_ids_by_key(session, BotValueTypes.Captcha)

    global_data.welcome_messages = get_chat_dict_by_key(session, BotValueTypes.WelcomeMessage)
    global_data.welcome_button = get_chat_dict_by_key(session, BotValueTypes.WelcomeButton)
    global_data.delete_income = get_chat_dict_by_key(session, BotValueTypes.DeleteIncome)



@logger.catch
async def main():
    logger.add("skynet.log", rotation="1 MB", level='INFO')

    # Запуск бота
    engine = create_engine(config.db_dns, pool_pre_ping=True)
    # Creating DB connections pool
    db_pool = sessionmaker(bind=engine)

    # Creating bot and its dispatcher
    if 'test' in sys.argv:
        bot = Bot(token=config.test_token.get_secret_value(), parse_mode='HTML')
        print('start test')
    else:
        bot = Bot(token=config.bot_token.get_secret_value(), parse_mode="HTML")


    storage = RedisStorage(redis=Redis(host='localhost', port=6379, db=4))
    dp = Dispatcher(storage=storage)

    load_globals(db_pool())

    dp.message.middleware(DbSessionMiddleware(db_pool))
    dp.callback_query.middleware(DbSessionMiddleware(db_pool))
    dp.chat_member.middleware(DbSessionMiddleware(db_pool))

    dp.include_router(admin.router)
    dp.include_router(all.router)
    dp.include_router(inline.router)
    dp.include_router(polls.router)
    dp.include_router(start.router)
    dp.include_router(stellar.router)
    dp.include_router(welcome.router)
    dp.include_router(talk_handlers.router)  # last

    scheduler = AsyncIOScheduler(timezone=str(tzlocal.get_localzone()))
    aiogram_utils.scheduler = scheduler
    scheduler.start()
    time_handlers.scheduler_jobs(scheduler, bot, db_pool())

    # Запускаем бота и пропускаем все накопленные входящие
    # Да, этот метод можно вызвать даже если у вас поллинг
    await bot.delete_webhook(drop_pending_updates=True)
    await set_commands(bot)
    print(dp.resolve_used_update_types())
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.error("Exit")
