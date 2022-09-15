from datetime import datetime
import random

from aiogram import Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import fb
# from apscheduler.job import Job

import mystellar
from skynet_main import logger
from keyrate import show_key_rate


async def cmd_send_message_test(dp: Dispatcher, scheduler: AsyncIOScheduler):
    master_chat_id = -1001767165598
    # -1001767165598 тестовая группа
    # -1001239694752 подписанты
    # -1001169382324 garanteers EURMTL
    # FOND
    time = datetime.now().time()
    rand = random.randint(2, 10)
    job = scheduler.get_job('test')
    await dp.bot.send_message(master_chat_id, f"{time} {rand=} {job.next_run_time}")
    job.reschedule('interval', minutes=rand)
    if rand == 10:
        job.pause()


async def cmd_send_message_10m(dp: Dispatcher):
    logger.info(f'cmd_send_message_10m')
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
                                                       ['Payment', 'PathPaymentStrictSend', 'PathPaymentStrictReceive'])
    master_chat_id = -1001239694752
    if len(result) > 0:
        await dp.bot.send_message(master_chat_id, "Получены новые транзакции для MTL")
        for transaction in result:
            msg = f'\n'.join(transaction)
            if len(msg) > 4096:
                await dp.bot.send_message(master_chat_id, "Слишком много операций показаны первые ")
            await dp.bot.send_message(master_chat_id, msg[0:4000], disable_notification=True,
                                      disable_web_page_preview=True)

    # MTLand
    result = mystellar.cmd_check_new_asset_transaction('MTLand', mystellar.BotValueTypes.LastMTLandTransaction, 10,
                                                       ['Payment', 'PathPaymentStrictSend', 'PathPaymentStrictReceive'])
    master_chat_id = -1001239694752
    if len(result) > 0:
        await dp.bot.send_message(master_chat_id, "Получены новые транзакции для MTLand")
        for transaction in result:
            msg = f'\n'.join(transaction)
            if len(msg) > 4096:
                await dp.bot.send_message(master_chat_id, "Слишком много операций показаны первые ")
            await dp.bot.send_message(master_chat_id, msg[0:4000], disable_notification=True,
                                      disable_web_page_preview=True)

    logger.info(f'end cmd_send_message_10m')


async def cmd_send_message_key_rate(dp: Dispatcher):
    logger.info(f'cmd_send_message_singers')
    # -1001239694752 подписанты
    await dp.bot.send_message(-1001239694752, show_key_rate(''))


async def cmd_send_message_coochitse(dp: Dispatcher):
    logger.info(f'cmd_send_message_singers')
    # -1001239694752 подписанты
    await dp.bot.send_message(-1001239694752, 'Не пора ли с кучицы денег стрясти ? /all')


async def cmd_send_message_8h(dp: Dispatcher):
    logger.info(f'cmd_send_message_8h')
    master_chat_id = -1001239694752

    # balance Wallet
    if int(mystellar.get_balances('GB72L53HPZ2MNZQY4XEXULRD6AHYLK4CO55YTOBZUEORW2ZTSOEQ4MTL')['XLM']) < 100:
        await dp.bot.send_message(master_chat_id, 'Внимание Баланс MyMTLWallet меньше 100 !', disable_notification=True,
                                  disable_web_page_preview=True)

    # bot1
    dt = mystellar.cmd_check_last_operation('GCVF74HQRLPAGTPFSYUAKGHSDSMBQTMVSLKWKUU65ULEN7TL4N56IPZ7')
    now = datetime.now()
    delta = now - dt
    if delta.days > 0:
        await dp.bot.send_message(master_chat_id, 'Внимание по боту обмена 1 нет операций больше суток !',
                                  disable_notification=True, disable_web_page_preview=True)

    # bot2
    dt = mystellar.cmd_check_last_operation('GAEFTFGQYWSF5T3RVMBSW2HFZMFZUQFBYU5FUF3JT3ETJ42NXPDWOO2F')
    now = datetime.now()
    delta = now - dt
    if delta.days > 0:
        await dp.bot.send_message(master_chat_id, 'Внимание по боту обмена 2 нет операций больше суток !',
                                  disable_notification=True, disable_web_page_preview=True)

    # key rate
    # bot2
    dt = fb.execsql1('select max(t.dt_add) from t_keyrate t', [], datetime.now())
    dt = datetime.combine(dt, datetime.min.time())
    now = datetime.now()
    delta = now - dt
    if delta.days > 0:
        await dp.bot.send_message(master_chat_id, 'Внимание начислению key rate нет операций больше суток !',
                                  disable_notification=True, disable_web_page_preview=True)
    logger.info(f'end cmd_send_message_8h')


async def cmd_send_message_1m(dp: Dispatcher):
    for record in fb.execsql('select m.id, m.user_id, m.text, m.use_alarm from t_message m where m.was_send = 0'):
        await dp.bot.send_message(record[1], record[2], disable_notification=record[3] == 0,
                                  disable_web_page_preview=True)
        fb.execsql('update t_message m set m.was_send = 1 where m.id = ?', (record[0],))


def scheduler_jobs(scheduler: AsyncIOScheduler, dp):
    # scheduler.add_job(cmd_send_message_10m, "interval", minutes=10, jitter=120, args=(dp,))
    # scheduler.add_job(cmd_send_message_8h, "interval", hours=8, jitter=800, args=(dp,))
    scheduler.add_job(cmd_send_message_1m, "interval", minutes=1, args=(dp,))
    scheduler.add_job(cmd_send_message_key_rate, "cron", day_of_week='fri', hour=8, minute=10, args=(dp,))
    scheduler.add_job(cmd_send_message_coochitse, "cron", day=1, hour=8, minute=10, args=(dp,))

    # scheduler.add_job(cmd_send_message_test, "interval", minutes=1, args=(dp,scheduler,), id='test')
    # job.args = (dp, 25,)
    # await cmd_send_message_10м(dp)
