import asyncio
import json
import sys
from datetime import datetime
import random
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

from other import aiogram_tools
from db.requests import db_load_new_message
from other.grist_tools import grist_manager, MTLGrist
from other.loguru_tools import safe_catch_async, safe_catch
from other.pyro_tools import remove_deleted_users
from other.stellar_tools import cmd_create_list, cmd_calc_usdm_daily, cmd_gen_xdr, cmd_send_by_list_id
from scripts.check_stellar import cmd_check_cron_transaction, cmd_check_grist, cmd_check_bot
from scripts.mtl_exchange import check_exchange_one
from scripts.mtl_exchange2 import check_mm, check_mmwb
from other.global_data import MTLChats
from scripts.update_report import lite_report


@safe_catch_async
async def cmd_send_message_test(bot: Bot):
    master_chat_id: int = MTLChats.TestGroup
    # FOND
    time = datetime.now().time()
    rand = random.randint(2, 10)
    # job = scheduler.get_job('test')
    await bot.send_message(master_chat_id, f"{time} {rand=} job.next_run_time")
    # job.reschedule('interval', minutes=rand)
    # if rand == 10:
    #    job.pause()


# async def cmd_send_message_key_rate(dp: Dispatcher):
#    logger.info(f'cmd_send_message_singers')
#    await dp.bot.send_message(MTLChats.SignGroup, show_key_rate(''), message_thread_id=59558)

@safe_catch_async
async def cmd_send_message_start_month(bot: Bot):
    logger.info('cmd_send_message_singers')
    await bot.send_message(MTLChats.SignGroup, 'Не пора ли с кучицы и GPA денег стрясти ? /all',
                           message_thread_id=59558)


@safe_catch_async
async def cmd_send_message_1m(bot: Bot, session_pool):
    with session_pool() as session:
        for record in db_load_new_message(session):
            try:
                if record.update_id > 0:
                    reply_markup = None
                    if len(record.button_json) > 10:
                        button_json = json.loads(record.button_json)
                        reply_markup = InlineKeyboardMarkup(inline_keyboard=[[
                            InlineKeyboardButton(text=button_json['text'],
                                                 url=button_json['link'])
                        ]])

                    await bot.edit_message_text(chat_id=record.user_id, message_id=record.update_id,
                                                text=record.text,
                                                disable_web_page_preview=True,
                                                reply_markup=reply_markup)
                else:
                    topic_id = record.topic_id if record.topic_id > 0 else None
                    await bot.send_message(record.user_id, record.text, disable_notification=record.use_alarm == 0,
                                           disable_web_page_preview=True, message_thread_id=topic_id)

                record.was_send = 1
                session.commit()
            except Exception as ex:
                record.was_send = 2
                session.commit()
                logger.error(f'Error in cmd_send_message_1m: {ex} {record}')


@safe_catch_async
async def time_check_ledger(bot: Bot, session_pool):
    return #Todo: fix it to NATS
    # with session_pool() as session:
    #     saved_ledger = int(db_load_bot_value_ext(session, 0, BotValueTypes.LastLedger, '45407700'))
    #     async with aiohttp.ClientSession() as httpsession:
    #         async with httpsession.get(config.horizon_url) as resp:
    #             json_resp = await resp.json()
    #             core_latest_ledger = int(json_resp['history_latest_ledger'])
    #             if core_latest_ledger > saved_ledger + 10:
    #                 db_send_admin_message(session,
    #                                       f'Отставание от горизонта больше чем {core_latest_ledger - saved_ledger}')
    #     queue_size = db_get_ledger_count(session)
    #     if queue_size > 10:
    #         db_send_admin_message(session, f'Очередь в обработке ledger {queue_size}!')


@safe_catch_async
async def time_check_mm(bot: Bot, session_pool):
    with session_pool() as session:
        await check_mm(session)


@safe_catch_async
async def time_check_mmwb(bot: Bot, session_pool):
    with session_pool() as session:
        await check_mmwb(session)


@safe_catch_async
async def time_clear(bot: Bot):
    chats = await grist_manager.load_table_data(
        MTLGrist.CONFIG_auto_clean,
        filter_dict={"enabled": [True]}
    )
    for chat in chats:
        try:
            chat_info = await bot.get_chat(chat['chat_id'])
            count = await remove_deleted_users(chat['chat_id'])
            if count > 0 :
                await bot.send_message(MTLChats.SpamGroup,f"Finished removing deleted users from {chat_info.full_name}. \n Total deleted users: {count}")
        except Exception as e:
            logger.error(f"Error in cmd_delete_dead_members: {e}")
            await bot.send_message(MTLChats.ITolstov,f"An error occurred while removing deleted users: {str(e)}")
        await asyncio.sleep(30)


