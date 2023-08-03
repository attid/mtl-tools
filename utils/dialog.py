import asyncio
import json
from datetime import datetime, date
import random
import openai
from aioredis import Redis
from loguru import logger

from config_reader import config
from utils.gspread_tools import gs_save_new_task

save_time_long = 60 * 60 * 2
redis = Redis(host='localhost', port=6379, db=6)
openai_key = config.openai_key.get_secret_value()


# https://dialogflow.cloud.google.com/#/editAgent/mtl-skynet-hldy/


async def save_to_redis(chat_id, msg, is_answer=False):
    data_name = f'{chat_id}:{round(datetime.now().timestamp())}'
    j = {"content": msg}
    if is_answer:
        j["role"] = "assistant"
    else:
        j["role"] = "user"
    await redis.set(data_name, json.dumps(j))
    await redis.expire(data_name, save_time_long)


async def load_from_redis(chat_id):
    keys = await redis.keys(f'{chat_id}:*')
    messages = []

    for key in keys:
        value = await redis.get(key)
        # извлекаем сообщение и добавляем его в список сообщений
        message = json.loads(value)
        # извлекаем timestamp из ключа
        _, timestamp = key.decode().split(":")
        # добавляем сообщение и соответствующий timestamp в список
        messages.append((float(timestamp), message))

    # сортируем сообщения по времени
    messages.sort(key=lambda x: x[0])

    # возвращаем только сообщения, без timestamp
    return [msg for _, msg in messages]


async def delete_last_redis(chat_id):
    keys = await redis.keys(f'{chat_id}:*')

    if not keys:  # проверяем, есть ли ключи
        return

    # Извлекаем timestamp из каждого ключа и сортируем ключи по времени
    keys.sort(key=lambda key: float(key.decode().split(":")[1]))

    # Удаляем ключ с наибольшим значением времени (т.е. последний ключ)
    await redis.delete(keys[-1])


async def talk(chat_id, msg):
    await save_to_redis(chat_id, msg)
    msg_data = await load_from_redis(chat_id)
    msg = await talk_open_ai_async(msg_data=msg_data)
    if msg:
        await save_to_redis(chat_id, msg, is_answer=True)
        return msg
    else:
        await delete_last_redis(chat_id)
        return '=( connection error, retry again )='


async def talk_open_ai_list_models():
    openai.organization = "org-Iq64OmMI81NWnwcPtn72dc7E"
    openai.api_key = openai_key
    # list models
    models = openai.Model.list()
    print(list(models))
    for raw in models['data']:
        if raw['id'].find('gpt') > -1:
            print(raw['id'])
    # print(raw)
    # gpt-3.5-turbo-0613
    # gpt-3.5-turbo-16k-0613
    # gpt-3.5-turbo-16k
    # gpt-3.5-turbo-0301
    # gpt-3.5-turbo


async def talk_open_ai_async(msg=None, msg_data=None, user_name=None, b16k=False):
    openai.organization = "org-Iq64OmMI81NWnwcPtn72dc7E"
    openai.api_key = openai_key
    # list models
    # models = openai.Model.list()

    if msg_data:
        messages = msg_data
    else:
        messages = [{"role": "user", "content": msg}]
        if user_name:
            messages[0]["name"] = user_name
    try:
        print('****', messages)
        if b16k:
            chat_completion_resp = await openai.ChatCompletion.acreate(model="gpt-3.5-turbo-16k", messages=messages)
        else:
            chat_completion_resp = await openai.ChatCompletion.acreate(model="gpt-3.5-turbo", messages=messages)
        return chat_completion_resp.choices[0].message.content
    except openai.error.APIError as e:
        logger.info(e.code)
        logger.info(e.args)
        return None


