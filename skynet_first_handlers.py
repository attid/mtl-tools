from os.path import isfile

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import ParseMode, ChatPermissions
import json
import mystellar
import mystellar2
from datetime import datetime
from datetime import timedelta

import update_report3
from skynet_main import dp, logger, multi_reply, multi_answer, delete_income, cmd_save_delete_income, is_admin, \
    welcome_message, cmd_save_welcome_message, scheduler, is_skynet_admin, MTLChats, add_text, cb_captcha

# from aiogram.utils.markdown import bold, code, italic, text, link

# https://docs.aiogram.dev/en/latest/quick_start.html
# https://surik00.gitbooks.io/aiogram-lessons/content/chapter3.html
from keyrate import show_key_rate

startmsg = """
Я молодой бот
Это все что я умею:
/start  начать все с чистого листа
/links  показать полезные ссылки
/dron2 открыть линию доверия дрону2
/mtlcamp открыть линию доверия mtlcamp
/blacklist операции с блеклистом
/get_vote_fund_xdr сделать транзакцию на обновление голосов фонда
/get_vote_city_xdr сделать транзакцию на обновление голосов сити
/editxdr редактировать транзакцию
/show_bdm показать инфо по БОД

"""

drink_msg = """Выпьем, добрая подружка
Бедной юности моей,
Выпьем с горя; где же кружка?
Сердцу будет веселей.
Спой мне песню, как синица
Тихо за морем жила;
Спой мне песню, как девица
За водой поутру шла."""

link_stellar = "https://stellar.expert/explorer/public/account/"
link_json = "https://raw.githubusercontent.com/montelibero-org/mtl/main/json/"

links_msg = f"""
Полезные ссылки

[Отчет по фонду](https://docs.google.com/spreadsheets/d/1fTOWq7JqX24YEqhCZTQ-z8IICPpgBHXcj91moxkT6R4/edit#gid=1372993507)
[Список всех документов](https://docs.google.com/spreadsheets/d/1x3E1ai_kPVMQ85nuGwuTq1bXD051fnVlf0Dz9NaFoq0)
Тулзы [для подписания](mtl.ergvein.net/) / [расчет голосов и дивов](https://ncrashed.github.io/dividend-tools/votes/)
[Лаборатория](https://laboratory.stellar.org/#?network=public)
Ссылки на аккаунты фонда [Хранение]({link_stellar}{mystellar.public_fond}) / [Эмитент]({link_stellar}{mystellar.public_issuer}) / [Дистрибьютор]({link_stellar}{mystellar.public_distributor}) / [Залоговый счет]({link_stellar}{mystellar.public_pawnshop})
Стакан на [мульки](https://stellar.expert/explorer/public/market/EURMTL-GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V/XLM)
Списки [черный]({link_json}blacklist.json) / [BIM]({link_json}bodreplenish.json) / [донаты]({link_json}donation.json)
Боты [Обмен 1]({link_stellar}GCVF74HQRLPAGTPFSYUAKGHSDSMBQTMVSLKWKUU65ULEN7TL4N56IPZ7) / \
[Обмен 2]({link_stellar}GAEFTFGQYWSF5T3RVMBSW2HFZMFZUQFBYU5FUF3JT3ETJ42NXPDWOO2F) / \
[Дивиденды]({link_stellar}GDNHQWZRZDZZBARNOH6VFFXMN6LBUNZTZHOKBUT7GREOWBTZI4FGS7IQ/) / \
[BIM-XLM]({link_stellar}GARUNHJH3U5LCO573JSZU4IOBEVQL6OJAAPISN4JKBG2IYUGLLVPX5OH) / \
[BIM-EURMTL]({link_stellar}GDEK5KGFA3WCG3F2MLSXFGLR4T4M6W6BMGWY6FBDSDQM6HXFMRSTEWBW) / \
[Wallet]({link_stellar}GB72L53HPZ2MNZQY4XEXULRD6AHYLK4CO55YTOBZUEORW2ZTSOEQ4MTL) 
Видео [Как подписывать](https://t.me/MTL_production/26) / [Как проверять](https://t.me/MTL_production/27) / [Как склеить\редактировать транзакции](https://t.me/MTL_production/28)
"""


