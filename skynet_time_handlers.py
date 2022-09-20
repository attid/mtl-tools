from datetime import datetime
import random

from aiogram import Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import fb
# from apscheduler.job import Job

import mystellar
from skynet_main import logger, MTLChats
from keyrate import show_key_rate


async def cmd_send_message_test(dp: Dispatcher, scheduler: AsyncIOScheduler):
    master_chat_id = MTLChats.TestGroup
    # FOND
    time = datetime.now().time()
    rand = random.randint(2, 10)
    job = scheduler.get_job('test')
    await dp.bot.send_message(master_chat_id, f"{time} {rand=} {job.next_run_time}")
    job.reschedule('interval', minutes=rand)
    if rand == 10:
        job.pause()


async def cmd_send_message_key_rate(dp: Dispatcher):
    logger.info(f'cmd_send_message_singers')
    await dp.bot.send_message(MTLChats.SignGroup, show_key_rate(''))


async def cmd_send_message_coochitse(dp: Dispatcher):
    logger.info(f'cmd_send_message_singers')
    await dp.bot.send_message(MTLChats.SignGroup, 'Не пора ли с кучицы денег стрясти ? /all')


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
