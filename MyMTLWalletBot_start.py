import aiogram
from MyMTLWalletBot_main import dp, scheduler
import MyMTLWalletBot_handlers


# from aiogram.utils.markdown import bold, code, italic, text, link

# https://docs.aiogram.dev/en/latest/quick_start.html
# https://surik00.gitbooks.io/aiogram-lessons/content/chapter3.html

def unhit():
    pass
    MyMTLWalletBot_handlers.cmd_all()
    #mtl_bot_state_handlers.cmd_mtlcamp0()
    #mtl_bot_talk_handlers.has_words(None, None)
    #mtl_bot_poll_handlers.cmd_save()


if __name__ == "__main__":
    # Запуск бота
    #scheduler.start()
    #mtl_bot_time_handlers.scheduler_jobs(scheduler, dp)
    aiogram.executor.start_polling(dp, skip_updates=True)
