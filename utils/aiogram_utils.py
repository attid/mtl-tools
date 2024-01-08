from datetime import datetime, timedelta

from aiogram.client.session import aiohttp
from aiogram.filters import Filter
from aiogram.types import Message

from utils.global_data import MTLChats
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler: AsyncIOScheduler


async def is_admin(message: Message):
    members = await message.chat.get_administrators()
    if message.from_user.id == MTLChats.GroupAnonymousBot:
        return True
    try:
        chat_member = next(filter(lambda member: member.user.id == message.from_user.id, members))
    except StopIteration:
        return False
    return True


def add_text(lines, num_line, text):
    if len(lines) > num_line - 1:
        lines.pop(num_line - 1)
    lines.append(text)
    return "\n".join(lines)


def cmd_delete_later(message: Message, minutes=5):
    current_time = datetime.now()
    future_time = current_time + timedelta(minutes=minutes)
    scheduler.add_job(cmd_delete_by_scheduler, run_date=future_time, args=(message,))


async def cmd_delete_by_scheduler(message: Message):
    try:
        await message.delete()
    except:
        pass


async def multi_reply(message: Message, text: str):
    while len(text) > 0:
        await message.reply(text[:4000])
        text = text[4000:]


async def multi_answer(message: Message, text: str):
    while len(text) > 0:
        await message.answer(text[:4000])
        text = text[4000:]


def has_words(master, words_array):
    for word in words_array:
        if master.upper().find(word.upper()) > -1:
            return True
    return False


def start_words(master, words_array):
    if master:
        for word in words_array:
            if master.upper().startswith(word.upper()):
                return True
    return False


class HasText(Filter):
    def __init__(self, my_arr: tuple) -> None:
        self.my_arr = my_arr

    async def __call__(self, message: Message) -> bool:
        return has_words(message.text, self.my_arr)


class StartText(Filter):
    def __init__(self, my_arr: tuple) -> None:
        self.my_arr = my_arr

    async def __call__(self, message: Message) -> bool:
        return start_words(message.text, self.my_arr)


async def get_web_request(method, url, json=None, headers=None, data=None, return_type=None):
    async with aiohttp.ClientSession() as web_session:
        if method.upper() == 'POST':
            request_coroutine = web_session.post(url, json=json, headers=headers, data=data)
        elif method.upper() == 'GET':
            request_coroutine = web_session.get(url, headers=headers, params=data)
        else:
            raise ValueError("Неизвестный метод запроса")

        async with request_coroutine as response:
            if response.headers.get('Content-Type') == 'application/json' or return_type == 'json':
                return response.status, await response.json()
            else:
                return response.status, await response.text()
