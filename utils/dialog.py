import asyncio
import json
import random
from datetime import datetime, date
import tiktoken
import openai
from aioredis import Redis
from loguru import logger

from config_reader import config
from utils.gspread_tools import gs_save_new_task

MAX_TOKENS = 4000
save_time_long = 60 * 60 * 2
redis = Redis(host='localhost', port=6379, db=6)
openai_key = config.openai_key.get_secret_value()
enc = tiktoken.encoding_for_model("gpt-3.5-turbo")


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


def num_tokens_from_messages(messages, model="gpt-3.5-turbo"):
    """Возвращает количество токенов, используемых списком сообщений."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        print("Предупреждение: модель не найдена. Используется кодировка cl100k_base.")
        encoding = tiktoken.get_encoding("cl100k_base")

    if "gpt-3.5-turbo" in model or "gpt-4" in model:
        # Для моделей gpt-3.5-turbo и gpt-4
        tokens_per_message = 3
        tokens_per_name = 1
    else:
        raise NotImplementedError(
            f"""num_tokens_from_messages() не реализована для модели {model}. См. https://github.com/openai/openai-python/blob/main/chatml.md для информации о преобразовании сообщений в токены."""
        )

    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name

    num_tokens += 3  # каждый ответ начинается с 'assistant'
    return num_tokens


async def load_from_redis(chat_id):
    keys = await redis.keys(f'{chat_id}:*')
    messages = []

    for key in keys:
        value = await redis.get(key)
        message = json.loads(value)
        _, timestamp = key.decode().split(":")
        messages.append((float(timestamp), message))

    # Сортируем сообщения по времени (от самых старых к самым новым)
    messages.sort(key=lambda x: x[0])

    # Подсчитываем токены
    model = "gpt-3.5-turbo"  # Или используйте другую модель, если необходимо
    formatted_messages = [msg[1] for msg in messages]  # Форматируем сообщения для подсчета токенов
    total_tokens = num_tokens_from_messages(formatted_messages, model=model)
    logger.info(f"Total tokens: {total_tokens}")

    # Удаляем старые сообщения, если количество токенов превышает максимальное значение
    while total_tokens > MAX_TOKENS and messages:
        removed_message = messages.pop(0)
        total_tokens = num_tokens_from_messages([msg[1] for msg in messages], model=model)
        logger.info(f"Total tokens after removing: {total_tokens}")

    return [msg[1] for msg in messages]  # Возвращаем только данные сообщений


async def delete_last_redis(chat_id):
    keys = await redis.keys(f'{chat_id}:*')

    if not keys:  # проверяем, есть ли ключи
        return

    # Извлекаем timestamp из каждого ключа и сортируем ключи по времени
    keys.sort(key=lambda key: float(key.decode().split(":")[1]))

    # Удаляем ключ с наибольшим значением времени (т.е. последний ключ)
    await redis.delete(keys[-1])


async def talk(chat_id, msg, gpt4=False):
    await save_to_redis(chat_id, msg)
    if gpt4:
        msg = await talk_open_ai_async(msg=msg, gpt4=True)
    else:
        msg_data = await load_from_redis(chat_id)
        msg = await talk_open_ai_async(msg_data=msg_data)
    if msg:
        await save_to_redis(chat_id, msg, is_answer=True)
        return msg
    else:
        await delete_last_redis(chat_id)
        return '=( connection error, retry again )='


async def talk_open_ai_list_models(name_filter):
    openai.organization = "org-Iq64OmMI81NWnwcPtn72dc7E"
    openai.api_key = openai_key
    # list models
    models = openai.Model.list()
    print(list(models))
    for raw in models['data']:
        if raw['id'].find(name_filter) > -1:
            print(raw['id'])
    # print(raw)
    # gpt-3.5-turbo-0613
    # gpt-3.5-turbo-16k-0613
    # gpt-3.5-turbo-16k
    # gpt-3.5-turbo-0301
    # gpt-3.5-turbo


