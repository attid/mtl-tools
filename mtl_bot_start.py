from aiogram import types
from mtl_bot_main import dp, scheduler
import importlib
import aiogram
import mtl_bot_first_handlers
import mtl_bot_time_handlers
import mtl_bot_poll_handlers
import mtl_bot_state_handlers
import mtl_bot_talk_handlers


# from aiogram.utils.markdown import bold, code, italic, text, link

# https://docs.aiogram.dev/en/latest/quick_start.html
# https://surik00.gitbooks.io/aiogram-lessons/content/chapter3.html

def unhit():
    mtl_bot_first_handlers.cmd_decode()
    mtl_bot_state_handlers.cmd_mtlcamp0()
    mtl_bot_talk_handlers.has_words(None, None)
    mtl_bot_poll_handlers.cmd_save()


@dp.message_handler(commands="poll_reload_vote")
async def cmd_poll_check(message: types.Message):
    print(mtl_bot_poll_handlers.cmd_save_votes())
    importlib.reload(mtl_bot_poll_handlers)
    await message.reply('reload complete')


@dp.inline_handler(state="*")
async def inline_handler(query: types.InlineQuery):
    switch_text = "Не найдено ссылок по данному запросу. Добавить »»"
    return await query.answer(
        [], cache_time=60, is_personal=True,
        switch_pm_parameter="add", switch_pm_text=switch_text)
    # articles = [types.InlineQueryResultArticle(
    #     id=item[0],
    #     title=item[1],
    #     description=f"https://youtu.be/{item[0]}",
    #     url=f"https://youtu.be/{item[0]}",
    #     hide_url=False,
    #     thumb_url=f"https://img.youtube.com/vi/{item[0]}/1.jpg",
    #     input_message_content=types.InputTextMessageContent(
    #         message_text=f"<b>{quote_html(item[1])}</b>\nhttps://youtu.be/{item[0]}",
    #         parse_mode="HTML"
    #     )
    # ) for item in user_links]
    # await query.answer(articles, cache_time=60, is_personal=True,
    #                    switch_pm_text="Добавить ссылку »»", switch_pm_parameter="add")


if __name__ == "__main__":
    # Запуск бота
    scheduler.start()
    mtl_bot_time_handlers.scheduler_jobs(scheduler, dp)
    dp.register_message_handler(mtl_bot_talk_handlers.cmd_last_check, state='*')
    aiogram.executor.start_polling(dp, skip_updates=True)
