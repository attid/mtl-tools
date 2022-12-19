import copy

import requests
from aiogram import types
from aiogram.utils.callback_data import CallbackData
from skynet_main import dp
import json

# from aiogram.utils.markdown import bold, code, italic, text, link

# https://docs.aiogram.dev/en/latest/quick_start.html
# https://surik00.gitbooks.io/aiogram-lessons/content/chapter3.html
from mystellar import address_id_to_username
from mystellar import cmd_gen_vote_list

cb_poll_click = CallbackData("join_chat", "answer")


@dp.message_handler(commands="test")
async def cmd_test(message: types.Message):
    print(message)
    await message.reply("test")


@dp.message_handler(commands="poll2")
async def cmd_save(message: types.Message):
    print(message)
    # logger.info(f'save {message.text}')
    await dp.bot.send_poll(message.chat.id, message.reply_to_message.poll.question,
                           ['1', '2', '3'], False)


@dp.message_handler(commands="poll")
async def cmd_poll(message: types.Message):
    # print(message)
    if message.reply_to_message and message.reply_to_message.poll:
        poll = message.reply_to_message.poll
        buttons = []
        my_buttons = []
        my_poll = {}
        for option in poll.options:
            my_buttons.append([option.text, 0, []])
            buttons.append(types.InlineKeyboardButton(option.text + '(0)',
                                                      callback_data=cb_poll_click.new(answer=len(buttons))))
        # print(my_buttons)
        msg = await message.answer(poll.question, reply_markup=types.InlineKeyboardMarkup(row_width=1).add(*buttons))
        my_poll["question"] = poll.question
        my_poll["closed"] = False
        my_poll['message_id'] = msg.message_id
        my_poll['buttons'] = my_buttons
        with open(f"polls/{msg.message_id}{message.chat.id}.json", "w") as fp:
            json.dump(my_poll, fp)

    else:
        await message.answer('Требуется в ответ на голосование')


@dp.message_handler(commands="poll_replace_text")
async def cmd_poll_rt(message: types.Message):
    # print(message)
    if message.reply_to_message:
        with open(f"polls/{message.reply_to_message.message_id}{message.chat.id}.json", "r") as fp:
            my_poll = json.load(fp)

        if my_poll["closed"]:
            await message.reply("This poll is closed!")
        else:
            my_poll["question"] = message.get_args()

            with open(f"polls/{message.reply_to_message.message_id}{message.chat.id}.json", "w") as fp:
                json.dump(my_poll, fp)
    else:
        await message.answer('Требуется в ответ на голосование')


@dp.message_handler(commands="poll_close")
@dp.message_handler(commands="poll_stop")
async def cmd_poll_close(message: types.Message):
    # print(message)
    if message.reply_to_message:
        with open(f"polls/{message.reply_to_message.message_id}{message.chat.id}.json", "r") as fp:
            my_poll = json.load(fp)

        if my_poll["closed"]:
            await message.reply("This poll is closed!")
        else:
            my_poll["closed"] = True

            with open(f"polls/{message.reply_to_message.message_id}{message.chat.id}.json", "w") as fp:
                json.dump(my_poll, fp)
    else:
        await message.answer('Требуется в ответ на голосование')


@dp.message_handler(commands="poll_check")
async def cmd_poll_check(message: types.Message):
    # print(message)
    if message.reply_to_message:
        with open(f"polls/{message.reply_to_message.message_id}{message.chat.id}.json", "r") as fp:
            my_poll = json.load(fp)
        votes_check = copy.deepcopy(votes)
        for button in my_poll["buttons"]:
            for vote in button[2]:
                if vote in votes_check:
                    votes_check.pop(vote)
        votes_check.pop("NEED")
        keys = votes_check.keys()
        await dp.bot.send_message(message.chat.id, ' '.join(keys) + '\nСмотрите закреп \ Look at the pinned message',
                                  reply_to_message_id=message.reply_to_message)
    else:
        await message.answer('Требуется в ответ на голосование')


@dp.callback_query_handler(cb_poll_click.filter())
async def cq_join_list(query: types.CallbackQuery, callback_data: dict):
    answer = int(callback_data["answer"])
    user = '@' + query.from_user.username
    with open(f"polls/{query.message.message_id}{query.message.chat.id}.json", "r") as fp:
        my_poll = json.load(fp)

    if my_poll["closed"]:
        await query.answer("This poll is closed!", show_alert=True)
    else:
        # {'question': '????? ????? ??? ???????? ?', 'closed': False, 'message_id': 80, 'buttons': [['??????', 0, []],
        # ['??????', 0, []], ['??????', 0, []]]}
        if user in votes:
            if user in my_poll["buttons"][answer][2]:
                my_poll["buttons"][answer][1] -= votes[user]
                my_poll["buttons"][answer][2].remove(user)
            else:
                my_poll["buttons"][answer][1] += votes[user]
                my_poll["buttons"][answer][2].append(user)
            msg = my_poll["question"] + "\n\n"
            buttons = []
            for idx, button in enumerate(my_poll["buttons"]):
                msg += f"{button[0][:3]} ({button[1]}) : {' '.join(button[2])}\n"
                buttons.append(types.InlineKeyboardButton(button[0] + f"({button[1]})",
                                                          callback_data=cb_poll_click.new(answer=len(buttons))))
            msg += f'Need {votes["NEED"]["50"]}({votes["NEED"]["75"]}) votes from {votes["NEED"]["100"]}'

            await query.message.edit_text(msg, reply_markup=types.InlineKeyboardMarkup(row_width=1).add(*buttons))
            with open(f"polls/{query.message.message_id}{query.message.chat.id}.json", "w") as fp:
                json.dump(my_poll, fp)
        else:
            await query.answer("You are't in list!", show_alert=True)
        # await query.message.edit_text(answer, reply_markup=query.message.reply_markup)
        # await query.answer(_("This message is not for you!"), show_alert=True)
    return True


def cmd_save_votes():
    total = 0
    vote_list = cmd_gen_vote_list()
    for vote in vote_list:
        if vote[2] == 0:
            vote_list.remove(vote)
    while len(vote_list) > 20:
        vote_list.pop(20)
    votes_list = {}
    for vote in vote_list:
        votes_list[address_id_to_username(vote[0])] = vote[2]
        total += vote[2]
    votes_list['NEED'] = {'50': cmd_get_needed_votes(), '75': total // 3 * 2 + 1, '100': total}
    # print(votes)
    with open("polls/votes.json", "w") as fp:
        json.dump(votes_list, fp)
    return votes_list


def cmd_get_needed_votes():
    rq = requests.get(
        'https://horizon.stellar.org/accounts/GDX23CPGMQ4LN55VGEDVFZPAJMAUEHSHAMJ2GMCU2ZSHN5QF4TMZYPIS').json()
    return int(rq["thresholds"]["med_threshold"])


with open("polls/votes.json", "r") as fp:
    votes = json.load(fp)

if __name__ == "__main__":
    pass
    a = cmd_save_votes()
    print(a)
