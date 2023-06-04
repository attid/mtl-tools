import asyncio
import copy

import requests
from aiogram import types
from aiogram.types import ContentType
from aiogram.utils.callback_data import CallbackData
from loguru import logger

import mystellar
from skynet_main import dp, is_skynet_admin, bot
import json

# from aiogram.utils.markdown import bold, code, italic, text, link

# https://docs.aiogram.dev/en/latest/quick_start.html
# https://surik00.gitbooks.io/aiogram-lessons/content/chapter3.html
from mystellar import address_id_to_username
from mystellar import cmd_gen_mtl_vote_list

cb_poll_click = CallbackData("join_chat", "answer")
cb_sp_click = CallbackData("sp", "answer")

# we have dict with votes for different chats

chat_to_address = {-1001649743884: mystellar.public_issuer,
                   -1001837984392: mystellar.public_issuer,
                   -1001800264199: mystellar.public_usdm}


@dp.channel_post_handler(content_types=ContentType.all())
async def channel_post(message: types.Message):
    # logger.info(f'save {message.text}')
    if message.chat.id in (-1001649743884, -1001837984392):
        if message.poll:
            buttons = []
            my_buttons = []
            my_poll = {}
            for option in message.poll.options:
                my_buttons.append([option.text, 0, []])
                buttons.append(types.InlineKeyboardButton(option.text + '(0)',
                                                          callback_data=cb_poll_click.new(answer=len(buttons))))
            # print(my_buttons)
            msg = await message.answer(message.poll.question,
                                       reply_markup=types.InlineKeyboardMarkup(row_width=1).add(*buttons))
            my_poll["question"] = message.poll.question
            my_poll["closed"] = False
            my_poll['message_id'] = msg.message_id
            my_poll['buttons'] = my_buttons
            with open(f"polls/{msg.message_id}{message.chat.id}.json", "w") as fp:
                json.dump(my_poll, fp)


@dp.message_handler(commands="test")
async def cmd_test(message: types.Message):
    if not await is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return False
    # https://t.me/c/1948478564/2
    buttons = []
    buttons.append(types.InlineKeyboardButton('Поддерживаю',
                                              callback_data=cb_sp_click.new(answer=len(buttons))))
    buttons.append(types.InlineKeyboardButton('Воздерживаюсь',
                                              callback_data=cb_sp_click.new(answer=len(buttons))))
    buttons.append(types.InlineKeyboardButton('Против',
                                              callback_data=cb_sp_click.new(answer=len(buttons))))
    buttons.append(types.InlineKeyboardButton('Узнать результат',
                                              callback_data=cb_sp_click.new(answer=len(buttons))))
    # https://t.me/c/1863399780/16
    m = await bot.edit_message_reply_markup(-1001863399780, 16,
                                            reply_markup=None)
    await message.reply("test")
    await message.reply(str(m))


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
        if message.reply_to_message.forward_from_chat and message.reply_to_message.forward_from_message_id:
            file_name = f"polls/{message.reply_to_message.forward_from_message_id}{message.reply_to_message.forward_from_chat.id}.json"
        else:
            file_name = f"polls/{message.reply_to_message.message_id}{message.chat.id}.json"

        with open(file_name, "r") as fp:
            my_poll = json.load(fp)

        if my_poll["closed"]:
            await message.reply("This poll is closed!")
        else:
            my_poll["closed"] = True

            with open(file_name, "w") as fp:
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
        await message.reply_to_message.reply(' '.join(keys) + '\nСмотрите голосование \ Look at the poll')
        # await dp.bot.send_message(message.chat.id, ' '.join(keys) + '\nСмотрите закреп \ Look at the pinned message',
        #                          reply_to_message_id=message.reply_to_message, message_thread_id=)
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
        local_votes = votes[chat_to_address[query.message.chat.id]]
        if user in local_votes:
            if user in my_poll["buttons"][answer][2]:
                my_poll["buttons"][answer][1] -= local_votes[user]
                my_poll["buttons"][answer][2].remove(user)
            else:
                my_poll["buttons"][answer][1] += local_votes[user]
                my_poll["buttons"][answer][2].append(user)
            msg = my_poll["question"] + "\n\n"
            buttons = []
            for idx, button in enumerate(my_poll["buttons"]):
                msg += f"{button[0][:3]} ({button[1]}) : {' '.join(button[2])}\n"
                buttons.append(types.InlineKeyboardButton(button[0] + f"({button[1]})",
                                                          callback_data=cb_poll_click.new(answer=len(buttons))))
            msg += f'Need {local_votes["NEED"]["50"]}({local_votes["NEED"]["75"]}) votes from {local_votes["NEED"]["100"]}'

            await query.message.edit_text(msg, reply_markup=types.InlineKeyboardMarkup(row_width=1).add(*buttons))
            with open(f"polls/{query.message.message_id}{query.message.chat.id}.json", "w") as fp:
                json.dump(my_poll, fp)
        else:
            await query.answer("You are't in list!", show_alert=True)
        # await query.message.edit_text(answer, reply_markup=query.message.reply_markup)
        # await query.answer(_("This message is not for you!"), show_alert=True)
    return True


async def cmd_save_votes():
    vote_list = {}
    for chat_id in chat_to_address:
        if chat_to_address[chat_id] in vote_list:
            pass
        else:
            total = 0
            vote_list[chat_to_address[chat_id]] = {}
            _, signers = await mystellar.get_balances(address=chat_to_address[chat_id], return_signers=True)
            for signer in signers:
                if signer['weight'] > 0:
                    total += signer['weight']
                    vote_list[chat_to_address[chat_id]][address_id_to_username(signer['key'])] = signer['weight']
            vote_list[chat_to_address[chat_id]]['NEED'] = {'50': total // 2 + 1, '75': total // 3 * 2 + 1,
                                                           '100': total}
            # print(votes)
            with open("polls/votes.json", "w") as fp:
                json.dump(vote_list, fp)
            global votes
            votes = vote_list
    return votes


@dp.message_handler(commands="poll_reload_vote")
async def cmd_poll_reload_vote(message: types.Message):
    if not await is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return False

    await cmd_save_votes()
    # importlib.reload(skynet_poll_handlers)
    await message.reply('reload complete')


def cmd_load_votes():
    with open("polls/votes.json", "r") as fp:
        return json.load(fp)


votes = cmd_load_votes()

if __name__ == "__main__":
    pass
    a = asyncio.run(cmd_save_votes())
    print(a)
