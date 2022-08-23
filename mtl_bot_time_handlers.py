import datetime
import random

from aiogram import Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler
# from apscheduler.job import Job

import mystellar
from mtl_bot_main import logger
from update_eurmtl_log import show_key_rate


async def cmd_send_message_test(dp: Dispatcher, scheduler: AsyncIOScheduler):
    master_chat_id = -1001767165598
    # -1001767165598 тестовая группа
    # -1001239694752 подписанты
    # -1001169382324 garanteers EURMTL
    # FOND
    time = datetime.datetime.now().time()
    rand = random.randint(2, 10)
    job = scheduler.get_job('test')
    await dp.bot.send_message(master_chat_id, f"{time} {rand=} {job.next_run_time}")
    job.reschedule('interval', minutes=rand)
    if rand == 10:
        job.pause()


async def cmd_send_message_singers(dp: Dispatcher):
    logger.info(f'cmd_send_message_singers')
    result = mystellar.cmd_check_new_fond_transaction(ignore_operation=['CreateClaimableBalance'])
    master_chat_id = -1001239694752
    # -1001767165598 тестовая группа
    # -1001239694752 подписанты
    # -1001169382324 garanteers EURMTL
    # FOND
    if len(result) > 0:
        await dp.bot.send_message(master_chat_id, "Получены новые транзакции")
        for transaction in result:
            msg = f'\n'.join(transaction)
            if len(msg) > 4096:
                await dp.bot.send_message(master_chat_id, "Слишком много операций показаны первые ")
            await dp.bot.send_message(master_chat_id, msg[0:4000])
    # EURDEBT
    result = mystellar.cmd_check_new_asset_transaction('EURDEBT', mystellar.BotValueTypes.LastDebtTransaction)
    master_chat_id = -1001169382324
    if len(result) > 0:
        await dp.bot.send_message(master_chat_id, "Получены новые транзакции для EURDEBT")
        for transaction in result:
            msg = f'\n'.join(transaction)
            if len(msg) > 4096:
                await dp.bot.send_message(master_chat_id, "Слишком много операций показаны первые ")
            await dp.bot.send_message(master_chat_id, msg[0:4000])
    # EURMTL
    result = mystellar.cmd_check_new_asset_transaction('EURMTL', mystellar.BotValueTypes.LastEurTransaction, 900,
                                                       ['Payment'])
    master_chat_id = -1001169382324
    if len(result) > 0:
        await dp.bot.send_message(master_chat_id, "Получены новые транзакции для EURMTL")
        for transaction in result:
            msg = f'\n'.join(transaction)
            if len(msg) > 4096:
                await dp.bot.send_message(master_chat_id, "Слишком много операций показаны первые ")
            await dp.bot.send_message(master_chat_id, msg[0:4000])
    # MTLRECT
    result = mystellar.cmd_check_new_asset_transaction('MTLRECT', mystellar.BotValueTypes.LastRectTransaction, -1,
                                                       ['Payment'])
    master_chat_id = -1001239694752
    if len(result) > 0:
        await dp.bot.send_message(master_chat_id, "Получены новые транзакции для MTLRECT")
        for transaction in result:
            msg = f'\n'.join(transaction)
            if len(msg) > 4096:
                await dp.bot.send_message(master_chat_id, "Слишком много операций показаны первые ")
            await dp.bot.send_message(master_chat_id, msg[0:4000], disable_notification=True,
                                      disable_web_page_preview=True)

    # MTL
    result = mystellar.cmd_check_new_asset_transaction('MTL', mystellar.BotValueTypes.LastMTLTransaction, 10,
                                                       ['Payment'])
    master_chat_id = -1001239694752
    if len(result) > 0:
        await dp.bot.send_message(master_chat_id, "Получены новые транзакции для MTL")
        for transaction in result:
            msg = f'\n'.join(transaction)
            if len(msg) > 4096:
                await dp.bot.send_message(master_chat_id, "Слишком много операций показаны первые ")
            await dp.bot.send_message(master_chat_id, msg[0:4000], disable_notification=True,
                                      disable_web_page_preview=True)
    logger.info(f'end cmd_send_message_singers')


async def cmd_send_message_key_rate(dp: Dispatcher):
    logger.info(f'cmd_send_message_singers')
    # -1001239694752 подписанты
    await dp.bot.send_message(-1001239694752, show_key_rate(''))


async def cmd_send_message_coochitse(dp: Dispatcher):
    logger.info(f'cmd_send_message_singers')
    # -1001239694752 подписанты
    await dp.bot.send_message(-1001239694752, 'Не пора ли с кучицы денег стрясти ? /all')


def scheduler_jobs(scheduler: AsyncIOScheduler, dp):
    scheduler.add_job(cmd_send_message_singers, "interval", minutes=10, jitter=120, args=(dp,))
    scheduler.add_job(cmd_send_message_key_rate, "cron", day_of_week='fri', hour=8, minute=10, args=(dp,))
    scheduler.add_job(cmd_send_message_coochitse, "cron", day=1, hour=8, minute=10, args=(dp,))
    # scheduler.add_job(cmd_send_message_test, "interval", minutes=1, args=(dp,scheduler,), id='test')
    # job.args = (dp, 25,)
    # await cmd_send_message_singers(dp)
