import asyncio
import json
from datetime import datetime, date
import random
import openai
from aioredis import Redis
from settings import opanaikey
from loguru import logger

save_time_long = 60 * 60 * 2
redis = Redis(host='localhost', port=6379, db=6)


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



async def talk_open_ai_async(msg=None, msg_data=None, user_name=None):
    openai.organization = "org-Iq64OmMI81NWnwcPtn72dc7E"
    openai.api_key = opanaikey
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


# messages array Required

# A list of messages describing the conversation so far.

# role string Required
# The role of the author of this message. One of system, user, or assistant.

# content string Required
# The contents of the message.

# name string Optional
# The name of the author of this message. May contain a-z, A-Z, 0-9, and underscores, with a maximum length of 64 characters.

if __name__ == "__main__":
    article  = '''*'''
    print(asyncio.run(talk_get_comment(1, article)))
    pass
    # print(talk(9, 'Как выглядит марс ?'))
    # print(asyncio.run(talk_open_ai_async('Привет, запомни, тебя зовут скайнет.')))
    # print(asyncio.run(talk_open_ai_async('Давай поиграем, представь тебя зовут Скайнет, ты продавец сладостей.')))

    # print(asyncio.run(talk(58, 'Давай поиграем, представь тебя зовут Скайнет, ты продавец сладостей.')))
    # print(asyncio.run(talk(58, 'Я тебе давал имя, Как тебя зовут ?')))
    # print(asyncio.run(talk(58, 'Взвесте мне 500 грамм ')))
