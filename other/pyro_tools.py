import asyncio
import html
import os
import re
from dataclasses import dataclass
from typing import Optional, List

from loguru import logger
from pyrogram import Client  # kurigram
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import FloodWait, PeerIdInvalid, UserNotMutualContact
from sentry_sdk import capture_exception

from other.config_reader import config, start_path


# https://docs.kurigram.icu/intro/quickstart/


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
    is_bot: bool = False


# if 'test' in sys.argv or __name__ == "__main__":
#     session_name = "test_session"
# else:
#     session_name = "pyro_session"
#pyro_app = Client(session_name, api_id=config.pyro_api_id, api_hash=config.pyro_api_hash.get_secret_value(),
#                  workdir=os.path.join(start_path, 'data'))

_pyro_app: Optional[Client] = None


def get_pyro_app() -> Client:
    global _pyro_app
    if _pyro_app is None:
        _pyro_app = Client(
            name="my_bot",
            bot_token=config.bot_token.get_secret_value(),
            api_id=config.pyro_api_id,
            api_hash=config.pyro_api_hash.get_secret_value(),
            workdir=os.path.join(start_path, 'data'),
            no_updates=True,
        )
    return _pyro_app



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
    # await pyro_app.send_message("itolstov", "Greetings from **Kurigram**!")
    # from_user can be None for channel/anonymous messages; fall back to sender_chat.
    def _get_sender_name(message) -> str:
        if message.from_user:
            if message.from_user.username:
                return message.from_user.username
            return html.escape(message.from_user.full_name)
        if getattr(message, "sender_chat", None):
            if message.sender_chat.username:
                return message.sender_chat.username
            return html.escape(message.sender_chat.title or "")
        return ""

    pyro_app = get_pyro_app()
    message = await pyro_app.get_messages(chat_id=msg.chat_id, message_ids=msg.message_id)
    if message.chat.username:
        msg.chat_name = f"{message.chat.username} ({msg.chat_name})"
    else:
        msg.chat_name = message.chat.title

    msg.user_from = _get_sender_name(message)

    if message.topic:
        msg.thread_id = message.topic.id
        msg.thread_name = message.topic.title

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
                user_from=_get_sender_name(message.reply_to_message),
            )

    if message.text:
        msg.message_text = message.text.html
    elif message.caption:
        msg.message_text = message.caption.html


async def pyro_start():
    try:
        if config.pyro_api_id == 0:
            logger.warning("pyro_api_id is disabled")
            return
        await get_pyro_app().start()
    except Exception as e:
        logger.error(e)
        capture_exception(e)
    # await pyro_app.send_message("itolstov", "Greetings from **SkyNet**!")


async def pyro_test():
    await get_pyro_app().send_message("@itolstov", "Greetings from **SkyNet**!")

async def get_group_members(chat_id: int) -> List[GroupMember]:
    pyro_app = get_pyro_app()
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
                is_admin=is_admin,
                is_bot=member.user.is_bot
            ))
    except Exception as e:
        logger.error(f"Error getting group members: {e}")
        capture_exception(e)
    return members


async def remove_deleted_users(chat_id: int):
    pyro_app = get_pyro_app()
    try:
        total_removals = 0
        async for member in pyro_app.get_chat_members(chat_id):
            if member.user.is_deleted:
                try:
                    await pyro_app.ban_chat_member(chat_id, member.user.id)
                    logger.info(f"Removed deleted user with ID {member.user.id} from chat {chat_id}")
                    total_removals += 1
                    await asyncio.sleep(3)
                except FloodWait as e:
                    logger.warning(f"FloodWait error: waiting for {e.value} seconds")
                    await asyncio.sleep(e.value)
                except Exception as e:
                    logger.error(f"Error removing user {member.user.id}: {e}")
                    capture_exception(e)
        return total_removals
    except Exception as e:
        logger.error(f"Error in remove_deleted_users for chat {chat_id}: {e}")
        capture_exception(e)

async def add_contact(user_id: int):
    pyro_app = get_pyro_app()
    try:
        # Get user info
        user = await pyro_app.get_users(user_id)
        if not user:
            logger.error(f"User {user_id} not found")
            return False

        # Add contact
        result = await pyro_app.add_contact(
            user_id=user.id,
            first_name=user.first_name or "",
            last_name=user.last_name or "",
            phone_number=user.phone_number or ""
        )
        if result:
            logger.info(f"Successfully added user {user_id} to contacts")
            return True
        else:
            logger.warning(f"Failed to add user {user_id} to contacts")
            return False
    except PeerIdInvalid:
        logger.error(f"Invalid user ID: {user_id}")
        return False
    except UserNotMutualContact:
        logger.warning(f"User {user_id} is not a mutual contact")
        return False
    except FloodWait as e:
        logger.warning(f"FloodWait error: waiting for {e.value} seconds")
        await asyncio.sleep(e.value)
        return await add_contact(user_id)  # Retry after waiting
    except Exception as e:
        logger.error(f"Error adding user {user_id} to contacts: {e}")
        capture_exception(e)
        return False


async def common_chats(user_id: int|str):
    pyro_app = get_pyro_app()
    try:
        chats = await pyro_app.get_common_chats(user_id=user_id)
        print(chats)
    except Exception as e:
        logger.error(f"Error for chat {user_id}: {e}")
        capture_exception(e)

async def main():
    pyro_app = get_pyro_app()
    await pyro_app.start()
    a = await pyro_test()
    print(a)

    # await remove_deleted_users(-1002032873651)
    # await pyro_app.send_message("itolstov", "Greetings from **SkyNet**!")

    a = await get_group_members(-1001269297637)
    for member in a:
        print(f"{member.user_id}\t{member.full_name}\t{member.username or ''}")


    # from app_context import app_context
    # await app_context.mongo_config.update_chat_info(-1001892843127, await get_group_members(-1001892843127))
    # url = "https://t.me/c/1798357244/90095/95343"
    # msg_info = extract_telegram_info(url)
    # await pyro_update_msg_info(msg_info)
    # print(msg_info)


    try:
        await pyro_app.stop()
    except Exception:
        pass


if __name__ == "__main__":
    asyncio.run(main())
