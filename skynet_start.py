import asyncio
import json
import sys
from contextlib import suppress
import tzlocal
from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeChat
from aioredis import Redis
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from config_reader import config
from db.requests import db_load_bot_value, db_get_chat_ids_by_key, db_get_chat_dict_by_key
from middlewares.db import DbSessionMiddleware
from utils import aiogram_utils
from utils.global_data import global_data, BotValueTypes, MTLChats, global_tasks
from utils.gspread_tools import gs_update_namelist, gs_update_watchlist
from utils.support_tools import work_with_support


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
    global_data.skynet_admins = json.loads(db_load_bot_value(session, 0, BotValueTypes.SkynetAdmins, '[]'))
    global_data.votes = json.loads(db_load_bot_value(session, 0, BotValueTypes.Votes, '{}'))
    global_data.auto_all = db_get_chat_ids_by_key(session, BotValueTypes.AutoAll)
    global_data.reply_only = db_get_chat_ids_by_key(session, BotValueTypes.ReplyOnly)
    global_data.captcha = db_get_chat_ids_by_key(session, BotValueTypes.Captcha)
    global_data.listen = db_get_chat_ids_by_key(session, BotValueTypes.Listen)
    global_data.full_data = db_get_chat_ids_by_key(session, BotValueTypes.FullData)

    global_data.welcome_messages = db_get_chat_dict_by_key(session, BotValueTypes.WelcomeMessage)
    global_data.welcome_button = db_get_chat_dict_by_key(session, BotValueTypes.WelcomeButton)
    global_data.delete_income = db_get_chat_dict_by_key(session, BotValueTypes.DeleteIncome)


async def on_startup(bot: Bot, dispatcher: Dispatcher):
    await set_commands(bot)
    with suppress(TelegramBadRequest):
        await bot.send_message(chat_id=MTLChats.ITolstov, text='Bot started')
    with suppress(TelegramBadRequest):
        await bot.send_message(chat_id=MTLChats.HelperChat, text='Bot started')
    global_tasks.append(asyncio.create_task(work_with_support()))
    asyncio.create_task(startup_update_namelist(bot))
    asyncio.create_task(gs_update_watchlist(dispatcher['dbsession_pool']))


async def startup_update_namelist(bot: Bot):
    await gs_update_namelist()
    with suppress(TelegramBadRequest):
        await bot.send_message(chat_id=MTLChats.ITolstov, text='namelist loaded')


async def on_shutdown(bot: Bot):
    with suppress(TelegramBadRequest):
        await bot.send_message(chat_id=MTLChats.ITolstov, text='Bot stopped')
    for task in global_tasks:
        task.cancel()


@logger.catch
async def main():
    logger.add("skynet.log", rotation="1 MB", level='INFO')

    # Запуск бота
    engine = create_engine(config.db_dns, pool_pre_ping=True, max_overflow=50)
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
    from routers import (admin, all, inline, polls, start, stellar, talk_handlers, time_handlers, welcome)

    dp.message.middleware(DbSessionMiddleware(db_pool))
    dp.callback_query.middleware(DbSessionMiddleware(db_pool))
    dp.chat_member.middleware(DbSessionMiddleware(db_pool))
    dp.channel_post.middleware(DbSessionMiddleware(db_pool))

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
    time_handlers.scheduler_jobs(scheduler, bot, db_pool)
    dp['dbsession_pool'] = db_pool
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Запускаем бота и пропускаем все накопленные входящие
    # Да, этот метод можно вызвать даже если у вас поллинг
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.error("Exit")