async def talk_get_comment(chat_id, article):
    messages = [{"role": "system",
                 "content": "Напиши комментарий к статье, ты сторонник либертарианства. Комментарий должен быть прикольный, дружественный, не более 300 символов. Не указывай, что это комментарий или анализируй его. Напиши комментарий сразу, без введения или заключения. Не используй кавычки в ответе. Не используй хештеги # в комментариях !"},
                {"role": "user", "content": article}]
    await save_to_redis(chat_id, article)
    msg = await talk_open_ai_async(msg_data=messages)
    if msg:
        await save_to_redis(chat_id, msg, is_answer=True)
        return msg
    else:
        await delete_last_redis(chat_id)
        return '=( connection error, retry again )='


gor = (
    ("Овен", "Телец", "Близнецы", "Рак", "Лев", "Дева", "Весы", "Скорпион", "Стрелец", "Козерог", "Водолей", "Рыбы"),
    ("Расположение звезд ", "Расположение планет ", "Марс ", "Венера ", "Луна ", "Млечный путь ", "Астральные карта ",
     "Юпитер ", "Плутон ", "Сатурн ",),
    ("говорит вам ", "советует вам ", "предлагает вам ", "предрекает вам ", "благоволит вас ", "рекомендует вам ",
     "очень рекомендует вам ", "намекает вам ", "требует от вас ",),
    ("выпить пива", "напиться в хлам", "выпить никшечко", "выпить нефильтрованного никшечко", "выпить темного никшечко",
     "выпыть хугардена", "сегодня не пить =(", "хорошо приглядывать за орешками", "выпить чего по крепче",
     "пить сегодня с хорошей закуской", "поберечь печень", "нагрузить печень", "выпить ракии", "выпить дуньки",
     "выпить лозы", "выпить каспии", "сообразить на троих",)
)

lang_dict = {}


def get_horoscope() -> list:
    if date.today() == lang_dict.get('horoscope_date'):
        return lang_dict.get('horoscope', ['Ошибка при получении =('])
    else:
        today_dic = [""]
        s3 = ""
        lang_dict['horoscope_date'] = date.today()
        horoscope = ["Гороскоп на сегодня"]
        for s in gor[0]:
            horoscope.append(f'**{s}**')
            while s3 in today_dic:
                s3 = random.choice(gor[3])
            today_dic.append(s3)

            g = (random.choice(gor[1]) + random.choice(gor[2]) + s3)
            while g in horoscope:
                g = (random.choice(gor[1]) + random.choice(gor[2]) + s3)
            horoscope.append(g)

        horoscope.append("")
        horoscope.append("Желаю всем хорошего дня! 🍺🍺🍺")
        lang_dict['horoscope'] = horoscope
        return horoscope


async def talk_check_spam(article):
    messages = [{"role": "system",
                 "content": "Вы являетесь виртуальным ассистентом, специализирующимся на выявлении спама в объявлениях. Ваша задача - проанализировать предоставленные объявления и определить, являются ли они спамом. Предоставьте свой ответ в виде процентной вероятности, что данное объявление является спамом. Ваша оценка должна быть выражена в числовом формате, например, 70.0 для 70% вероятности. Никакого текста, только 2 цифры. Верни сообщение длиной в 2 символа."},
                {"role": "user", "content": article}]
    msg = None
    while msg is None:
        msg = await talk_open_ai_async(msg_data=messages)
        if not msg:
            await asyncio.sleep(1)
        if len(msg) > 3:
            logger.info(msg)
            msg = None
    return float(msg)