@dp.message_handler(state='*', commands="start")
@dp.message_handler(state='*', commands="cancel")
@dp.message_handler(state='*', commands="help")
@dp.message_handler(state='*', commands="reset")
async def cmd_start(message: types.Message, state: FSMContext):
    # Cancel state and inform user about it
    await state.finish()
    # And remove keyboard (just in case)
    await message.reply(startmsg)


# Хэндлер на команду /options
@dp.message_handler(commands="options")
async def cmd_test1(message: types.Message):
    await message.reply("У вас нет прав на изменение настроек")


@dp.message_handler(commands="answer")
async def cmd_answer(message: types.Message):
    await message.answer("Это простой ответ")


@dp.message_handler(commands="save")
async def cmd_save(message: types.Message):
    logger.info(f'save {message.text}')
    logger.info(f'{message}')
    if message.from_user.username == "itolstov":
        await message.answer("Готово")
    else:
        await message.answer('Saved')


@dp.message_handler(commands="links")
async def cmd_links(message: types.Message):
    await message.answer(links_msg, parse_mode=ParseMode.MARKDOWN)


@dp.message_handler(commands="drink")
async def cmd_drink(message: types.Message):
    # await message.answer(drink_msg)
    await message.answer(mystellar.cmd_get_info(6))


@dp.message_handler(commands="decode")
async def cmd_decode(message: types.Message):
    try:
        if message.text.find('mtl.ergvein.net/view') > -1:
            msg = mystellar.check_url_xdr(message.get_args())
        else:
            msg = mystellar.decode_xdr(message.get_args())
        msg = f'\n'.join(msg)
        await message.reply(msg)
    except Exception as e:
        print(message.get_args())
        print(e)
        await message.reply(f'Параметр не распознан. Надо ссылку на тулзу')


@dp.message_handler(commands="show_bdm")
async def cmd_show_bdm(message: types.Message):
    await message.answer(mystellar.cmd_show_bdm())


@dp.message_handler(commands="balance")
async def cmd_show_balance(message: types.Message):
    await message.answer(mystellar.get_safe_balance())


@dp.message_handler(commands="show_key_rate")
async def cmd_show_key_rate(message: types.Message):
    key = 'key'
    if len(message.get_args()) > 2:
        arg = message.get_args().split()
        key = arg[0]
    await message.answer(show_key_rate(key))


@dp.message_handler(commands="do_bdm")
async def cmd_do_bdm(message: types.Message):
    if not await is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return False

    # новая запись
    list_id = mystellar.cmd_create_list(datetime.now().strftime('Basic Income %d/%m/%Y'), 1)  # ('mtl div 17/12/2021')
    lines = []
    msg = await message.answer(add_text(lines, 1, f"Start BDM pays. PayID №{list_id}. Step (1/7)"))
    result = mystellar.cmd_calc_bods(list_id)
    await msg.edit_text(add_text(lines, 2, f"Found {len(result)} addresses. Try gen xdr. Step (2/7)"))

    i = 1
    while i > 0:
        i = mystellar.cmd_gen_xdr(list_id)
        await msg.edit_text(add_text(lines, 3, f"Part done. Need {i} more. Step (3/7)"))

    await msg.edit_text(add_text(lines, 4, f"Try send transactions. Step (4/7)"))
    i = 1
    e = 1
    while i > 0:
        try:
            i = mystellar.cmd_send(list_id)
            await msg.edit_text(add_text(lines, 5, f"Part done. Need {i} more. Step (5/7)"))
        except Exception as err:
            await msg.edit_text(add_text(lines, 6, f"Got error. New attempt {e}. Step (6/7)"))
            e += 1
    await msg.edit_text(add_text(lines, 7, f"BDM. Work done. Step (7/7)"))


