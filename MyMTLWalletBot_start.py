import aiogram
from MyMTLWalletBot_main import dp, scheduler
import MyMTLWalletBot_handlers
import MyMTLWalletBot_callbacks


# from aiogram.utils.markdown import bold, code, italic, text, link

# https://docs.aiogram.dev/en/latest/quick_start.html
# https://surik00.gitbooks.io/aiogram-lessons/content/chapter3.html

def un_hit():
    MyMTLWalletBot_handlers.cmd_all()
    MyMTLWalletBot_callbacks.cmd_all()


if __name__ == "__main__":
    # Запуск бота
    #scheduler.start()
    #mtl_bot_time_handlers.scheduler_jobs(scheduler, dp)
    aiogram.executor.start_polling(dp, skip_updates=True)