async def add_task_to_google(msg):
    # https://platform.openai.com/docs/guides/gpt/function-calling
    # Step 1: send the conversation and available functions to GPT
    openai.organization = "org-Iq64OmMI81NWnwcPtn72dc7E"
    openai.api_key = openai_key

    messages = [{"role": "user", "content": msg}]
    #async def gs_save_new_task(task_name, customer, manager, executor, contract_url):
    functions = [
        {
            "name": "gs_save_new_task",
            "description": "Добавляет задачу в таблицу задач",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_name": {
                        "type": "string",
                        "description": "Описание задачи",
                    },
                    "customer": {
                        "type": "string",
                        "description": "Заказчик, может быть None",
                    },
                    "manager": {
                        "type": "string",
                        "description": "Менеджер задачи, может быть None",
                    },
                    "executor": {
                        "type": "string",
                        "description": "Исполнитель, по умолчанию пользователь который дает задачу",
                    },
                    "contract_url": {
                        "type": "string",
                        "description": "Ссылка на задачу, по умолчанию ссылка на прошлое сообщение",
                    },
                    #"unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                },
                "required": ["task_name", "executor", "contract_url"],
            },
        }
    ]
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-0613",
        messages=messages,
        functions=functions,
        function_call="auto",  # auto is default, but we'll be explicit
    )
    response_message = response["choices"][0]["message"]

    # Step 2: check if GPT wanted to call a function
    if response_message.get("function_call"):
        # Step 3: call the function
        # Note: the JSON response may not always be valid; be sure to handle errors
        available_functions = {
            "gs_save_new_task": gs_save_new_task,
        }  # only one function in this example, but you can have multiple
        function_name = response_message["function_call"]["name"]
        function_to_call = available_functions[function_name]
        function_args = json.loads(response_message["function_call"]["arguments"])
        # async def gs_save_new_task(task_name, customer, manager, executor, contract_url):
        function_response = await function_to_call(
            task_name=function_args.get("task_name"),
            customer=function_args.get("customer"),
            manager=function_args.get("manager"),
            executor=function_args.get("executor"),
            contract_url=function_args.get("contract_url"),
        )

        # Step 4: send the info on the function call and function response to GPT
        messages.append(response_message)  # extend conversation with assistant's reply
        messages.append(
            {
                "role": "function",
                "name": function_name,
                "content": function_response,
            }
        )  # extend conversation with function response
        second_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-0613",
            messages=messages,
        )  # get a new response from GPT where it can see the function response
        return second_response.choices[0].message.content


async def talk_get_summary(article):
    messages = [{"role": "system",
                 "content": "Вы являетесь виртуальным ассистентом, специализирующимся на анализе текстов. Ваша задача - проанализировать предоставленный текст чата и предоставить краткий обзор его содержания."},
                {"role": "user", "content": article}]
    msg = None
    while msg is None:
        msg = await talk_open_ai_async(msg_data=messages, b16k=True)
        if not msg:
            logger.info('msg is None')
            await asyncio.sleep(3)
    return msg


