import asyncio
import html
from contextlib import suppress
from datetime import datetime, timedelta

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Filter
from aiogram.types import Message, User, CallbackQuery, Chat, ChatMember, ReactionTypeCustomEmoji
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from middlewares.retry import logger
from other.config_reader import config
from other.global_data import MTLChats, global_data

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


def get_chat_link(chat: Chat):
    if chat.username:
        return f"@{chat.username} {chat.title}"

    return f"<a href='https://t.me/c/{chat.id}/999999999999'>{chat.title}</a>"


async def is_admin(event: Message | CallbackQuery, chat_id=None):
    if chat_id is None:
        if isinstance(event, CallbackQuery):
            chat_id = event.message.chat.id
        else:
            chat_id = event.chat.id

    user_id = get_user_id(event)

    if user_id == MTLChats.GroupAnonymousBot:
        return True

    if user_id == chat_id:
        return True

    with suppress(TelegramBadRequest):
        members = await event.bot.get_chat_administrators(chat_id=chat_id)
        return any(member.user.id == user_id for member in members)


def add_text(lines, num_line, text):
    if len(lines) > num_line - 1:
        lines.pop(num_line - 1)
    lines.append(text)
    return "\n".join(lines)


def cmd_delete_later(message: Message, minutes=5, seconds=None):
    current_time = datetime.now()
    if seconds:
        future_time = current_time + timedelta(seconds=seconds)
    else:
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




def get_username_link(user: User):
    full_name = html.unescape(user.full_name)
    if user.username:
        username = f'@{user.username} {full_name}'
    else:
        username = f'<a href="tg://user?id={user.id}">{full_name}</a>'
    return username


async def get_user_info(chat_id: int, user_id: int) -> ChatMember:
    bot = Bot(token=config.bot_token.get_secret_value())
    try:
        # Получение информации о пользователе
        chat_member = await bot.get_chat_member(chat_id, user_id)
        return chat_member
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        return None

# Пример вызова функции
async def main():
    chat_id = -1001429770534  # Замените на реальный chat_id
    user_id = 7539876829  # Замените на реальный user_id
    user_id2 = 7321780032  # Замените на реальный user_id

    user_info = await get_user_info(chat_id, user_id)
    if user_info:
        print(user_info)
    else:
        print("Не удалось получить информацию о пользователе.")

    user_info = await get_user_info(chat_id, user_id2)
    if user_info:
        print(user_info)
    else:
        print("Не удалось получить информацию о пользователе.")


async def main0():
    async with Bot(
        token=config.bot_token.get_secret_value(),
    ) as bot:
        await bot.set_message_reaction(chat_id='@Montelibero_ru', message_id=9544,
                                       reaction=[ReactionTypeCustomEmoji(custom_emoji_id='5458863124947942457')])


async def update_mongo_chats_names():
    chats = await global_data.mongo_config.get_all_chats()

    for chat in chats:
        try:
            async with Bot(
                token=config.bot_token.get_secret_value(),
            ) as bot:
                info = await bot.get_chat(chat_id=chat.chat_id)
                count = await global_data.mongo_config.update_chat_with_dict(chat.chat_id, {"username": info.username,
                                                                                      "name": info.title})
                print(count)
                await asyncio.sleep(0.5)
        except Exception as ex:
            logger.warning(ex)


if __name__ == '__main__':
    a = asyncio.run(update_mongo_chats_names())
    print(a)
