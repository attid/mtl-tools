import json
from datetime import datetime
import random

from aiogram import Dispatcher, types
from aiogram.types import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

import fb
# from apscheduler.job import Job

from skynet_main import MTLChats
from keyrate import show_key_rate

@logger.catch
async def cmd_send_message_test(dp: Dispatcher, scheduler: AsyncIOScheduler):
    master_chat_id: int = MTLChats.TestGroup.value
    # FOND
    time = datetime.now().time()
    rand = random.randint(2, 10)
    job = scheduler.get_job('test')
    await dp.bot.send_message(master_chat_id, f"{time} {rand=} {job.next_run_time}")
    job.reschedule('interval', minutes=rand)
    if rand == 10:
        job.pause()


#async def cmd_send_message_key_rate(dp: Dispatcher):
#    logger.info(f'cmd_send_message_singers')
#    await dp.bot.send_message(MTLChats.SignGroup.value, show_key_rate(''), message_thread_id=59558)

@logger.catch
async def cmd_send_message_coochitse(dp: Dispatcher):
    logger.info(f'cmd_send_message_singers')
    await dp.bot.send_message(MTLChats.SignGroup.value, 'Не пора ли с кучицы и GPA денег стрясти ? /all',
                              message_thread_id=59558)

@logger.catch
async def cmd_send_message_1m(dp: Dispatcher):
    for record in fb.execsql('select first 10 m.id, m.user_id, m.text, m.use_alarm, m.update_id, m.button_json '
                             'from t_message m where m.was_send = 0'):
        try:
            if record[1] == MTLChats.SignGroup.value:
                await dp.bot.send_message(record[1], record[2], disable_notification=record[3] == 0,
                                          message_thread_id=59558, disable_web_page_preview=True, parse_mode=ParseMode.HTML)
            else:
                if record[4] > 0:
                    reply_markup = None
                    if len(record[5]) > 10:
                        button_json = json.loads(record[5])
                        reply_markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton(button_json['text'],
                                                                                                   url=button_json['link']))

                    await dp.bot.edit_message_text(chat_id=record[1], message_id=record[4], text=record[2],
                                                   disable_web_page_preview=True,
                                                   parse_mode=ParseMode.HTML, reply_markup=reply_markup)
                else:
                    await dp.bot.send_message(record[1], record[2], disable_notification=record[3] == 0,
                                              disable_web_page_preview=True, parse_mode=ParseMode.HTML)

            fb.execsql('update t_message m set m.was_send = 1 where m.id = ?', (record[0],))
        except Exception as ex:
            fb.execsql('update t_message m set m.was_send = 2 where m.id = ?', (record[0],))
            logger.error(f'Error in cmd_send_message_1m: {ex}')

@logger.catch
def scheduler_jobs(scheduler: AsyncIOScheduler, dp):
    # scheduler.add_job(cmd_send_message_10m, "interval", minutes=10, jitter=120, args=(dp,))
    # scheduler.add_job(cmd_send_message_8h, "interval", hours=8, jitter=800, args=(dp,))
    scheduler.add_job(cmd_send_message_1m, "interval", seconds=10, args=(dp,))
    # scheduler.add_job(cmd_send_message_key_rate, "cron", day_of_week='fri', hour=8, minute=10, args=(dp,))
    scheduler.add_job(cmd_send_message_coochitse, "cron", day=1, hour=8, minute=10, args=(dp,))


    # scheduler.add_job(cmd_send_message_test, "interval", minutes=1, args=(dp,scheduler,), id='test')
    # job.args = (dp, 25,)
    # await cmd_send_message_10м(dp)
