import copy
import json

import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.orm import Session
from db.requests import cmd_save_bot_value, cmd_load_bot_value
from utils.global_data import MTLChats, BotValueTypes, is_skynet_admin, global_data
from utils.stellar_utils import MTLAddresses, get_balances, address_id_to_username

router = Router()


class PollCallbackData(CallbackData, prefix="poll"):
    answer: int

empty_poll = '{"closed": true, "question": "", "options": []}'

# we have dict with votes for different chats
chat_to_address = {-1001649743884: MTLAddresses.public_issuer,
                   -1001837984392: MTLAddresses.public_issuer,
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
                                       reply_markup=InlineKeyboardMarkup(inline_keyboard=my_buttons))
            my_poll["question"] = message.poll.question
            my_poll["closed"] = False
            my_poll['message_id'] = msg.message_id
            my_poll['buttons'] = my_buttons
            cmd_save_bot_value(session, message.chat.id, -1 * msg.message_id, json.dumps(my_poll))


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
        msg = await message.answer(poll.question, reply_markup=InlineKeyboardMarkup(inline_keyboard=my_buttons))
        my_poll["question"] = poll.question
        my_poll["closed"] = False
        my_poll['message_id'] = msg.message_id
        my_poll['buttons'] = my_buttons
        cmd_save_bot_value(session, message.chat.id, -1 * msg.message_id, json.dumps(my_poll))
    else:
        await message.answer('Требуется в ответ на голосование')


@router.message(Command(commands=["poll_replace_text"]))
async def cmd_poll_rt(message: Message, session: Session):
    # print(message)
    if message.reply_to_message:
        my_poll = json.loads(cmd_load_bot_value(session, message.chat.id, -1*message.reply_to_message.message_id, empty_poll))

        if my_poll["closed"]:
            await message.reply("This poll is closed!")
        else:
            my_poll["question"] = message.text[len('/poll_replace_text '):]

            cmd_save_bot_value(session, message.chat.id, -1 * message.reply_to_message.message_id, json.dumps(my_poll))
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

        my_poll = json.loads(cmd_load_bot_value(session, message.chat.id, -1* message_id, empty_poll))

        if my_poll["closed"]:
            await message.reply("This poll is closed!")
        else:
            my_poll["closed"] = True

            cmd_save_bot_value(session, message.chat.id, -1 * message_id, json.dumps(my_poll))
    else:
        await message.answer('Требуется в ответ на голосование')


@router.message(Command(commands=["poll_check"]))
async def cmd_poll_check(message: Message, session: Session):
    if message.reply_to_message:
        my_poll = json.loads(cmd_load_bot_value(session, message.chat.id, -1 * message.reply_to_message.message_id, empty_poll))
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
    user = '@' + query.from_user.username
    my_poll = json.loads(
        cmd_load_bot_value(session, query.message.chat.id, -1 * query.message.message_id, empty_poll))

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
            cmd_save_bot_value(session, query.message.message_id, -1 * msg.message_id, json.dumps(my_poll))
        else:
            await query.answer("You are't in list!", show_alert=True)
    return True


async def cmd_save_votes(session: Session):
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
                    vote_list[chat_to_address[chat_id]][address_id_to_username(signer['key'])] = signer['weight']
            vote_list[chat_to_address[chat_id]]['NEED'] = {'50': total // 2 + 1, '75': total // 3 * 2 + 1,
                                                           '100': total}
    cmd_save_bot_value(session, 0, BotValueTypes.Votes, json.dumps(vote_list))
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


if __name__ == "__main__":
    pass
    #a = asyncio.run(cmd_save_votes(None))
    #print(a)