@dp.message_handler(commands="do_key_rate")
async def cmd_do_key_rate(message: types.Message):
    if not await is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return False

    await message.answer(show_key_rate('key'))

    # новая запись
    list_id = mystellar.cmd_create_list(datetime.now().strftime('Key Rate %d/%m/%Y'), 3)  # ('mtl div 17/12/2021')
    lines = []
    msg = await message.answer(add_text(lines, 1, f"Start key rate pays. PayID №{list_id}. Step (1/6)"))

    i = 1
    while i > 0:
        i = mystellar.cmd_gen_key_rate_xdr(list_id)

        await msg.edit_text(add_text(lines, 2, f"Part done. Need {i} more. Step (2/6)"))

    await msg.edit_text(add_text(lines, 3, f"Try send transactions. Step (3/6)"))
    i = 1
    e = 1
    while i > 0:
        try:
            i = mystellar.cmd_send(list_id)
            await msg.edit_text(add_text(lines, 4, f"Part done. Need {i} more. Step (4/6)"))
        except Exception as err:
            await msg.edit_text(add_text(lines, 5, f"Got error. New attempt {e}. Step (5/6)"))
            e += 1
    await msg.edit_text(add_text(lines, 6, f"Key rate. Work done. Step (6/6)"))


@dp.message_handler(commands="do_all")
async def cmd_do_all(message: types.Message):
    if not await is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return False

    await cmd_do_div(message)
    await cmd_show_bdm(message)
    await cmd_do_bdm(message)
    await cmd_do_key_rate(message)


@dp.message_handler(commands="do_div")
async def cmd_do_div(message: types.Message):
    if not await is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return False

    # новая запись
    # ('mtl div 17/12/2021')
    div_list_id = mystellar.cmd_create_list(datetime.now().strftime('mtl div %d/%m/%Y'), 0)
    donate_list_id = mystellar.cmd_create_list(datetime.now().strftime('donate %d/%m/%Y'), 0)
    lines = []
    msg = await message.answer(
        add_text(lines, 1, f"Start div pays №{div_list_id} donate pays №{donate_list_id}. Step (1/12)"))
    result = mystellar.cmd_calc_divs(div_list_id, donate_list_id)
    await msg.edit_text(add_text(lines, 2, f"Found {len(result)} addresses. Try gen xdr. Step (2/12)"))

    i = 1
    while i > 0:
        i = mystellar.cmd_gen_xdr(div_list_id)
        await msg.edit_text(add_text(lines, 3, f"Div part done. Need {i} more. Step (3/12)"))

    i = 1
    while i > 0:
        i = mystellar.cmd_gen_xdr(donate_list_id)
        await msg.edit_text(add_text(lines, 4, f"Donate part done. Need {i} more. Step (4/12)"))

    await msg.edit_text(add_text(lines, 5, f"Try send div transactions. Step (5/12)"))
    i = 1
    e = 1
    while i > 0:
        try:
            i = mystellar.cmd_send(div_list_id)
            await msg.edit_text(add_text(lines, 6, f"Part done. Need {i} more. Step (6/12)"))
        except Exception as err:
            await msg.edit_text(add_text(lines, 7, f"Got error. New attempt {e}. Step (7/12)"))
            e += 1
    await msg.edit_text(add_text(lines, 8, f"All work done. Step (8/12)"))

    await msg.edit_text(add_text(lines, 9, f"Try send donate transactions. Step (9/12)"))
    i = 1
    e = 1
    while i > 0:
        try:
            i = mystellar.cmd_send(donate_list_id)
            await msg.edit_text(add_text(lines, 10, f"Part done. Need {i} more. Step (10/12)"))
        except Exception as err:
            await msg.edit_text(add_text(lines, 11, f"Got error. New attempt {e}. Step (11/12)"))
            e += 1
    await msg.edit_text(add_text(lines, 12, f"All work done. Step (12/12)"))


@dp.message_handler(commands="open")
async def smd_add_trust_line(message: types.Message, state: FSMContext):
    try:
        args = message.get_args().split()
        xdr = mystellar.stellar_add_fond_trustline(args[1], args[0])
    except ValueError:
        await message.reply('This is not a valid account. Try another.')
        return
    # except Exception:
    #    print('Это что ещё такое?')

    async with state.proxy() as data:
        data['xdr'] = xdr
    await message.reply('Ваша транзакция :')
    await message.reply(xdr)


