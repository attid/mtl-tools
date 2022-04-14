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
    if message.from_user.username == "itolstov":
        print(mtl_bot_poll_handlers.cmd_save_votes())
        importlib.reload(mtl_bot_poll_handlers)
        await message.reply('reload complete')
    else:
        await message.answer("Не положено, хозяин не разрешил.")


info_cmd = {
    "/start": "начать все с чистого листа",
    "/links": "показать полезные ссылки",
    "/dron2": "открыть линию доверия дрону2",
    "/mtlcamp": "открыть линию доверия mtlcamp",
    "/blacklist": "операции с блеклистом",
    "/getvotexdr": "сделать транзакцию на обновление голосов",
    "/editxdr": "редактировать транзакцию",
    "/show_bod": "показать инфо по БОД",
    "/drink": " попросить тост",
    "/decode": "декодирует xdr использовать: /decode xdr где ",
    "/do_div": "начать выплаты дивидентов",
    "/all": "тегнуть всех пользователей. работает зависимо от чата. и только  в рабочих чатах",
    "/gen_data": "сгенерить xdr для сохранения данных в стеларе. например для bod или делигирования. Использовать : /gen_data public_key data_name:data_value",
    "/show_data": "Показать какие данные есть в стеларе на этот адрес. Use: /show_data public_key",
    "/show_data bod": "Показать какие данные есть в стеларе по боду",
    "/show_data delegate": "Показать какие данные есть в стеларе по делегированию",
    "/show_data donate": "Показать какие данные есть в стеларе по донатам в правительство",
    "/poll": "Создать голование с учетом веса голосов, надо слать в ответ на стандартное голосование",
    "/poll_replace_text": "Заменить в спец голосовании текст на предлагаемый далее. Использовать /poll_replace_text new_text",
    "/poll_close": "Закрыть голосование. после этого нельзя голосовать или менять его.",
    "/poll_check": "Проверить кто не головал. Слать в ответ на спец голосование. 'кто молчит', 'найди молчунов', 'найди безбилетника'",
    "/poll_reload_vote": "Перечитать голоса из блокчейна",
    "skynet update donates": "Попросить Скайнет обновить табличку донатов",
    "Скайнет сгенери дивиденты на 100 мулек": "Попросить Скайнет сгенерить xdr для дивов. 'сгенери', 'сделай', 'подготовь' 'дивиденты', 'дивы'",
    "Скайнет напомни": "Попросить Скайнет напопнить про подпись транзакции. Только в рабочем чате.",
    "Скайнет обнови отчёт": "Попросить Скайнет обновить файл отчета. Только в рабочем чате.",
    "Скайнет обнови гарантов": "Попросить Скайнет обновить файл гарантов. Только в рабочем чате.",
    "Скайнет анекдот": "Попросить Скайнет рассказать анекдот",
    "Скайнет тост": "Попросить Скайнет сказать тост. 'выпьем', 'тост' ",
    "Скайнет умница": "Похвалить Скайнет",
    "Скайнет покажи сиськи": "Домогаться Скайнет ",
    "Скайнет хочется стабильности": "Попросить Скайнет поворчать про стабильность"
}


@dp.inline_handler(state="*")
async def inline_handler(query: types.InlineQuery):
    switch_text = "По Вашему запросу найдено :"
    answers = []
    for key, value in info_cmd.items():
        if (key.find(query.query) > -1) or (value.find(query.query) > -1):
            answers.append(types.InlineQueryResultArticle(
                id=str(len(answers)),
                title=key,
                description=value,
                input_message_content=types.InputTextMessageContent(key),
            ))
    return await query.answer(answers, cache_time=60, switch_pm_text=switch_text, switch_pm_parameter="xz")


if __name__ == "__main__":
    # Запуск бота
    scheduler.start()
    mtl_bot_time_handlers.scheduler_jobs(scheduler, dp)
    dp.register_message_handler(mtl_bot_talk_handlers.cmd_last_check, state='*')
    aiogram.executor.start_polling(dp, skip_updates=True)
