# Standard library imports
import asyncio
import importlib
from contextlib import suppress

# Third-party imports
import sentry_sdk
import uvloop
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeChat,
)
from loguru import logger
from redis.asyncio import Redis
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Local application imports
from db.repositories import ChatsRepository
from middlewares.db import DbSessionMiddleware
from middlewares.emoji_reaction import EmojiReactionMiddleware
from middlewares.retry import RetryRequestMiddleware
from middlewares.sentry_error_handler import sentry_error_handler
from middlewares.throttling import ThrottlingMiddleware
from middlewares.app_context import AppContextMiddleware
from other.config_reader import config
from other.global_data import MTLChats, global_data, global_tasks
from other.pyro_tools import pyro_start
from other.support_tools import work_with_support

logger.info('start')


async def set_commands(bot):
    # commands_clear = []
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
    # commands_treasury = [
    #     BotCommand(
    #         command="balance",
    #         description="Show balance",
    #     ),
    # ]

    await bot.set_my_commands(commands=commands_private, scope=BotCommandScopeAllPrivateChats())
    await bot.set_my_commands(commands=commands_admin, scope=BotCommandScopeChat(chat_id=84131737))
    # await bot.set_my_commands(commands=commands_treasury, scope=BotCommandScopeChat(chat_id=-1001169382324))


async def on_startup(bot: Bot, dispatcher: Dispatcher):
    await set_commands(bot)
    with suppress(TelegramBadRequest):
        await bot.send_message(chat_id=MTLChats.ITolstov, text='Bot started')

    if config.test_mode:
        logger.info('test mode')
        # await pyro_start()
    else:
        global_tasks.append(asyncio.create_task(work_with_support()))
        await pyro_start()


async def on_shutdown(bot: Bot):
    with suppress(TelegramBadRequest):
        await bot.send_message(chat_id=MTLChats.ITolstov, text='Bot stopped')
    for task in global_tasks:
        task.cancel()


async def load_routers(dp: Dispatcher, bot: Bot):
    """Динамическая загрузка и регистрация роутеров"""
    import os

    routers_path = os.path.join(os.path.dirname(__file__), 'routers')
    router_modules = []
    registered_handlers = set()  # Для отслеживания уже зарегистрированных обработчиков

    # Загрузка всех модулей роутеров
    for filename in os.listdir(routers_path):
        if filename.endswith('.py') and not filename.startswith('__'):
            module_name = f'routers.{filename[:-3]}'
            try:
                module = importlib.import_module(module_name)
                if hasattr(module, 'register_handlers'):
                    # Проверка на дублирование модуля
                    if module.__name__ in registered_handlers:
                        logger.warning(f"Skipping duplicate router module: {module.__name__}")
                        continue

                    # Установка дефолтного приоритета, если не указан
                    if not hasattr(module.register_handlers, 'priority'):
                        module.register_handlers.priority = 50
                    router_modules.append(module)
                    registered_handlers.add(module.__name__)
                    logger.info(f"Found router module {module_name} with priority {module.register_handlers.priority}")
            except Exception as e:
                logger.error(f"Error loading module {module_name}: {e}", exc_info=True)

    # Сортировка модулей по приоритету
    router_modules.sort(key=lambda m: getattr(m.register_handlers, 'priority', 50))

    # Регистрация роутеров в порядке приоритета
    for module in router_modules:
        try:
            logger.debug(f"Registering handlers from {module.__name__}")
            module.register_handlers(dp, bot)
            logger.info(f"Successfully registered handlers from {module.__name__}")
        except Exception as e:
            logger.error(f"Error registering handlers from {module.__name__}: {e}", exc_info=True)

    logger.info(f"Total router modules loaded: {len(router_modules)}")


async def main():
    logger.add("logs/skynet.log", rotation="1 MB", level='INFO')

    # Запуск бота
    engine = create_engine(config.postgres_url, pool_pre_ping=True, max_overflow=50)
    # Creating DB connections pool
    db_pool = sessionmaker(bind=engine)

    # Creating bot and its dispatcher
    session: AiohttpSession = AiohttpSession()
    session.middleware(RetryRequestMiddleware())
    if config.test_mode:
        bot = Bot(token=config.test_token.get_secret_value(), default=DefaultBotProperties(parse_mode='HTML'),
                  session=session)
        logger.info('start test')
    else:
        bot = Bot(token=config.bot_token.get_secret_value(), default=DefaultBotProperties(parse_mode='HTML'),
                  session=session)

    redis = Redis.from_url(config.redis_url)
    storage = RedisStorage(redis=redis)
    dp = Dispatcher(storage=storage)

    global_tasks.append(asyncio.create_task(load_globals(db_pool(), bot)))

    # Настройка middleware
    app_context_middleware = AppContextMiddleware(bot)
    dp.message.middleware(DbSessionMiddleware(db_pool))
    dp.callback_query.middleware(DbSessionMiddleware(db_pool))
    dp.inline_query.middleware(DbSessionMiddleware(db_pool))
    dp.chat_member.middleware(DbSessionMiddleware(db_pool))
    dp.channel_post.middleware(DbSessionMiddleware(db_pool))
    dp.edited_channel_post.middleware(DbSessionMiddleware(db_pool))
    dp.poll_answer.middleware(DbSessionMiddleware(db_pool))
    
    dp.message.middleware(app_context_middleware)
    dp.callback_query.middleware(app_context_middleware)
    dp.inline_query.middleware(app_context_middleware)
    dp.chat_member.middleware(app_context_middleware)
    dp.channel_post.middleware(app_context_middleware)
    dp.edited_channel_post.middleware(app_context_middleware)
    dp.poll_answer.middleware(app_context_middleware)

    dp.message.middleware(ThrottlingMiddleware(redis=redis))
    dp.message.middleware(EmojiReactionMiddleware())

    dp['dbsession_pool'] = db_pool

    # Загрузка и регистрация роутеров
    await load_routers(dp, bot)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    dp.errors.register(sentry_error_handler)

    # Запускаем бота и пропускаем все накопленные входящие
    # Да, этот метод можно вызвать даже если у вас поллинг
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info(dp.resolve_used_update_types())
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


async def load_globals(session: Session, bot: Bot):
    for user in ChatsRepository(session).load_bot_users():
        global_data.users_list[user.user_id] = user.user_type
    with suppress(TelegramBadRequest):
        await bot.send_message(chat_id=MTLChats.ITolstov, text='globals loaded')


def add_bot_users(session: Session, user_id: int, username: str | None, new_user_type: int = 0):
    """Добавляет или обновляет пользователя в списке с логированием"""
    global_data.add_user(user_id, new_user_type)
    # user_type = 1 if good else 2
    # -1 one mistake -2 two mistake
    ### user_type_now = global_data.users_list.get(user_id)
    ### # Проверяем, существует ли пользователь, его текущий тип не равен 2, и новый тип больше текущего
    ### if not user_type_now or (new_user_type > user_type_now):
    ChatsRepository(session).save_bot_user(user_id, username, new_user_type)


if __name__ == "__main__":
    if len(config.sentry_dsn) > 20:
        sentry_sdk.init(
            dsn=config.sentry_dsn,
            traces_sample_rate=1.0,
            profiles_sample_rate=1.0,
        )
    else:
        logger.warning("sentry_dsn is bad. Not start it")
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
