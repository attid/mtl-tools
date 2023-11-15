import copy
import json
from contextlib import suppress
from typing import List

from aiogram import Router, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, PollAnswer
from sqlalchemy.orm import Session
from db.requests import db_save_bot_value, db_load_bot_value
from utils.global_data import MTLChats, BotValueTypes, is_skynet_admin, global_data
from utils.gspread_tools import gs_update_namelist, gs_copy_a_table, gs_find_user_a, gs_update_a_table_vote, \
    gs_update_a_table_first
from utils.stellar_utils import MTLAddresses, get_balances, address_id_to_username, get_mtlap_votes

router = Router()


class PollCallbackData(CallbackData, prefix="poll"):
    answer: int


empty_poll = '{"closed": true, "question": "", "options": []}'

# we have dict with votes for different chats
chat_to_address = {-1001649743884: MTLAddresses.public_issuer,
                   -1001837984392: MTLAddresses.public_issuer,
                   MTLChats.TestGroup: MTLAddresses.public_issuer,
                   MTLChats.USDMMGroup: MTLAddresses.public_usdm}


@router.channel_post()
async def channel_post(message: Message, session: Session):
    if message.chat.id in (-1001649743884, -1001837984392):
        if message.poll:
            buttons = []
            my_buttons = []
            my_poll = {}
            for option in message.poll.options:
                my_buttons.append([option.text, 0, []])
                buttons.append([InlineKeyboardButton(text=option.text + '(0)',
                                                     callback_data=PollCallbackData(answer=len(buttons)).pack())])
            msg = await message.answer(message.poll.question,
                                       reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
            my_poll["question"] = message.poll.question
            my_poll["closed"] = False
            my_poll['message_id'] = msg.message_id
            my_poll['buttons'] = my_buttons
            db_save_bot_value(session, message.chat.id, -1 * msg.message_id, json.dumps(my_poll))


@router.message(Command(commands=["poll"]))
async def cmd_poll(message: Message, session: Session):
    if message.reply_to_message and message.reply_to_message.poll:
        poll = message.reply_to_message.poll
        buttons = []
        my_buttons = []
        my_poll = {}
        for option in poll.options:
            my_buttons.append([option.text, 0, []])
            buttons.append([InlineKeyboardButton(text=option.text + '(0)',
                                                 callback_data=PollCallbackData(answer=len(buttons)).pack())])
        # print(my_buttons)
        msg = await message.answer(poll.question, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        my_poll["question"] = poll.question
        my_poll["closed"] = False
        my_poll['message_id'] = msg.message_id
        my_poll['buttons'] = my_buttons
        db_save_bot_value(session, message.chat.id, -1 * msg.message_id, json.dumps(my_poll))
    else:
        await message.answer('Требуется в ответ на голосование')


@router.message(Command(commands=["poll_replace_text"]))
async def cmd_poll_rt(message: Message, session: Session):
    # print(message)
    if message.reply_to_message:
        my_poll = json.loads(
            db_load_bot_value(session, message.chat.id, -1 * message.reply_to_message.message_id, empty_poll))

        if my_poll["closed"]:
            await message.reply("This poll is closed!")
        else:
            my_poll["question"] = message.text[len('/poll_replace_text '):]

            db_save_bot_value(session, message.chat.id, -1 * message.reply_to_message.message_id, json.dumps(my_poll))
    else:
        await message.answer('Требуется в ответ на голосование')


@router.message(Command(commands=["poll_close"]))
@router.message(Command(commands=["poll_stop"]))
async def cmd_poll_close(message: Message, session: Session):
    # print(message)
    if message.reply_to_message:
        if message.reply_to_message.forward_from_chat and message.reply_to_message.forward_from_message_id:
            message_id = message.reply_to_message.forward_from_message_id
        else:
            message_id = message.reply_to_message.message_id

        my_poll = json.loads(db_load_bot_value(session, message.chat.id, -1 * message_id, empty_poll))

        if my_poll["closed"]:
            await message.reply("This poll is closed!")
        else:
            my_poll["closed"] = True

            db_save_bot_value(session, message.chat.id, -1 * message_id, json.dumps(my_poll))
    else:
        await message.answer('Требуется в ответ на голосование')


@router.message(Command(commands=["poll_check"]))
async def cmd_poll_check(message: Message, session: Session):
    if message.reply_to_message:
        my_poll = json.loads(
            db_load_bot_value(session, message.chat.id, -1 * message.reply_to_message.message_id, empty_poll))
        votes_check = copy.deepcopy(global_data.votes)
        for button in my_poll["buttons"]:
            for vote in button[2]:
                if vote in votes_check:
                    votes_check.pop(vote)
        votes_check.pop("NEED")
        keys = votes_check.keys()
        await message.reply_to_message.reply(' '.join(keys) + '\nСмотрите голосование \ Look at the poll')
    else:
        await message.answer('Требуется в ответ на голосование')


@router.callback_query(PollCallbackData.filter())
async def cq_join_list(query: CallbackQuery, callback_data: PollCallbackData, session: Session):
    answer = callback_data.answer
    user = '@' + query.from_user.username.lower() if query.from_user.username else query.from_user.id
    my_poll = json.loads(
        db_load_bot_value(session, query.message.chat.id, -1 * query.message.message_id, empty_poll))

    if my_poll["closed"]:
        await query.answer("This poll is closed!", show_alert=True)
    else:
        # {'question': '????? ????? ??? ???????? ?', 'closed': False, 'message_id': 80, 'buttons': [['??????', 0, []],
        # ['??????', 0, []], ['??????', 0, []]]}
        local_votes = global_data.votes[chat_to_address[query.message.chat.id]]
        need_close = False
        if user in local_votes:
            if user in my_poll["buttons"][answer][2]:
                my_poll["buttons"][answer][1] -= local_votes[user]
                my_poll["buttons"][answer][2].remove(user)
            else:
                my_poll["buttons"][answer][1] += local_votes[user]
                my_poll["buttons"][answer][2].append(user)
                if my_poll["buttons"][answer][1] >= local_votes["NEED"]["75"]:
                    need_close = True
            msg = my_poll["question"] + "\n\n"
            buttons = []
            for idx, button in enumerate(my_poll["buttons"]):
                msg += f"{button[0][:3]} ({button[1]}) : {' '.join(button[2])}\n"
                buttons.append([InlineKeyboardButton(text=button[0] + f"({button[1]})",
                                                     callback_data=PollCallbackData(answer=len(buttons)).pack())])
            msg += f'Need {local_votes["NEED"]["50"]}({local_votes["NEED"]["75"]}) votes from {local_votes["NEED"]["100"]}'

            await query.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
            if need_close:
                my_poll["closed"] = True
            db_save_bot_value(session, query.message.chat.id, -1 * query.message.message_id, json.dumps(my_poll))
        else:
            await query.answer("You are't in list!", show_alert=True)
    return True


async def cmd_save_votes(session: Session):
    await gs_update_namelist()
    vote_list = {}
    for chat_id in chat_to_address:
        if chat_to_address[chat_id] in vote_list:
            pass
        else:
            total = 0
            vote_list[chat_to_address[chat_id]] = {}
            _, signers = await get_balances(address=chat_to_address[chat_id], return_signers=True)
            for signer in signers:
                if signer['weight'] > 0:
                    total += signer['weight']
                    vote_list[chat_to_address[chat_id]][address_id_to_username(signer['key'], full_data=True).lower()] = \
                        signer['weight']
            vote_list[chat_to_address[chat_id]]['NEED'] = {'50': total // 2 + 1, '75': total // 3 * 2 + 1,
                                                           '100': total}
    db_save_bot_value(session, 0, BotValueTypes.Votes, json.dumps(vote_list))
    global_data.votes = vote_list
    return vote_list


@router.message(Command(commands=["poll_reload_vote"]))
async def cmd_poll_reload_vote(message: Message, session: Session):
    if not is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return False

    await cmd_save_votes(session)
    # importlib.reload(skynet_poll_handlers)
    await message.reply('reload complete')


@router.message(Command(commands=["apoll"]))
async def cmd_apoll(message: Message, session: Session):
    if message.reply_to_message and message.reply_to_message.poll:
        my_poll = {}
        google_url, google_id = await gs_copy_a_table(message.reply_to_message.poll.question)
        options = []
        options.extend([option.text for option in message.reply_to_message.poll.options])

        await gs_update_a_table_first(google_id, message.reply_to_message.poll.question, options,
                                      (await get_mtlap_votes()))

        msg = await message.answer_poll(question=message.reply_to_message.poll.question,
                                        options=options,
                                        allows_multiple_answers=message.reply_to_message.poll.allows_multiple_answers,
                                        is_anonymous=message.reply_to_message.poll.is_anonymous)
        msg2 = await msg.reply(f'url {google_url}\nData will be here soon', disable_web_page_preview=True)
        my_poll["poll_id"] = msg.poll.id
        my_poll["info_chat_id"] = msg2.chat.id
        my_poll["info_message_id"] = msg2.message_id
        my_poll["google_id"] = google_id
        my_poll["google_url"] = google_url
        db_save_bot_value(session, -1, int(msg.poll.id), json.dumps(my_poll))
        await message.reply_to_message.delete()
        await message.delete()
    else:
        await message.answer('Требуется в ответ на голосование')


# @router.poll()
# async def cmd_test(message: Message):
#    print(1, message)
#    #1 id='5341722582053815395' question='test' options=[PollOption(text='a', voter_count=1), PollOption(text='b', voter_count=1), PollOption(text='c', voter_count=2)] total_voter_count=4 is_closed=False is_anonymous=False type='regular' allows_multiple_answers=False correct_option_id=None explanation=None explanation_entities=None open_period=None close_date=None


@router.poll_answer()
async def cmd_poll_answer(poll: PollAnswer, session: Session, bot: Bot):
    # print(2, poll)
    # 2 poll_id='5341722582053815395' option_ids=[1] voter_chat=None user=User(id=84131737, is_bot=False, first_name='Igor', last_name='Tolstov', username='itolstov', language_code='ru', is_premium=True, added_to_attachment_menu=None, can_join_groups=None, can_read_all_group_messages=None, supports_inline_queries=None)
    # -1 id='5341722582053815395' question='test' options=[PollOption(text='a', voter_count=1), PollOption(text='b', voter_count=0), PollOption(text='c', voter_count=2)] total_voter_count=3 is_closed=False is_anonymous=False type='regular' allows_multiple_answers=False correct_option_id=None explanation=None explanation_entities=None open_period=None close_date=None
    # -2 poll_id='5341722582053815395' option_ids=[] voter_chat=None user=User(id=84131737, is_bot=False, first_name='Igor', last_name='Tolstov', username='itolstov', language_code='ru', is_premium=True, added_to_attachment_menu=None, can_join_groups=None, can_read_all_group_messages=None, supports_inline_queries=None)
    my_poll = json.loads(db_load_bot_value(session, -1, int(poll.poll_id), empty_poll))
    # find user
    user_address = await gs_find_user_a(f'@{poll.user.username}')
    if not user_address:
        await bot.send_message(my_poll["info_chat_id"], f'User @{poll.user.username} not found')
        return

    # update answer
    # gs_update_a_table_vote(table_uuid, address, options):
    result = await gs_update_a_table_vote(my_poll["google_id"], user_address, poll.option_ids)
    msg_text = f'<a href="{my_poll["google_url"]}">GoogleSheets</a>\n'
    if result:
        for data in result:
            msg_text += f'{data[0]}: {data[1]}\n'

        with suppress(TelegramBadRequest):
            await bot.edit_message_text(chat_id=my_poll["info_chat_id"], message_id=my_poll["info_message_id"],
                                        text=msg_text, disable_web_page_preview=True)


if __name__ == "__main__":
    pass
    # a = asyncio.run(cmd_save_votes(None))
    # print(a)
