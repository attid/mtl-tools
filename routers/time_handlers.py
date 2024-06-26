import json
from datetime import datetime
import random
import aiohttp
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger
from config_reader import config
from db.requests import db_load_new_message, db_send_admin_message, db_get_ledger_count, db_load_bot_value_ext
from scripts.mtl_exchange2 import check_mm, check_mmwb
from utils.global_data import MTLChats, BotValueTypes, global_data


@logger.catch
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

@logger.catch
async def cmd_send_message_start_month(bot: Bot):
    logger.info(f'cmd_send_message_singers')
    await bot.send_message(MTLChats.SignGroup, 'Не пора ли с кучицы и GPA денег стрясти ? /all',
                           message_thread_id=59558)


@logger.catch
async def cmd_send_message_1m(bot: Bot, session_pool):
    with session_pool() as session:
        for record in db_load_new_message(session):
            try:
                #    for record in fb.execsql('select first 10 m.id, m.user_id, m.text, m.use_alarm, m.update_id, m.button_json '
                if record.user_id == MTLChats.SignGroup:
                    await bot.send_message(record.user_id, record.text, disable_notification=record.use_alarm == 0,
                                           message_thread_id=59558, disable_web_page_preview=True)
                elif record.user_id == MTLChats.MTLAAgoraGroup:
                    await bot.send_message(record.user_id, record.text, disable_notification=record.use_alarm == 0,
                                           message_thread_id=5418, disable_web_page_preview=True)
                else:
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
                        await bot.send_message(record.user_id, record.text, disable_notification=record.use_alarm == 0,
                                               disable_web_page_preview=True)

                record.was_send = 1
                session.commit()
            except Exception as ex:
                record.was_send = 2
                session.commit()
                logger.error(f'Error in cmd_send_message_1m: {ex} {record}')


@logger.catch
async def time_check_ledger(bot: Bot, session_pool):
    with session_pool() as session:
        saved_ledger = int(db_load_bot_value_ext(session,0, BotValueTypes.LastLedger, '45407700'))
        async with aiohttp.ClientSession() as httpsession:
            async with httpsession.get(config.horizon_url) as resp:
                json_resp = await resp.json()
                core_latest_ledger = int(json_resp['history_latest_ledger'])
                if core_latest_ledger > saved_ledger + 10:
                    db_send_admin_message(session, f'Отставание от горизонта больше чем {core_latest_ledger - saved_ledger}')
        queue_size = db_get_ledger_count(session)
        if queue_size > 10:
            db_send_admin_message(session, f'Очередь в обработке ledger {queue_size}!')


@logger.catch
async def time_check_mm(bot: Bot, session_pool):
    with session_pool() as session:
        await check_mm(session)


@logger.catch
async def time_check_mmwb(bot: Bot, session_pool):
    with session_pool() as session:
        await check_mmwb(session)


@logger.catch
def scheduler_jobs(scheduler: AsyncIOScheduler, bot: Bot, session_pool):
    scheduler.add_job(cmd_send_message_1m, "interval", seconds=10, args=(bot, session_pool), misfire_grace_time=360)
    scheduler.add_job(time_check_ledger, "interval", minutes=15, args=(bot, session_pool), misfire_grace_time=360,
                      jitter=5 * 60)
    scheduler.add_job(time_check_mm, "interval", hours=1, args=(bot, session_pool), misfire_grace_time=360,
                      jitter=10 * 60)
    scheduler.add_job(time_check_mmwb, "interval", hours=6, args=(bot, session_pool), misfire_grace_time=360,
                      jitter=10 * 60)

    scheduler.add_job(cmd_send_message_start_month, "cron", day=1, hour=8, minute=10, args=(bot,),
                      misfire_grace_time=360)
    ##scheduler.add_job(cmd_send_message_test, "interval", minutes=1, args=(bot,), id='test')
    #### scheduler.add_job(cmd_send_message_10m, "interval", minutes=10, jitter=120, args=(dp,))
    #### scheduler.add_job(cmd_send_message_8h, "interval", hours=8, jitter=800, args=(dp,))
    ### scheduler.add_job(cmd_send_message_key_rate, "cron", day_of_week='fri', hour=8, minute=10, args=(dp,))

    ### job.args = (dp, 25,)
    ### await cmd_send_message_10м(dp)