@dp.message_handler(commands="all")
async def smd_all(message: types.Message, state: FSMContext):
    if message.chat.id == MTLChats.SignGroup.value:
        with open("polls/votes.json", "r") as fp:
            members = list(json.load(fp))
        members.remove("NEED")
        await message.reply(' '.join(members))
    # elif message.chat.id == MTLChats.Test.value:
    #    await message.reply('@SomeoneAny @itolstov')
    elif message.chat.id == MTLChats.DistributedGroup.value:
        result = mystellar.cmd_check_donate_list()
        await message.reply(' '.join(result))
    else:
        all_file = f'polls/all{message.chat.id}'
        if isfile(all_file):
            with open(all_file, "r") as fp:
                members = list(json.load(fp))
            await message.reply(' '.join(members))
        else:
            await message.reply('/all не настроен, используйте /add_all и /del_all')


@dp.message_handler(commands="add_all")
async def smd_add_all(message: types.Message, state: FSMContext):
    if not await is_admin(message):
        await message.reply('You are not admin.')
        return False

    if len(message.get_args()) > 2:
        all_file = f'polls/all{message.chat.id}'
        if isfile(all_file):
            with open(all_file, "r") as fp:
                members = list(json.load(fp))
        else:
            members = []
        arg = message.get_args().split()
        members.extend(arg)
        with open(all_file, "w") as fp:
            json.dump(members, fp)

        await message.reply('Done')
    else:
        await message.reply('не указаны параметры кого добавить')


@dp.message_handler(commands="del_all")
async def smd_del_all(message: types.Message, state: FSMContext):
    if not await is_admin(message):
        await message.reply('You are not admin.')
        return False

    if len(message.get_args()) > 2:
        all_file = f'polls/all{message.chat.id}'
        if isfile(all_file):
            with open(all_file, "r") as fp:
                members = list(json.load(fp))
            arg = message.get_args().split()
            for member in arg:
                if member in members:
                    members.remove(member)
            with open(all_file, "w") as fp:
                json.dump(members, fp)
            await message.reply('Done')
        else:
            await message.reply('Настройки не найдены =(')
    else:
        await message.reply('не указаны параметры кого добавить')


@dp.message_handler(commands="get_vote_fund_xdr")
async def cmd_get_vote_fund_xdr(message: types.Message):
    if len(message.get_args()) > 10:
        arr2 = mystellar2.cmd_get_new_vote_mtl(message.get_args())
        await message.answer(arr2[0])
    else:
        await message.answer('Делаю транзакции подождите несколько секунд')
        arr2 = mystellar2.cmd_get_new_vote_mtl('')
        await message.answer('for FUND')
        await multi_answer(message, arr2[0])


@dp.message_handler(commands="get_vote_city_xdr")
async def cmd_get_vote_city_xdr(message: types.Message):
    if len(message.get_args()) > 10:
        arr2 = mystellar2.cmd_get_new_vote_mtl(message.get_args())
        await message.answer(arr2[0])
    else:
        await message.answer('Делаю транзакции подождите несколько секунд')
        arr1 = mystellar2.cmd_get_new_vote_mtlcity()
        await message.answer('for MTLCITY')
        await multi_answer(message, arr1[0])


@dp.message_handler(commands="get_mrxpinvest_xdr")
async def cmd_get_mrxpinvest_xdr(message: types.Message):
    if len(message.get_args()) > 1:
        xdr = mystellar.get_mrxpinvest_xdr(float(message.get_args()))
        await multi_answer(message, xdr)


@dp.message_handler(commands="delete")
async def cmd_delete(message: types.Message):
    await message.delete()


@dp.message_handler(commands="update_airdrops")
async def cmd_update_airdrops(message: types.Message):
    if not await is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return False

    await message.answer('Запускаю полное обновление')
    update_report3.update_airdrop()
    await message.answer('Обновление завершено')


@dp.message_handler(commands="gen_data")
async def cmd_gen_data(message: types.Message):
    if len(message.get_args()) > 2:
        arg = message.get_args().split()
        if len(arg) > 1:
            arr1 = mystellar.cmd_gen_data_xdr(arg[0], arg[1])
            await message.answer(arr1)
            return
    # else
    await message.reply('Wrong format. Use: /gen_data public_key data_name:data_value')


