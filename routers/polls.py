import json
import math
from contextlib import suppress

from aiogram import Router, Bot, F
from loguru import logger
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, PollAnswer, \
    ReactionTypeEmoji
from sqlalchemy.orm import Session

from other.global_data import MTLChats, BotValueTypes, is_skynet_admin, global_data, update_command_info
from other.grist_tools import grist_manager, MTLGrist
from other.gspread_tools import (gs_copy_a_table, gs_update_a_table_vote,
                                 gs_update_a_table_first, gs_check_vote_table)
from other.stellar_tools import MTLAddresses, get_balances, address_id_to_username, get_mtlap_votes

router = Router()


class PollCallbackData(CallbackData, prefix="poll"):
    answer: int


empty_poll = '{"closed": true, "question": "", "options": []}'

# we have dict with votes for different chats
chat_to_address = {-1001649743884: MTLAddresses.public_issuer,
                   -1001837984392: MTLAddresses.public_issuer,
                   MTLChats.TestGroup: MTLAddresses.public_issuer,
                   MTLChats.USDMMGroup: MTLAddresses.public_usdm,
                   -1002210483308: MTLAddresses.public_issuer,  # -1002210483308 тестовый канал
                   -1002042260878: MTLAddresses.public_mtla}


@router.channel_post(F.poll)
async def channel_post(message: Message, session: Session):
    if message.chat.id in (-1001649743884, -1001837984392, -1002042260878, -1002210483308):
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
            await global_data.mongo_config.save_bot_value(message.chat.id, -1 * msg.message_id, json.dumps(my_poll))


@update_command_info("/poll", "Создать голование с учетом веса голосов, "
                              "надо слать в ответ на стандартное голосование")
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
        await global_data.mongo_config.save_bot_value(message.chat.id, -1 * msg.message_id, json.dumps(my_poll))
    else:
        await message.answer('Требуется в ответ на голосование')


@update_command_info("/poll_replace_text",
                     "Заменить в спец голосовании текст на предлагаемый далее. "
                     "Использовать /poll_replace_text new_text")
@router.message(Command(commands=["poll_replace_text"]))
async def cmd_poll_rt(message: Message, session: Session):
    # print(message)
    if message.reply_to_message:
        my_poll = json.loads(
            await global_data.mongo_config.load_bot_value(message.chat.id, -1 * message.reply_to_message.message_id,
                                                          empty_poll))

        if my_poll["closed"]:
            await message.reply("This poll is closed!")
        else:
            my_poll["question"] = message.text[len('/poll_replace_text '):]

            await global_data.mongo_config.save_bot_value(message.chat.id, -1 * message.reply_to_message.message_id,
                                                          json.dumps(my_poll))
    else:
        await message.answer('Требуется в ответ на голосование')


@update_command_info("/poll_close", "Закрыть голосование. "
                                    "после этого нельзя голосовать или менять его.")
@router.message(Command(commands=["poll_close"]))
@router.message(Command(commands=["poll_stop"]))
@router.message(Command(commands=["apoll_stop"]))
async def cmd_poll_close(message: Message, session: Session, bot: Bot):
    if message.reply_to_message and message.reply_to_message.poll:
        await bot.stop_poll(message.chat.id, message.reply_to_message.message_id)
        return

    # print(message)
    if message.reply_to_message:
        if message.reply_to_message.forward_from_chat and message.reply_to_message.forward_from_message_id:
            message_id = message.reply_to_message.forward_from_message_id
        else:
            message_id = message.reply_to_message.message_id

        my_poll = json.loads(
            await global_data.mongo_config.load_bot_value(message.chat.id, -1 * message_id, empty_poll))

        if my_poll["closed"]:
            await message.reply("This poll is closed!")
        else:
            my_poll["closed"] = True

            await global_data.mongo_config.save_bot_value(message.chat.id, -1 * message_id, json.dumps(my_poll))
    else:
        await message.answer('Требуется в ответ на голосование')


@update_command_info("/poll_check",
                     "Проверить кто не голосовал. Слать в ответ на спец голосование. "
                     "'кто молчит', 'найди молчунов', 'найди безбилетника'")
@router.message(Command(commands=["poll_check"]))
async def cmd_poll_check(message: Message, session: Session):
    chat_id = message.chat.id
    message_id = None

    # Проверка, является ли сообщение ответом на другое сообщение
    if message.reply_to_message:
        message_id = -1 * message.reply_to_message.message_id
        if message.reply_to_message.forward_origin:
            chat_id = message.reply_to_message.forward_origin.chat.id
            message_id = -1 * message.reply_to_message.forward_origin.message_id

    if message_id:
        my_poll = json.loads(
            await global_data.mongo_config.load_bot_value(chat_id, message_id, empty_poll))

        # Получение ключа для votes_check из chat_to_address
        address_key = chat_to_address.get(chat_id)
        if address_key and address_key in global_data.votes:
            votes_detail = global_data.votes[address_key]

            # Извлечение всех уникальных пользователей из votes_detail
            all_voters = set(votes_detail.keys())
            all_voters.remove("NEED")

            # Проверка и удаление голосовавших пользователей из списка всех голосов
            for button in my_poll["buttons"]:
                for voter in button[2]:
                    voter = voter.strip("'")  # Удаление кавычек из имён пользователей, если они есть
                    if voter in all_voters:
                        all_voters.remove(voter)

            # Вывод оставшихся голосов
            remaining_voters = ' '.join(all_voters)
            await message.reply_to_message.reply(f'{remaining_voters}\nСмотрите голосование / Look at the poll')
        else:
            await message.reply_to_message.reply(
                'Данные голосования не найдены или ключ чата отсутствует в chat_to_address')
    else:
        await message.answer('Требуется в ответ на голосование или пересланное голосование из канала')