@safe_catch_async
async def time_usdm_daily(session_pool, bot: Bot):
    with session_pool() as session:
        # новая запись
        # ('mtl div 17/12/2021')
        div_list_id = cmd_create_list(session, datetime.now().strftime('usdm div %d/%m/%Y'), 6)
        lines = []
        logger.info(f"Start div pays №{div_list_id}. Step (1/7)")
        result = await cmd_calc_usdm_daily(session, div_list_id)
        logger.info(f"Found {len(result)} addresses. Try gen xdr.")

        i = 1

        while i > 0:
            i = cmd_gen_xdr(session, div_list_id)
            logger.info(f"Div part done. Need {i} more. Step (3/7)")

        logger.info("Try send div transactions. Step (4/7)")
        i = 1
        e = 1
        while i > 0:
            try:
                i = await cmd_send_by_list_id(session, div_list_id)
                logger.info(f"Part done. Need {i} more. Step (5/7)")
            except Exception as err:
                logger.info(str(err))
                logger.error(f"Got error. New attempt {e}. Step (6/7)")
                e += 1
                await asyncio.sleep(10)
                if e > 20:
                    return

        logger.info("All work done. Step (7/7)")
        msg = (f"Start div pays №{div_list_id}.\n"
               f"Found {len(result)} addresses.\n"
               f"All work done.")
        await bot.send_message(MTLChats.USDMMGroup, msg)


@safe_catch
def scheduler_jobs(scheduler: AsyncIOScheduler, bot: Bot, session_pool):
    scheduler.add_job(cmd_send_message_1m, "interval", seconds=10, args=(bot, session_pool), misfire_grace_time=360)
    # scheduler.add_job(time_check_ledger, "interval", minutes=15, args=(bot, session_pool), misfire_grace_time=360,
    #                   jitter=5 * 60)
    scheduler.add_job(time_check_mm, "interval", hours=1, args=(bot, session_pool), misfire_grace_time=360,
                      jitter=10 * 60)
    scheduler.add_job(time_check_mmwb, "interval", hours=6, args=(bot, session_pool), misfire_grace_time=360,
                      jitter=10 * 60)

    scheduler.add_job(cmd_send_message_start_month, "cron", day=1, hour=8, minute=10, args=(bot,),
                      misfire_grace_time=360)
    ###########
    # m h  dom mon dow   command

    # Задача проверки транзакций Stellar каждые 5 минут
    # */5 * * * * /home/skynet_bot/deploy/check_stellar.sh check_transaction
    scheduler.add_job(cmd_check_cron_transaction, "interval", minutes=5, args=(session_pool,),
                      misfire_grace_time=360, jitter=60)

    # 30 */3 * * * /home/skynet_bot/deploy/check_stellar.sh check_grist
    scheduler.add_job(cmd_check_grist, "interval", hours=3, minutes=30,
                      misfire_grace_time=360, jitter=120)

    # Задача проверки бота Stellar три раза в день
    # 10 */6 * * * /home/skynet_bot/deploy/check_stellar.sh check_bot
    scheduler.add_job(cmd_check_bot, "interval", hours=6, minutes=10, args=(session_pool,),
                      misfire_grace_time=360, jitter=120)


    # обмен
    # */13 * * * * /home/skynet_bot/deploy/mtl_exchange.sh check_exchange
    # 17 10 * * * /home/skynet_bot/deploy/mtl_exchange.sh one_exchange
    # scheduler.add_job(check_exchange, "interval", minutes=13,
    #                   misfire_grace_time=360, jitter=120)
    scheduler.add_job(check_exchange_one, "interval", hours=18,
                      misfire_grace_time=360, jitter=120)


    # Другие задачи
    # 17 8 * * * /home/skynet_bot/deploy/mtl_backup.sh > /dev/null*
    # 25 8 * * * /home/skynet_bot/deploy/report.sh > /dev/null
    scheduler.add_job(lite_report, "cron", hour=8, minute=10, args=(session_pool,),
                      misfire_grace_time=360)

    scheduler.add_job(time_clear, "interval", hours=10, args=(bot,),
                      misfire_grace_time=360, jitter=120)
    # 30 */8 * * * /opt/firebird/bin/isql -i /db/archive.sql

    ##scheduler.add_job(cmd_send_message_test, "interval", minutes=1, args=(bot,), id='test')
    #### scheduler.add_job(cmd_send_message_10m, "interval", minutes=10, jitter=120, args=(dp,))
    #### scheduler.add_job(cmd_send_message_8h, "interval", hours=8, jitter=800, args=(dp,))
    ### scheduler.add_job(cmd_send_message_key_rate, "cron", day_of_week='fri', hour=8, minute=10, args=(dp,))

    # usdm divs
    scheduler.add_job(time_usdm_daily, "interval", hours=4, minutes=4, args=(session_pool, bot),
                      misfire_grace_time=360)
    ### job.args = (dp, 25,)
    ### await cmd_send_message_10м(dp)


def register_handlers(dp, bot):
    if 'test' not in sys.argv:
        scheduler = AsyncIOScheduler(timezone='Europe/Podgorica')  # str(tzlocal.get_localzone()))
        aiogram_tools.scheduler = scheduler
        scheduler.start()
        db_pool = dp['dbsession_pool']
        scheduler_jobs(scheduler, bot, db_pool)

        logger.info('router time_handlers was loaded')


register_handlers.priority = 90