if __name__ == "__main__":
    pass
    #print(asyncio.run(add_task_to_google('Скайнет, задача. Добавь задачу , заказчик эни, ссылка ya.ru , описание "Добавить новые поля в отчет"')))
    #asyncio.run(talk_open_ai_list_models())

    # article  = '''привет, ищу где купить мыло '''
    # print(asyncio.run(talk_check_spam(article)))
    #print(asyncio.run(talk(0,'Расскажи сказку про колобка на 10000 знаков')))
    arr= [{'role': 'system',
            'content': 'Вы являетесь виртуальным ассистентом, специализирующимся на анализе текстов. Ваша задача - проанализировать предоставленный текст чата и предоставить краткий обзор его содержания.'},
           {'role': 'user',
            'content': 'itolstov: На андроиде красивее выглядит, просто иконка бота\n\nitolstov: Сама верещала от радости, когда Соз показал :) Можно вынести себе в виджет все самые актуальные чаты и забыть про сотни флудилок навсегда 😁\n\nitolstov: Я пока просто приколол в одной из папок, а вот как тотал рачун приколоть - я не знаю\n\nitolstov: Перешли сообщение с тотал рачун из чата в бота, и запинь\n\nitolstov: Кстати чета не радит тотал рачун сегодня. 😒\n\nitolstov: Бум разбираццо.\n\nitolstov: Тут, кажется, нужно не все 9 часов смотреть, а только те моменты, когда открывался холодильник, и сопоставлять с тем, о каких позициях есть записи в рачунах. Соответственно скорость х5 подойдет, т.к. нет необходимости отслеживать было ли сообщено устно (если было, то будет запись в рачунах)\n\nА еще можно вебкамеру включать на 3 минуты после каждого открытия холодильника, тогда, вероятно, еще проще будет просматривать. (про датчик ты, собственно, сам выше написал)\n\nИ для того, чтобы исправлять процесс можно сделать так: если человек сам сообщил в клубобот, то цена обычная, а если человека пришлось искать, то цена увеличивается, т.к. было потрачено чье-то время. Если наценка 50%, то такой просмотр записей, вероятно, уже будет окупаться. \n\nСоответственно, можно предположить, что со временем просматривать нужно будет не так много, т.к. люди будут больше обращать на это внимание (или не будут :) )\n\nitolstov: Можно посмотреть, сколько в месяц составляют потери. Если незначительные, то просто заложить их в расходы или наценку. И не городить сложных систем.\n\nitolstov: Наверное, правильнее будет назвать это не наценка, а "доп. услуга" по фиксации взятого)\n\nitolstov: абсолютно? нет, не позиционируют\n\nitolstov: Я искренне наслаждаюсь экспериментом) \nВторой год комьюнити из 100 человек, которые позиционирует себя как абсолютно доверяющие друг другу люди пытаются решить вопрос с оплатой товаров в двух холодильниках под камерами в закрытом от чужих людей помещении))))\n1) Предположу что сумарная недостача за период уже превышает 600-700€ которые окупили бы снековый автомат. \n2) Комьюнити не готово к "корефанскому" отношению к учёту. \n3) явное смещение состава в кодерскую среду - любая задача пытается решиться с помощью разработки, а не готовых решений\n\nitolstov: Я думаю основные потери - это когда хозяюшку попросили  внести, а она отвлеклась и забыла.\n\nitolstov: Я исключительно в аспекте продавец покупатель условного пива, не в общечеловеческом смысле.\n\nitolstov: Создаёшь папку с чатами и до пяти самых нужных ты можешь в каждой папке закрепить наверху\n\nitolstov: клуб позиционируется как «друзья с репутацией». друзьям всё можно, но если обманул, то уже не друг.\n\nя так понимаю. @sozidatel может иначе формулировать\n\nitolstov: 3 - этож интересно. мы вообще все в рамках социального эксперемента собрались\n\nitolstov: Сложно оценить.\nЯ наблюдал своими глазами, когда человек выставил на стол 4 баночки пива, достал телефон, сделал фото, что-то в телефоне потыкал, но в Клубобот эти фотографии так и не пришли. Когда пару часов спустя я в личке спросил, то фотография пришла-таки в Клубобот.\n\nПодозреваю в первый раз она либо ушла в чат бывшей, либо человек в итоге тупо забыл нажать кнопку "отправить".\n\nitolstov: нет, писать быстрее, чем фоткать и прикреплять\n\nitolstov: В папке можно закрепить до 100 чатов.\n\n5 — лимит для "папки" "все чаты".\n\nitolstov: Ну или так, да. То есть неумышленный человеческий фактор\n\nitolstov: Тем паче\n\nitolstov: Дальше. Снековый аппарат. Это я так понимаю, то, что знакомо мне, как вендинговый.\nНужен будет такой аппарат.\n\nУ нас сейчас в одном только холодильнике 30 наименований. Нужен соответствующий аппарат с функцией охлаждения.\n\nНу и "сухомятки" ещё где-то 20 позиций.\n\nРазмер от тик-така до сисек-двухлитровок (ну из больших ещё чипсы есть 230 грамм, принглсы.\n\nТы видишь подходящее решение для нас?\n\nitolstov: Так в боте где приложить фото есть сразу опция "сфотать напрямую"\n\nitolstov: Я очень рад твоему наслаждению :)\nЗаходи к нам почаще, проверяй на местах ;-)\n\nЗавтра вот будет коктель-бургер-пати.\n\nitolstov: Холодильник с электромеханическим замком\n1) биотехнология: пульт - у хозяюшки. Написал в Клубобот что хочешь купить - тебе открыли\n2) современные технологии: замок получает команду на открытие через Клубобот\n\nitolstov: Ну и ещё одно соображение против физических методов решения обсуждаемой проблемы.\n\nМы должны выглядеть НЕ как магазин/кафе. Т.к. мы в зоне чистой контрэкономике, в случае интереса со стороны каких-нибудь говнюков, всё должно выглядеть, как квартира очень общительного человека. Ни ценников нет, ни меню.. У меня дома просто куча запасов пива и снеков угощать друзей.\n\nitolstov: Тогда остаётся только "постом и молитвою"\n\nitolstov: Спасибо большое, ребзя я на пляже ещё ни разу не был какие заходы - у нас 24/7работа\n\nitolstov: Жетонник, или оплата по куаркоду\nДевайс не должен принимать настоящие деньги. Всё в вопрос с продажей решён. \nМодели разные есть и с разным количеством разноформатных ячеек обычно это 6*8, 7*8 и тд зависит от нужных размеров продукта. Свяжитесь с конторой и узнайте что есть. И почем - за спрос денег не возьмут. \nА по поводу прикрутить к таким автоматам оплату криптой или чём-то другим это реально востребованная  хрень, ищете де для акселерации проекты - а здесь и паяльник нужен и аппаратное решение и код чтоб прикрутить оплату с кошельков. \nРеальная тема, на клубе оттеснить и в мир продавать\n\nitolstov: А надо сначала прикреплять, а потом фоткать\n\nitolstov: вот 2 мне нравиться, потом можно пропинговать -  уважаемый ты открывал холодос и ничего не прислал. Не забыл ?\n\nitolstov: Все мы такие ;-)\n\nitolstov: Да. тоже мало кто знает.\n\n1. Зайти в Клубобот (у меня это один клик с главного экрана).\n2. Тапнуть скрепку.\n3. Тапнуть камеру.\n4. Навести камеру на цель, нажат "фото".\n5. Нажать отправить.\n\nБуквально 5 тапов.\n\nitolstov: Я иногда открываю и ничего не беру :)\n\nitolstov: Я тоже, ну ответишь что все норм, ничего не брал.\n\nitolstov: Ну да, можно так. Тем более, раз человек открыл холодильник, значит что телефон с открытым Клубоботом уже у него в руках :)\n\nВсего-ничего, найти такой замок, и сделать сервис, который по сигналу из Клубобота разомкнёт замок.\n\nВозможно ещё желательно другой холодильник, ибо этот недорогой бытовой может развалиться от редких попыток дёрнуть дверь, пока замок закрыт..\n\nitolstov: Куаркод на двери холодоса уже намекает, что не всё так просто\n\nitolstov: Ты читал сообщения выше?\n\nitolstov: Вот так говнюкам и будешь объяснять\n\nitolstov: Ты странный. QR код однозначно намекает на вакцину от ковида :)\n\nitolstov: Там супер нейтральный текст.\nС говнюками просто: да, в холодосе пивас для друзей. Я его заряжаю вон, в магазине рядом, они берут и возвращают мои расходы. Никакой торговли нет. Это как скинуться на шашлык там, или бензин.\n\nitolstov: вендинг не проще сразу взять?\n\nitolstov: Витринный холодильник: дверь прозрачная\n\nitolstov: Открутить ручку и добавить пружинку чтоб сам открывался 😎\n\nitolstov: да\n\nitolstov: обсуждается взять новый холодильник и приколхозить к нему замок )\n\nitolstov: Может, зря нагородили , а нужно просто попросить задонатить (именно задонатить, не купить фцмки) тех, кто потребляет в клубе пиво? А оно в каких-то абсолютно космических (для меня) объёмах потребляется - люди просто ничего не соображают, когда берут из холодильника очередную банку. Тот, кто себя узнал, задонатит по десятке, и вопрос решён. А вы уже какие-то вендинговые аппараты с приёмом крипты вводите - это же много дороже выйдет\n\nitolstov: Не мешай полету творческой мысли\n\nitolstov: Я щитаю с аппаратом хорошая идея. Вопрос цены и реализацаии\n\nitolstov: Ща ещё придёт Лях и прикрутит к вашему вендингу мини-реактор ядерный на случай отключения электричества, и тогда вообще заживёте.\n\nitolstov: Ну и вообще это всё же работа хозяюшки следить, кто и что берёт... Если везде делать самообслуживание без снижения наценок, которые в том числе идут на зарплату работникам клуба, мне не очень понятно, где заканчивается их сфера ответственности.\n\nitolstov: Вот конкретно про вендинг.\n\nitolstov: Тогда я не понял, почему ты предлагаешь вендинг в таймлайне, где обуждается идея взять вендинг.\n\nitolstov: Не припомню их с холодильником. Наверняка есть но уже подороже.\n\nitolstov: Хозяюшки — не реализаторы. На них висит тонна ответственности за всё, от смены тулетной бумаги в туалете до поломаной маркизы в недострое.\nДа, бывает что они выглядят, как скучающие и свободные. Иногда это так и есть, а иногда нет.\n\nitolstov: "Иногда, глядя с крыльца на двор и на пруд, говорил он о том, как бы хорошо было, если бы вдруг от дома провести подземный ход или чрез пруд выстроить каменный мост, на котором бы были по обеим сторонам лавки, и чтобы в них сидели купцы и продавали разные мелкие товары, нужные для крестьян."\n\nitolstov: У меня был такой дома.\nЖестокая вещь.. \n\nМиа говорит, я всё равно его открывал, смотрел, закрывал, повторял :)\n\nitolstov: Чаще всего хозяюшка всё же сидит на кухне и видит/должна видеть, кто что берёт.\n\nitolstov: Но нужна будет доп услуга открыватель пива упавшего с верхней полки\n\nitolstov: Во-во, всё удовольствие растрясётся\n\nitolstov: Изначально было как: ищите хозяюшку и попросите её что-то вам дать, и только если её нет в зоне видимости, берите сами и фотайте. Сейчас мы по сути расписываемся, что этот механизм не работает - значит, самое слабое звено в этой цепочке именно невнимание хозяюшки. Остальные люди гости, они имеют право на ошибку.\n\nitolstov: по дефолту они с холодильноком\n\nitolstov: Ну вот если будет доп услуга по отсмотру и вбиванию то кто то с выходного может заниматься, или дети типа Савы. И все в плюсе и это считай восстанавление напа.\n\nitolstov: Так и либертарианство пропадёт\n\nitolstov: https://s3.eu-central-1.amazonaws.com/web.repository/bel-media/files/1574434232-brosura-samousluzni-automati.pdf\n\nitolstov: За неимением на данный момент удовлетворительного решения предлагаю топить за сознательность. А то все они маргинализируют пивопийц. Так и до репрессий недалеко\n\nitolstov: Возможно это будет итоговым решением — отменить самозабор, как явление.\n\nitolstov: У тебя неприятная формулировка, перечитай мой пост в Клубе.\nЯ уверен, что всем можно доверить сильно больше, чем баночку никшичка.\nПросто люди — люди, и проёбываются. А это, к сожалению, бъёт по Клубу. \n\nТут предлагали просто оценить объёмы проёба и заложить это в маржу.\nТоже решение. Попробую оценить в деньгах.\n\nitolstov: А вы маржу только по алкоголю будете увеличивать, если что? Или по всему раскидывать? Второе считаю несправедливым\n\nitolstov: Отсмотр и вбивание оканчиваются только на предположениях. Мы видим спину Игоря, что подошла, открыла холодос, пошубуршала там руками, закрыла дверцу и вышла в недострой.\n\n— И-игорь, там позавчера в 21:18 ты открывал холодильник. Брал ли ты чего?\n\nitolstov: ну эт то же самое, что в клубобот постить, я так понял проблема в том, что мажоритарий ПКМ перестаёт доверять постояльцам.\n\nitolstov: увеличение цен приведет к тому что добросовестные гости будут брать меньше что приведет к еще большим потерям\n\nitolstov: рядом с холодильником поставить лазерный считыватель штрихкодов. руку протянул, пиво взял, считыватель просканировал и бутылку, и порядковый номер на рукаве\n\nitolstov: ...когда счет приближается к ящику, вспомнить тешко)))\n\nitolstov: Камеру в холодильник ? Отсматривать только когда светло (дверь открыли)\n\nitolstov: да и первое не очень\n\nitolstov: Зашел, поёрничал, на прямой вопрос по делу не ответил.\nКрасавец рыцарь :)\n\nP.S. Ладно, вижу печатает, видно это ответ по существу :)\n\nitolstov: Да. Наладить связку учета склада с продажами…\n\nitolstov: Вывод человека даже не узнавшего цену) а ведя я вас считаю людьми незашореными) пробующими новое)\n\nitolstov: Почти во всех твоих постах в таких ситуациях считывается язвительная интонация. Если это не так, извиняюсь.\n\nitolstov: А ошибся - уже возникла)\n\nitolstov: Может все же закотилось куда? Ну или кто вспомнит. Просто треть это довольно много. \n\nЯ вот тоже сходил в тотал рачун, проверил, вроде все есть что я брал. Может другие алкоголики тоже проверят и вспомнят чего.\n\nitolstov: Потом сверить с видео. \nНесколько раз забытухам предметно указать на косяк. \nТо е то.\n\nitolstov: На какое-то время это даст геморрой, зато потом полегчает. Наверное :)\n\nitolstov: Я предложил решение - оно никому не понравилось тк подразумевает траты вероятно акционеров, всём нравится обсуждать то что уже не сработало пока ты считаешь недостачу)\n\nitolstov: Есть способ отследить пропавший алкоголь, если перед каждым закрытием пересчитывать банки, пока свежа память о тех, кто был в клубе. Конкретно банки в холодильнике.\nИ сравнивать с клубоботом.\n\nitolstov: Я же ответил что знал\nКто-нибудь прочитал? \nПросто уточняющих вопросов по тексту не последовало, я решил всё ок.\n\nitolstov: Почитайте этот чат годовой давности диалог о холодидьнике недостачах и сознательности - под копирку) какое время нужно для проверки версии?\n\nitolstov: Честно не очень люблю, когда кто-то делает вид, что знает все ответы.\n\nitolstov: ребзя я хоть и не акционер но:\n1) схему с ответственностью граждан проверяли больше года - недостачи не уменьшаются, ок пора делать вывод. \n2) кто не понимает разницу между ФОТ и основными средствами - хозяюшка стоит 400€ в месяц(я условно тк не знаю сколько у них зп) это деньги в никуда, причём очень маленькие для них и весьма приличные ежемесячные для клуба - но за такую зп требовать от них ещё за каждым плечом стоять у уважаемых алкашей - ово йе дохуя делов, как и вешать недостачу на них. \nПокупка любого оборудования это разовые траты и если купить б/у при продаже через полгода потеря будет 50€. Рассмотрите это как инвест проект \n3) акционеры любят одно ла потому - попиздеть. А мажоритарий грустит над холодосом\n4) не ебите моск купите железку поиграйтесь продайте железку - скажите Петрович - отстань с советами.\n\nitolstov: Я знаю только ответ на этот вопрос - извините за подачу, хорошее настроение просто) игривое)\n\nitolstov: Нет, тебя спросили уточнить https://t.me/c/1589571284/1957\n\nitolstov: 1) Вангую - повысится прайс условно на 50центов и в течении короткого времени возникнет дискуссия - "хто-то пиздит или проëбывается а мы переплачиваем"\n\nitolstov: Я не люблю, раз уж мы разговорились от том кто чего любит, \n1)когда обобщают \n2) это просто сарказм \n3) когда эмоции от сказанного и подача важнее чем суть)\n\n'}]
    print(asyncio.run(talk_open_ai_async(b16k=True, msg_data=arr)))
    asyncio.run(asyncio.sleep(50))

    print(asyncio.run(talk_open_ai_async('Расскажи сказку про колобка на 10000 знаков', b16k=True)))
    asyncio.run(asyncio.sleep(50))
    print(asyncio.run(talk_open_ai_async('Расскажи сказку про колобка на 10000 знаков', b16k=True)))
    asyncio.run(asyncio.sleep(50))
    print(asyncio.run(talk_open_ai_async('Расскажи сказку про колобка на 10000 знаков', b16k=True)))
    asyncio.run(asyncio.sleep(50))
    print(asyncio.run(talk_open_ai_async('Расскажи сказку про колобка на 10000 знаков', b16k=True)))
    asyncio.run(asyncio.sleep(50))
    print(asyncio.run(talk_open_ai_async('Расскажи сказку про колобка на 10000 знаков', b16k=True)))
    asyncio.run(asyncio.sleep(50))
    print(asyncio.run(talk_open_ai_async('Расскажи сказку про колобка на 10000 знаков', b16k=True)))
    asyncio.run(asyncio.sleep(50))
    print(asyncio.run(talk_open_ai_async('Расскажи сказку про колобка на 10000 знаков', b16k=True)))
    asyncio.run(asyncio.sleep(50))
    print(asyncio.run(talk_open_ai_async('Расскажи сказку про колобка на 10000 знаков', b16k=True)))
    asyncio.run(asyncio.sleep(50))
    print(asyncio.run(talk_open_ai_async('Расскажи сказку про колобка на 10000 знаков', b16k=True)))
    asyncio.run(asyncio.sleep(50))
    print(asyncio.run(talk_open_ai_async('Расскажи сказку про колобка на 10000 знаков', b16k=True)))
    asyncio.run(asyncio.sleep(50))
    print(asyncio.run(talk_open_ai_async('Расскажи сказку про колобка на 10000 знаков', b16k=True)))
    asyncio.run(asyncio.sleep(50))
    print(asyncio.run(talk_open_ai_async('Расскажи сказку про колобка на 10000 знаков', b16k=True)))
    asyncio.run(asyncio.sleep(50))
    print(asyncio.run(talk_open_ai_async('Расскажи сказку про колобка на 10000 знаков', b16k=True)))
    asyncio.run(asyncio.sleep(50))
    print(asyncio.run(talk_open_ai_async('Расскажи сказку про колобка на 10000 знаков', b16k=True)))
    asyncio.run(asyncio.sleep(50))
    print(asyncio.run(talk_open_ai_async('Расскажи сказку про колобка на 10000 знаков', b16k=True)))
    asyncio.run(asyncio.sleep(50))
    print(asyncio.run(talk_open_ai_async('Расскажи сказку про колобка на 10000 знаков', b16k=True)))
    asyncio.run(asyncio.sleep(50))
    print(asyncio.run(talk_open_ai_async('Расскажи сказку про колобка на 10000 знаков', b16k=True)))
    asyncio.run(asyncio.sleep(50))
    print(asyncio.run(talk_open_ai_async('Расскажи сказку про колобка на 10000 знаков', b16k=True)))
    asyncio.run(asyncio.sleep(50))
    print(asyncio.run(talk_open_ai_async('Расскажи сказку про колобка на 10000 знаков', b16k=True)))
    asyncio.run(asyncio.sleep(50))
    print(asyncio.run(talk_open_ai_async('Расскажи сказку про колобка на 10000 знаков', b16k=True)))
    asyncio.run(asyncio.sleep(50))
    print(asyncio.run(talk_open_ai_async('Расскажи сказку про колобка на 10000 знаков', b16k=True)))
    asyncio.run(asyncio.sleep(50))
    print(asyncio.run(talk_open_ai_async('Расскажи сказку про колобка на 10000 знаков', b16k=True)))
    asyncio.run(asyncio.sleep(50))
    print(asyncio.run(talk_open_ai_async('Расскажи сказку про колобка на 10000 знаков', b16k=True)))
    asyncio.run(asyncio.sleep(50))
    print(asyncio.run(talk_open_ai_async('Расскажи сказку про колобка на 10000 знаков', b16k=True)))
    asyncio.run(asyncio.sleep(50))