async def talk_open_ai_async(msg=None, msg_data=None, user_name=None, gpt4=False):
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
        # print('****', messages)
        if gpt4:
            chat_completion_resp = await openai.ChatCompletion.acreate(model="gpt-4", messages=messages)
        else:
            chat_completion_resp = await openai.ChatCompletion.acreate(model="gpt-3.5-turbo", messages=messages)
        return chat_completion_resp.choices[0].message.content
    except Exception as e:
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
    model = "gpt-4-turbo-preview"

    messages = [{"role": "user", "content": msg}]
    # async def gs_save_new_task(task_name, customer, manager, executor, contract_url):
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
                        "description": "Исполнитель, по умолчанию автор второго сообщения если нет другого в тексте",
                    },
                    "contract_url": {
                        "type": "string",
                        "description": "Ссылка на задачу, по умолчанию ссылка на первое сообщение",
                    },
                    # "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                },
                "required": ["task_name", "executor", "contract_url"],
            },
        }
    ]
    response = openai.ChatCompletion.create(
        model=model,
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
        messages.append({
            "role": "system",
            "content": "Пожалуйста, избегайте использования ссылок в вашем ответе."
        })
        second_response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
        )  # get a new response from GPT where it can see the function response
        return second_response.choices[0].message.content


async def talk_get_summary(article):
    messages = [{"role": "system",
                 "content": "Вы являетесь виртуальным ассистентом, специализирующимся на анализе текстов. Ваша задача - проанализировать предоставленный текст чата и предоставить краткий обзор его содержания."},
                {"role": "user", "content": article}]
    msg = None
    while msg is None:
        msg = await talk_open_ai_async(msg_data=messages, gpt4=True)
        if not msg:
            logger.info('msg is None')
            await asyncio.sleep(3)
    return msg


def generate_image(prompt, model="dall-e-3", n=1):
    openai.organization = "org-Iq64OmMI81NWnwcPtn72dc7E"
    openai.api_key = openai_key

    response = openai.Image.create(
        prompt=prompt,
        n=n,
        model=model
    )

    # Это вернет список URL изображений
    return [image['url'] for image in response['data']]


if __name__ == "__main__":
    pass
    # print(asyncio.run(add_task_to_google('Скайнет, задача. Добавь задачу , заказчик эни, ссылка ya.ru , описание "Добавить новые поля в отчет"')))
    text = '''
    сообщение от: sozidatel 
ссылка: https://t.me/c/1767165598/2780
текст: """Игорь, я недавно размышлял по теме телемедицины, и позволю себе накидать примерный ТЗ для более удобного бота обратной связи. Это может пригодиться и в других местах.

Всё, примерно, как сейчас, но добавляем поддержку топиков. У этого два смысла. Такое же плоский чат обратной связи, просто находится в определённом топике какого-то чата. По-моему уже тобою реализовано, и в этом моём сообщении не про это.

Моя идея следующая.
Чат обратной связи — топикизированный чат.

Когда человек в первый раз пишет, создаётся топик, с выбранной в настройках иконкой и названием согласно другим настройкам, но в целом содержащим имя того, кто обратился. Опционально префиксы, постфиксы, дата инициации и подобное.
Важно, что админы чата могут переименовывать топики для удобства, боту это фиолетово, он же ориентируется на айди.

В первом сообщении пишется сообщение от имени бота, оно же закрепляется. Там основные данные, такие как имя того, кто обратился, его айди, юзернейм и, важно, список других топиков, инициированных этим человеком (прошлые и будущие, в идеале с выделением этого конкретного топика (вы находитесь здесь).

Внутри топика идёт диалог с человеком, всё как обычно.

Есть комманда, мол, топик закончен. Тогда топик архивируется, а новые обращения человека породят новый топик.

Расширенная версия этой комманды позволит перенести часть общения в новый топик: я выделяю какую-либо реплику, в ответ на неё даю комманду, что топик закончен. Бот создаёт новый топик, ставит в него заголовочный закреп, как обычно, и переносит туда сообщение, на который я дал ответ + идущие ниже сообщения. Чтобы можно было перенести новый контекст в новый топик.

Перенесённые сообщения работают, как обычно, то есть если ответить на сообщение от человека, он получит этот ответ.

Примерно так, некоторые нюансы будут видны уже в реализации и можно будет уточнять по ходу дела."""


сообщение от: itolstov 
ссылка: https://t.me/c/1767165598/2816
текст: """т добавь задачу"""
'''
    p = asyncio.run(add_task_to_google(text))
    print(p)
    exit()

    # article  = '''привет, ищу где купить мыло '''
    # print(asyncio.run(talk_check_spam(article)))
    # print(asyncio.run(talk(0,'Расскажи сказку про колобка на 10000 знаков')))
    # asyncio.run(asyncio.sleep(50))
    # print(asyncio.run(talk_open_ai_async('Расскажи сказку про колобка на 10000 знаков', b16k=True)))
