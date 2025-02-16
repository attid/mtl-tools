import asyncio
import sys
from contextlib import suppress

import sentry_sdk
import uvloop
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeChat
from redis.asyncio import Redis
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from other import aiogram_tools
from other.config_reader import config
from routers.admin import command_config_loads
from db.requests import db_save_bot_user, db_load_bot_users
from middlewares.db import DbSessionMiddleware
from middlewares.retry import RetryRequestMiddleware
from middlewares.sentry_error_handler import sentry_error_handler
from middlewares.throttling import ThrottlingMiddleware
from routers import last_handler
from other.global_data import global_data, MTLChats, global_tasks
from other.pyro_tools import pyro_start
from other.support_tools import work_with_support
from routers.monitoring import register_handlers  # Импорт функции для регистрации роутера


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


async def on_startup(bot: Bot, dispatcher: Dispatcher):
    await set_commands(bot)
    with suppress(TelegramBadRequest):
        await bot.send_message(chat_id=MTLChats.ITolstov, text='Bot started')
    # with suppress(TelegramBadRequest):
    #     await bot.send_message(chat_id=MTLChats.HelperChat, text='Bot started')
    if 'test' in sys.argv:
        return
    global_tasks.append(asyncio.create_task(work_with_support()))
    await pyro_start()
    # _ = asyncio.create_task(startup_update_namelist(bot))
    # _ = asyncio.create_task(gs_update_watchlist(dispatcher['dbsession_pool']))


# async def startup_update_namelist(bot: Bot):
#     await gs_update_namelist()
#     with suppress(TelegramBadRequest):
#     await bot.send_message(chat_id=MTLChats.ITolstov, text='namelist loaded')


async def on_shutdown(bot: Bot):
    with suppress(TelegramBadRequest):
        await bot.send_message(chat_id=MTLChats.ITolstov, text='Bot stopped')
    for task in global_tasks:
        task.cancel()


async def main():
    logger.add("logs/skynet.log", rotation="1 MB", level='INFO')

    # Запуск бота
    engine = create_engine(config.db_dns, pool_pre_ping=True, max_overflow=50)
    # Creating DB connections pool
    db_pool = sessionmaker(bind=engine)

    # Creating bot and its dispatcher
    session: AiohttpSession = AiohttpSession()
    session.middleware(RetryRequestMiddleware())
    if 'test' in sys.argv:
        bot = Bot(token=config.test_token.get_secret_value(), default=DefaultBotProperties(parse_mode='HTML'),
                  session=session)
        logger.info('start test')
    else:
        bot = Bot(token=config.bot_token.get_secret_value(), default=DefaultBotProperties(parse_mode='HTML'),
                  session=session)

    redis = Redis(host='localhost', port=6379, db=4)
    storage = RedisStorage(redis=redis)
    dp = Dispatcher(storage=storage)

    global_tasks.append(asyncio.create_task(load_globals(db_pool())))
    from routers import (admin, inline, polls, start_router, stellar, talk_handlers, time_handlers, welcome)
    dp.message.middleware(DbSessionMiddleware(db_pool))
    dp.callback_query.middleware(DbSessionMiddleware(db_pool))
    dp.chat_member.middleware(DbSessionMiddleware(db_pool))
    dp.channel_post.middleware(DbSessionMiddleware(db_pool))
    dp.edited_channel_post.middleware(DbSessionMiddleware(db_pool))
    dp.poll_answer.middleware(DbSessionMiddleware(db_pool))

    dp.message.middleware(ThrottlingMiddleware(redis=redis))

    dp.include_router(admin.router)
    dp.include_router(inline.router)
    dp.include_router(polls.router)
    dp.include_router(start_router.router)
    dp.include_router(stellar.router)
    dp.include_router(welcome.router)
    dp.include_router(talk_handlers.router)  # last
    dp.include_router(last_handler.router)  # last, last

    register_handlers(dp, bot)  # Регистрация роутера

    scheduler = AsyncIOScheduler(timezone='Europe/Podgorica')#str(tzlocal.get_localzone()))
    aiogram_tools.scheduler = scheduler
    scheduler.start()
    if 'test' not in sys.argv:
        time_handlers.scheduler_jobs(scheduler, bot, db_pool)
    dp['dbsession_pool'] = db_pool
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    dp.errors.register(sentry_error_handler)

    # Запускаем бота и пропускаем все накопленные входящие
    # Да, этот метод можно вызвать даже если у вас поллинг
    await bot.delete_webhook(drop_pending_updates=True)
    print(dp.resolve_used_update_types())
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


async def load_globals(session: Session):
    await command_config_loads(session)
    for user in db_load_bot_users(session):
        global_data.users_list[user.user_id] = user.user_type


def add_bot_users(session: Session, user_id: int, username: str | None, new_user_type: int = 0):
    """Добавляет или обновляет пользователя в списке с логированием"""
    global_data.add_user(user_id, new_user_type)
    # user_type = 1 if good else 2
    # -1 one mistake -2 two mistake
    ### user_type_now = global_data.users_list.get(user_id)
    ### # Проверяем, существует ли пользователь, его текущий тип не равен 2, и новый тип больше текущего
    ### if not user_type_now or (new_user_type > user_type_now):
    db_save_bot_user(session, user_id, username, new_user_type)


if __name__ == "__main__":
    sentry_sdk.init(
        dsn=config.sentry_dsn,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )
    try:
        # import logging
        # logging.basicConfig(level=logging.DEBUG)
        uvloop.install()
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.error("Exit")
    except Exception as e:
        if not global_data.reboot:
            logger.exception(e)
            raise e
