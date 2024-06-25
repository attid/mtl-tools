import asyncio
import json
from datetime import datetime

from aioredis import Redis

from utils.global_data import MTLChats
from utils.gspread_tools import gs_save_new_support

redis = Redis(host='localhost', port=6379, db=7)


async def save_to_redis(chat_id, data: dict):
    data_name = f'{chat_id}:{round(datetime.now().timestamp())}'
    await redis.set(data_name, json.dumps(data))


async def work_with_support():
    while True:
        await asyncio.sleep(10)
        keys:list = await redis.keys(f'{MTLChats.TestGroup}:*')
        keys.extend(await redis.keys(f'{MTLChats.HelperChat}:*'))
        messages = []
        for key in keys:
            value = await redis.get(key)
            # извлекаем сообщение и добавляем его в список сообщений
            message: dict = json.loads(value)
            # извлекаем timestamp из ключа
            _, timestamp = key.decode().split(":")
            # добавляем сообщение и соответствующий timestamp в список
            messages.append((float(timestamp), message, key))
            # print(message)

        if len(messages) > 0:
            # сортируем сообщения по времени
            messages.sort(key=lambda x: x[0])

            # проходим по всем сообщениям
            for msg in messages:
                if msg[1].get('closed'):
                    # закрываем
                    pass
                else:
                    # отправляем
                    await gs_save_new_support(user_id=msg[1]['user_id'], username=msg[1]['username'],
                                              agent_username=msg[1]['agent_username'], url=msg[1]['url'])
                await redis.delete(msg[2])
