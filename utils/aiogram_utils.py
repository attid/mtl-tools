import html
from contextlib import suppress
from datetime import datetime, timedelta

import asyncio

from aiogram import Bot
from aiogram.client.session import aiohttp
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Filter
from aiogram.types import Message, User, CallbackQuery
from sentry_sdk.client import get_options

from config_reader import config
from utils.global_data import MTLChats, global_data
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler: AsyncIOScheduler
non_breaking_space = chr(0x00A0)


def get_user_id(user_id: Message | int | User | CallbackQuery):
    if isinstance(user_id, CallbackQuery):
        user_id = user_id.from_user.id
    elif isinstance(user_id, Message):
        user_id = user_id.from_user.id
    elif isinstance(user_id, User):
        user_id = user_id.id
    else:
        user_id = user_id

    return user_id


async def is_admin(event: Message | CallbackQuery, chat_id=None):
    if chat_id is None:
        chat_id = event.chat.id
    user_id = get_user_id(event)

    if user_id == MTLChats.GroupAnonymousBot:
        return True

    with suppress(TelegramBadRequest):
        members = await event.bot.get_chat_administrators(chat_id=chat_id)

    return any(member.user.id == user_id for member in members)


def add_text(lines, num_line, text):
    if len(lines) > num_line - 1:
        lines.pop(num_line - 1)
    lines.append(text)
    return "\n".join(lines)


def cmd_delete_later(message: Message, minutes=5):
    current_time = datetime.now()
    future_time = current_time + timedelta(minutes=minutes)
    scheduler.add_job(cmd_delete_by_scheduler, run_date=future_time, args=(message,))


async def cmd_sleep_and_delete(message: Message, sleep_time):
    """
    Asynchronous function that sleeps for a specified time and then attempts to delete a message.
    Args:
        message (Message): The message to be deleted.
        sleep_time: The time to sleep in seconds.
    """
    # asyncio.ensure_future(cmd_sleep_and_delete_task(message, sleep_time))
    return asyncio.create_task(cmd_sleep_and_delete_task(message, sleep_time))


async def cmd_sleep_and_delete_task(message: Message, sleep_time):
    await asyncio.sleep(sleep_time)
    try:
        await message.delete()
    except:
        pass


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


class ReplyToBot(Filter):
    async def __call__(self, message: Message, bot: Bot) -> bool:
        return message.reply_to_message and message.reply_to_message.from_user.id == bot.id


class ChatInOption(Filter):
    def __init__(self, name: str) -> None:
        self.attr_name = getattr(global_data, name)

    async def __call__(self, message: Message) -> bool:
        return message.chat.id in self.attr_name


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


async def get_debank_balance(account_id, chain='bsc'):
    url = ("https://pro-openapi.debank.com/v1/user/chain_balance"
           f"?id={account_id}"
           f"&chain_id={chain}")
    # url = ('https://pro-openapi.debank.com/v1/user/total_balance'
    #        '?id=0x0358d265874b5cf002d1801949f1cee3b08fa2e9'
    #        '&chain_id=bsc')

    headers = {
        'accept': 'application/json',
        'AccessKey': config.debank.get_secret_value()
    }
    status, response = await get_web_request('GET', url, headers=headers)
    if status == 200:
        # {'usd_value': 253279.1102783137}
        return float(response.get('usd_value'))
    else:
        raise Exception(f'Ошибка запроса: Статус {status}')


def get_username_link(user: User):
    full_name = html.unescape(user.full_name)
    if user.username:
        username = f'@{user.username} {full_name}'
    else:
        username = f'<a href="tg://user?id={user.id}">{full_name}</a>'
    return username


if __name__ == '__main__':
    a = asyncio.run(get_debank_balance('0x0358d265874b5cf002d1801949f1cee3b08fa2e9'))
    print(a)
