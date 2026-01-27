# other/stellar/utils.py
"""General utility functions for Stellar operations."""

import re

import requests
from aiogram import Bot
from aiogram.types import Message
from loguru import logger
from sqlalchemy.orm import Session

from db.repositories import ChatsRepository


def cleanhtml(raw_html: str) -> str:
    """
    Remove HTML tags and normalize whitespace.

    Args:
        raw_html: String containing HTML

    Returns:
        Clean text without HTML tags
    """
    clean_regex = re.compile('<.*?>')
    cleantext = re.sub(clean_regex, '', raw_html)
    while cleantext.find("\n") > -1:
        cleantext = cleantext.replace("\n", " ")
    while cleantext.find("  ") > -1:
        cleantext = cleantext.replace("  ", " ")
    return cleantext


def cmd_alarm_url(url: str) -> str:
    """
    Parse alarm content from web page.

    Extracts the list of users who haven't signed a transaction
    from the eurmtl.me multi-signature page.

    Args:
        url: URL to the transaction page

    Returns:
        String with users who need to sign or message if already published
    """
    rq = requests.get(url).text
    if rq.find('<h4 class="published">') > -1:
        return 'Нечего напоминать, транзакция отправлена.'
    rq = rq[rq.find('<div class="col-10 ignorants-nicks">'):]
    rq = rq[rq.find('">') + 2:]
    rq = rq[:rq.find('</div>')]
    rq = rq.replace("&#x3D;", "=")
    return cleanhtml(rq)


async def send_by_list(
    bot: Bot,
    all_users: list,
    message: Message,
    session: Session = None,
    url: str = None
):
    """
    Send messages to multiple users.

    Args:
        bot: Telegram bot instance
        all_users: List of usernames to notify (e.g., ['@user1', '@user2'])
        message: Original message with reply context
        session: Database session for looking up user IDs
        url: Optional URL to include (uses reply message URL if not provided)
    """
    good_users = []
    bad_users = []
    if url is None:
        url = message.reply_to_message.get_url()
    msg = f'@{message.from_user.username} call you here {url}'

    for user in all_users:
        if len(user) > 2 and user[0] == '@':
            try:
                chat_id = ChatsRepository(session).get_user_id(user)
                await bot.send_message(chat_id=chat_id, text=msg)
                good_users.append(user)
            except Exception as ex:
                bad_users.append(user)
                logger.info(ex)
                pass

    await message.reply(f'was send to {" ".join(good_users)} \n can`t send to {" ".join(bad_users)}')