@dp.message_handler(commands="show_data")
async def cmd_show_data(message: types.Message):
    if len(message.get_args()) > 2:
        arg = message.get_args().split()
        result = mystellar.cmd_show_data(arg[0])
        if len(result) == 0:
            await message.reply('Data not found')
        else:
            await multi_reply(message, '\n'.join(result))
        return
    # else
    await message.reply('Wrong format. Use: /show_data public_key')


@dp.message_handler(commands="delete_income")
async def cmd_delete_income(message: types.Message):
    if not await is_admin(message):
        await message.reply('You are not admin.')
        return False

    if message.chat.id in delete_income:
        delete_income.remove(message.chat.id)
        cmd_save_delete_income()
        await message.reply('Removed')
    else:
        delete_income.append(message.chat.id)
        cmd_save_delete_income()
        await message.reply('Added')


@dp.message_handler(commands="delete_welcome")
async def cmd_delete_welcome(message: types.Message):
    if not await is_admin(message):
        await message.reply('You are not admin.')
        return False

    if message.chat.id in welcome_message:
        welcome_message[message.chat.id] = None
        cmd_save_welcome_message()
    msg = await message.reply('Removed')
    cmd_delete_later(msg, 1)
    cmd_delete_later(message, 1)


@dp.message_handler(commands="set_welcome")
async def cmd_set_welcome(message: types.Message):
    if not await is_admin(message):
        await message.reply('You are not admin.')
        return False

    if len(message.get_args()) > 5:
        welcome_message[str(message.chat.id)] = message.html_text[13:]
        cmd_save_welcome_message()
        msg = await message.reply('Added')
        cmd_delete_later(msg, 1)
    else:
        await cmd_delete_welcome(message)

    cmd_delete_later(message, 1)


@dp.message_handler(commands="set_welcome_button")
async def cmd_set_welcome(message: types.Message):
    if not await is_admin(message):
        await message.reply('You are not admin.')
        return False

    if len(message.get_args()) > 5:
        welcome_message[str(message.chat.id) + 'button'] = message.html_text[19:]
        cmd_save_welcome_message()
        msg = await message.reply('Added')
        cmd_delete_later(msg, 1)
    else:
        msg = await message.reply('need more words')
        cmd_delete_later(msg, 1)

    cmd_delete_later(message, 1)


@dp.message_handler(commands="set_captcha")
async def cmd_set_captcha(message: types.Message):
    if not await is_admin(message):
        await message.reply('You are not admin.')
        return False

    if message.get_args() == 'on':
        welcome_message['captcha'].append(message.chat.id)
        cmd_save_welcome_message()
        msg = await message.reply('captcha on')
        cmd_delete_later(msg, 1)
    elif message.get_args() == 'off':
        welcome_message['captcha'].remove(message.chat.id)
        cmd_save_welcome_message()
        msg = await message.reply('captcha off')
        cmd_delete_later(msg, 1)
    cmd_delete_later(message, 1)


async def cmd_delete_by_scheduler(message: types.Message):
    try:
        await message.delete()
    except:
        pass


def cmd_delete_later(message: types.Message, minutes=5):
    current_time = datetime.now()
    future_time = current_time + timedelta(minutes=minutes)
    scheduler.add_job(cmd_delete_by_scheduler, run_date=future_time, args=(message,))


