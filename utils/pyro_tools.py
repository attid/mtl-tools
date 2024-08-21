import asyncio
import html
import os
import re
import sys
from dataclasses import dataclass
from typing import Optional, List

from loguru import logger
from pyrogram import Client  # pyrofork
from pyrogram.enums import ChatMemberStatus
from sentry_sdk import capture_exception

from config_reader import config


# https://pyrofork.mayuri.my.id/main/api/client.html

@dataclass
class MessageInfo:
    chat_id: int
    message_id: int
    user_from: Optional[str] = None
    chat_name: Optional[str] = None
    thread_id: Optional[int] = None
    thread_name: Optional[int] = None
    message_text: Optional[str] = None
    reply_to_message: Optional['MessageInfo'] = None
    full_text: Optional[str] = None


@dataclass
class GroupMember:
    user_id: int
    username: Optional[str]
    full_name: str
    is_admin: bool


if 'test' in sys.argv or __name__ == "__main__":
    session_name = "test_session"
else:
    session_name = "pyro_session"

pyro_app = Client(session_name, api_id=config.pyro_api_id, api_hash=config.pyro_api_hash.get_secret_value(),
                  workdir=os.path.dirname(__file__))


def extract_telegram_info(url):
    pattern1 = r'https://t\.me/([^/]+)/(\d+)$'
    pattern2 = r'https://t\.me/c/(\d+)/(\d+)$'
    pattern3 = r'https://t\.me/([^/]+)/\d+/(\d+)$'
    pattern4 = r'https://t\.me/c/(\d+)/\d+/(\d+)$'

    match1 = re.match(pattern1, url)
    match2 = re.match(pattern2, url)
    match3 = re.match(pattern3, url)
    match4 = re.match(pattern4, url)

    if match1:
        return MessageInfo(chat_id=match1.group(1), message_id=int(match1.group(2)))
    elif match2:
        return MessageInfo(chat_id=int('-100' + match2.group(1)), message_id=int(match2.group(2)))
    elif match3:
        return MessageInfo(chat_id=match3.group(1), message_id=int(match3.group(2)))
    elif match4:
        return MessageInfo(chat_id=int('-100' + match4.group(1)), message_id=int(match4.group(2)))
    else:
        return None


async def pyro_update_msg_info(msg: MessageInfo):
    # await pyro_app.send_message("itolstov", "Greetings from **Pyrofork**!")

    message = await pyro_app.get_messages(chat_id=msg.chat_id, message_ids=msg.message_id)
    if message.chat.username:
        msg.chat_name = f"{message.chat.username} ({msg.chat_name})"
    else:
        msg.chat_name = message.chat.title

    msg.user_from = message.from_user.username if message.from_user.username else html.escape(
        message.from_user.full_name)

    if message.topics:
        msg.thread_id = message.topics.id
        msg.thread_name = message.topics.title

    if message.has_protected_content:
        return

    if message.reply_to_message:
        if message.reply_to_message:
            reply_text = None
            if message.reply_to_message.text:
                reply_text = message.reply_to_message.text.html
            elif message.reply_to_message.caption:
                reply_text = message.reply_to_message.caption.html

            msg.reply_to_message = MessageInfo(
                chat_id=message.reply_to_message.chat.id,
                message_id=message.reply_to_message.id,
                message_text=reply_text,
                user_from=message.reply_to_message.from_user.username,
            )

    if message.text:
        msg.message_text = message.text.html
    elif message.caption:
        msg.message_text = message.caption.html


async def pyro_start():
    try:
        await pyro_app.start()
    except Exception as e:
        logger.error(e)
        capture_exception(e)
    # await pyro_app.send_message("itolstov", "Greetings from **SkyNet**!")


async def get_group_members(chat_id: int) -> List[GroupMember]:
    members = []
    try:
        async for member in pyro_app.get_chat_members(chat_id):
            if member.user.is_deleted:
                continue
            is_admin = member.status in (ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR)
            members.append(GroupMember(
                user_id=member.user.id,
                username=member.user.username,
                full_name=member.user.first_name + (" " + member.user.last_name if member.user.last_name else ""),
                is_admin=is_admin
            ))
    except Exception as e:
        logger.error(f"Error getting group members: {e}")
        capture_exception(e)
    return members


async def main():
    await pyro_app.start()
    # await pyro_app.send_message("itolstov", "Greetings from **SkyNet**!")
    # a = await get_group_members(-1001892843127)
    # # 1798357244
    # print(a)
    from utils.global_data import global_data
    await global_data.mongo_config.update_chat_info(-1001892843127, await get_group_members(-1001892843127))

    try:
        await pyro_app.stop()
    except Exception as e:
        pass


if __name__ == "__main__":
    asyncio.run(main())