@router.callback_query(PollCallbackData.filter())
async def cq_join_list(query: CallbackQuery, callback_data: PollCallbackData, session: Session):
    answer = callback_data.answer
    user = '@' + query.from_user.username.lower() if query.from_user.username else query.from_user.id
    my_poll = json.loads(
        await global_data.mongo_config.load_bot_value(query.message.chat.id, -1 * query.message.message_id, empty_poll))

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
            await global_data.mongo_config.save_bot_value(query.message.chat.id, -1 * query.message.message_id,
                                                          json.dumps(my_poll))
        else:
            await query.answer("You are't in list!", show_alert=True)
    return True


async def cmd_save_votes(session: Session):
    #await gs_update_namelist()
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
                    key_ = (await address_id_to_username(signer['key'], full_data=True)).lower()
                    vote_list[chat_to_address[chat_id]][key_] = signer['weight']
            vote_list[chat_to_address[chat_id]]['NEED'] = {'50': total // 2 + 1,
                                                           '75': math.ceil(total * 0.75),
                                                           '100': total}

    await global_data.mongo_config.save_bot_value(0, BotValueTypes.Votes, json.dumps(vote_list))
    global_data.votes = vote_list
    return vote_list


@update_command_info("/poll_reload_vote", "Перечитать голоса из блокчейна")
@router.message(Command(commands=["poll_reload_vote"]))
async def cmd_poll_reload_vote(message: Message, session: Session):
    if not is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return False

    vote_list = await cmd_save_votes(session)
    entries_with_dots = []

    for key, value in vote_list.items():
        for sub_key in value.keys():
            if '..' in sub_key:
                entries_with_dots.append(sub_key.upper())

    if len(entries_with_dots) > 0:
        await message.reply(
            'Список пользователей не найденых в реестрах:\n' + '\n'.join(entries_with_dots))

    # importlib.reload(skynet_poll_handlers)
    await message.reply('reload complete')


@update_command_info('/apoll', 'Создает голосование в Ассоциации')
@router.message(Command(commands=["apoll"]))
async def cmd_apoll(message: Message, session: Session):
    if message.reply_to_message and message.reply_to_message.poll:
        await message.react([ReactionTypeEmoji(emoji="👾")])
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
        await global_data.mongo_config.save_bot_value(MTLChats.MTLA_Poll, int(msg.poll.id), json.dumps(my_poll))
        await message.reply_to_message.delete()
        await message.delete()
    else:
        await message.answer('Требуется в ответ на голосование')


@router.poll_answer()
async def cmd_poll_answer(poll: PollAnswer, session: Session, bot: Bot):
    my_poll = json.loads(
        await global_data.mongo_config.load_bot_value(MTLChats.MTLA_Poll, int(poll.poll_id), empty_poll))
    # find user
    user_address = await grist_manager.load_table_data(MTLGrist.MTLA_USERS, filter_dict={"TGID": [poll.user.id]})

    if not user_address:
        await bot.send_message(my_poll["info_chat_id"], f'User @{poll.user.username} not found')
        return
    else:
        user_address = user_address[0]["Stellar"]

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


@update_command_info('/apoll_check', 'Проверка голосования в Ассоциации')
@router.message(Command(commands=["apoll_check"]))
async def cmd_poll_check(message: Message, session: Session):
    if message.reply_to_message:
        await message.react([ReactionTypeEmoji(emoji="👾")])
        my_poll = json.loads(await global_data.mongo_config.load_bot_value(MTLChats.MTLA_Poll,
                                                                           int(message.reply_to_message.poll.id),
                                                                           empty_poll))

        # update answer
        # gs_update_a_table_vote(table_uuid, address, options):
        result, delegates = await gs_check_vote_table(my_poll["google_id"])
        msg_text = ' '.join(result)
        msg_text2 = ' '.join(delegates)
        msg_text = f"{msg_text} \n --------- delegates --------- \n {msg_text2}"
        if result:
            with suppress(TelegramBadRequest):
                await message.reply(msg_text)
    else:
        await message.answer('Требуется в ответ на голосование')


def register_handlers(dp, bot):
    dp.include_router(router)
    logger.info('router polls was loaded')


if __name__ == "__main__":
    pass
    # a = asyncio.run(cmd_save_votes(None))
    # print(a)
