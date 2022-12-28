from aiogram import types
from loguru import logger

from skynet_main import dp, scheduler
import importlib
import aiogram
import skynet_first_handlers
import skynet_time_handlers
import skynet_poll_handlers
import skynet_state_handlers
import skynet_talk_handlers


# from aiogram.utils.markdown import bold, code, italic, text, link

# https://docs.aiogram.dev/en/latest/quick_start.html
# https://surik00.gitbooks.io/aiogram-lessons/content/chapter3.html

@dp.message_handler(commands="poll_reload_vote")
async def cmd_poll_check(message: types.Message):
    if message.from_user.username == "itolstov":
        print(skynet_poll_handlers.cmd_save_votes())
        importlib.reload(skynet_poll_handlers)
        await message.reply('reload complete')
    else:
        await message.answer("Не положено, хозяин не разрешил.")


info_cmd = {
    "/start": "начать все с чистого листа",
    "/links": "показать полезные ссылки",
    "/dron2": "открыть линию доверия дрону2",
    "/mtlcamp": "открыть линию доверия mtlcamp",
    "/blacklist": "операции с блеклистом",
    "/get_vote_fund_xdr": "сделать транзакцию на обновление голосов фонда",
    "/get_vote_city_xdr": "сделать транзакцию на обновление голосов сити",
    "/get_mrxpinvest_xdr": "сделать транзакцию на дивы mrxpinvest (div)",
    "/editxdr": "редактировать транзакцию",
    "/show_bdm": "показать инфо по БОД",
    "/drink": " попросить тост",
    "/decode": "декодирует xdr использовать: /decode xdr где ",
    "/do_div": "начать выплаты дивидентов",
    "/all": "тегнуть всех пользователей. работает зависимо от чата. и только  в рабочих чатах",
    "/gen_data": "сгенерить xdr для сохранения данных в стеларе. например для bdm или делигирования. Использовать : /gen_data public_key data_name:data_value",
    "/show_data": "Показать какие данные есть в стеларе на этот адрес. Use: /show_data public_key",
    "/show_data bdm": "Показать какие данные есть в стеларе по боду",
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
    "Скайнет хочется стабильности": "Попросить Скайнет поворчать про стабильность",
    "/delete_income": "Разрешить боту удалять сообщения о входе и выходе участников чата",
    "/delete_welcome": "Отключить сообщения приветствия",
    "/set_welcome": "Установить сообщение приветствия при входе. Шаблон на имя $$USER$$",
    "/set_welcome_button": "Установить текст на кнопке капчи",
    "/set_captcha on": "Включает капчу",
    "/set_captcha off": "Выключает капчу",
    "/set_check_welcome": "Установить отслеживания с добавлением в /all",
    "/add_all": "Добавить пользователей в /all. запуск с параметрами /add_all @user1 @user2 итд",
    "/del_all": "Убрать пользователей в /all. запуск с параметрами /del_all @user1 @user2 итд",
    "/save_all": "Добавлять пользователей в /all при входе",
    "/show_key_rate": "Показать сколько начислено мулек по ключевой ставке на всех",
    "/show_key_rate key": "Показать сколько начислено мулек по ключевой ставке на указанный адрес",
    "/balance": "Показать сколько денег или мулек(EURMTL) в кубышке",
    "Скайнет сколько в кубышке": "Показать сколько денег или мулек(EURMTL) в кубышке",
    "/update_airdrops": "Обновить файл airdrops",
    "/do_key_rate": "Запустить выплату по ключевой ставке",
    "/add_skynet_admin": "Добавить пользователей в админы скайнета. запуск с параметрами /add_skynet_admin @user1 @user2 итд",
    "/del_skynet_admin": "Убрать пользователей из админов скайнета. запуск с параметрами /del_skynet_admin @user1 @user2 итд",
    "/show_skynet_admin": "Показать админов скайнета",
    "/fee": "показать комиссию в стелларе",
    "/show_id": "Показать ID чата",
    "/do_resend": "Переотправить транзакцию. Только для админов",
    "/check_dg": "Проверить членов GP. Только для админов"
}

global_dict = {}


@dp.inline_handler(state="*")
async def inline_handler(query: types.InlineQuery):
    switch_text = "По Вашему запросу найдено :"
    answers = []
    for key, value in info_cmd.items():
        if (key.upper().find(query.query.upper()) > -1) or (value.upper().find(query.query.upper()) > -1):
            answers.append(types.InlineQueryResultArticle(
                id=str(len(answers)),
                title=key,
                description=value,
                input_message_content=types.InputTextMessageContent(key),
            ))
    return await query.answer(answers, cache_time=60, switch_pm_text=switch_text, switch_pm_parameter="xz")


@logger.catch
def main():
    # Запуск бота
    scheduler.start()
    skynet_time_handlers.scheduler_jobs(scheduler, dp)
    dp.register_message_handler(skynet_talk_handlers.cmd_last_check, state='*')
    aiogram.executor.start_polling(dp, skip_updates=True)


if __name__ == "__main__":
    main()