@dp.message_handler(content_types=types.ContentTypes.NEW_CHAT_MEMBERS)
async def new_chat_member(message: types.Message):
    if str(message.chat.id) in welcome_message:
        if message.from_user in message.new_chat_members:
            msg = welcome_message.get(str(message.chat.id), 'Hi new user')
            if message.from_user.username:
                username = f'@{message.from_user.username} {message.from_user.full_name}'
            else:
                username = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.full_name}</a>'
            msg = msg.replace('$$USER$$', username)

            kb_captcha = None
            if message.chat.id in welcome_message['captcha']:
                btn_msg = welcome_message.get(str(message.chat.id) + 'button', "I'm not bot")
                kb_captcha = types.InlineKeyboardMarkup()
                kb_captcha.add(
                    types.InlineKeyboardButton(text=btn_msg,
                                               callback_data=cb_captcha.new(answer=message.from_user.id)))
                await message.chat.restrict(message.from_user.id, can_send_messages=False,
                                            can_send_media_messages=False, can_send_other_messages=False)

            answer = await message.answer(msg, parse_mode=ParseMode.HTML, disable_web_page_preview=True,
                                          reply_markup=kb_captcha)

            cmd_delete_later(answer)

    if message.chat.id in delete_income:
        await message.delete()

    # if message.chat.id == MTLChats.TestGroup.value:
    #    await message.answer(message.from_user.user_name)
    #    await message.answer(str(message.new_chat_members))


@dp.message_handler(content_types=types.ContentTypes.LEFT_CHAT_MEMBER)
async def left_chat_member(message: types.Message):
    if message.chat.id in delete_income:
        await message.delete()


@dp.callback_query_handler(cb_captcha.filter())
async def cq_captcha(query: types.CallbackQuery, callback_data: dict):
    # logger.info(f'{query.from_user.id}, {callback_data}')

    answer = callback_data["answer"]
    if str(query.from_user.id) == answer:

        await query.answer("Thanks !", show_alert=True)
        chat = await dp.bot.get_chat(query.message.chat.id)
        # logger.info(f'{query.from_user.id}, {chat.permissions}')
        await query.message.chat.restrict(query.from_user.id, permissions=chat.permissions)
        # --//                                  ChatPermissions(can_send_messages=True, can_invite_users=True,
        #                                                  can_send_media_messages=True,
        #                                                  can_send_other_messages=True, can_send_polls=True,
        #                                                  can_add_web_page_previews=True))

    else:
        await query.answer("For other user", show_alert=True)

    return True


@dp.message_handler(commands="exit")
@dp.message_handler(commands="restart")
async def cmd_exit(message: types.Message, state: FSMContext):
    if not await is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return False

    async with state.proxy() as data:
        my_state = data.get('MyState')

    if my_state == 'StateExit':
        async with state.proxy() as data:
            data['MyState'] = None
        await message.reply(":[[[ ушла в закат =(")
        exit()
    else:
        async with state.proxy() as data:
            data['MyState'] = 'StateExit'
        await message.reply(":'[ боюсь")


@dp.message_handler(commands="err")
async def cmd_log(message: types.Message):
    if not await is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return False

    await dp.bot.send_document(message.chat.id, open('skynet.err', 'rb'))


@dp.message_handler(commands="add_skynet_admin")
async def smd_add_skynet_admin(message: types.Message):
    if not await is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return False

    if len(message.get_args()) > 2:
        all_file = f'polls/skynet_admins'
        if isfile(all_file):
            with open(all_file, "r") as fp:
                members = list(json.load(fp))
        else:
            members = []
        arg = message.get_args().split()
        members.extend(arg)
        with open(all_file, "w") as fp:
            json.dump(members, fp)

        await message.reply('Done')
    else:
        await message.reply('не указаны параметры кого добавить')


@dp.message_handler(commands="del_skynet_admin")
async def smd_del_skynet_admin(message: types.Message):
    if not await is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return False

    if len(message.get_args()) > 2:
        all_file = f'polls/skynet_admins'
        if isfile(all_file):
            with open(all_file, "r") as fp:
                members = list(json.load(fp))
            arg = message.get_args().split()
            for member in arg:
                if member in members:
                    members.remove(member)
            with open(all_file, "w") as fp:
                json.dump(members, fp)
            await message.reply('Done')
        else:
            await message.reply('Настройки не найдены =(')
    else:
        await message.reply('не указаны параметры кого добавить')


@dp.message_handler(commands="show_skynet_admin")
async def smd_show_skynet_admin(message: types.Message):
    if not await is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return False

    all_file = f'polls/skynet_admins'
    if isfile(all_file):
        with open(all_file, "r") as fp:
            members = list(json.load(fp))
        await message.reply(' '.join(members))
    else:
        await message.reply('не настроено =( ')


if __name__ == "__main__":
    pass
