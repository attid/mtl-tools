from datetime import datetime

from aiogram import Router, Bot
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile
from loguru import logger
from sqlalchemy.orm import Session

from config_reader import start_path
from scripts.update_report import update_airdrop, update_fest
from utils.aiogram_utils import multi_reply, add_text, multi_answer, get_web_request
from utils.global_data import MTLChats, is_skynet_admin, global_data, update_command_info
from utils.gspread_tools import gs_check_bim, agcm
from utils.img_tools import create_image_with_text
from utils.stellar_utils import (cmd_check_fee, check_url_xdr, decode_xdr, cmd_show_bim, get_cash_balance, get_balances,
                                 MTLAddresses, cmd_create_list, cmd_calc_bim_pays, cmd_gen_xdr, cmd_send_by_list_id,
                                 cmd_calc_divs, cmd_calc_sats_divs, cmd_get_new_vote_all_mtl,
                                 get_btcmtl_xdr, float2str, cmd_show_data, get_damircoin_xdr,
                                 cmd_calc_usdm_divs, get_toc_xdr, find_stellar_public_key, check_mtlap, get_agora_xdr,
                                 get_chicago_xdr, cmd_calc_usdm_usdm_divs, stellar_async_submit, stellar_sign)

router = Router()


@update_command_info("/fee", "показать комиссию в стелларе")
@router.message(Command(commands=["fee"]))
async def cmd_fee(message: Message):
    await message.answer("Комиссия (мин и мах) " + cmd_check_fee())


@update_command_info("/decode", "декодирует xdr использовать: /decode xdr где ")
@router.message(Command(commands=["decode"]))
async def cmd_decode(message: Message):
    try:
        # logger.info(f'decode {message}')
        if message.text.find('eurmtl.me') > -1:
            msg = await check_url_xdr(message.text.split()[1], full_data=message.chat.id in global_data.full_data)
        else:
            msg = decode_xdr(message.text.split()[1], full_data=message.chat.id in global_data.full_data)
        msg = f'\n'.join(msg)
        await multi_reply(message, msg)
    except Exception as e:
        await message.reply(f'Параметр не распознан. Надо xdr или ссылку на тулзу')
        logger.error(e)


@update_command_info("/show_bim", "показать инфо по БДM")
@router.message(Command(commands=["show_bim"]))
async def rt_show_bim_msg(message: Message, session: Session):
    await message.answer(await cmd_show_bim(session))


@update_command_info("/balance", "Показать сколько денег или мулек(EURMTL) в кубышке")
@router.message(Command(commands=["balance"]))
async def cmd_show_balance(message: Message):
    result = await get_cash_balance(message.chat.id)
    create_image_with_text(result, image_size=(550, 600))
    await message.answer_photo(FSInputFile(start_path + 'output_image.png'))


@router.message(Command(commands=["do_council"]))
async def cmd_do_council(message: Message, session: Session):
    if not is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return

    balance = await get_balances(MTLAddresses.public_council)
    if int(balance.get('EURMTL', 0)) < 10:
        await message.reply(f'Low balance at {MTLAddresses.public_council} can`t pay')
        return
    url = "https://distribute-e62teamaya-lm.a.run.app/distribute?address=" + MTLAddresses.public_council

    status, json_data = await get_web_request('GET', url=url, return_type='json')

    print(json_data)
    print(json_data['xdr'])
    print(json_data["distribution"])

    distribution_message = "Distribution:\n"
    for address, amount in json_data["distribution"].items():
        shortened_address = address[:4] + '..' + address[-4:]
        distribution_message += f"{shortened_address}: {amount}\n"

    await message.answer(distribution_message)
    await stellar_async_submit(stellar_sign(json_data['xdr']))
    await message.answer("Work done.")


@router.message(Command(commands=["do_bim"]))
async def cmd_do_bim(message: Message, session: Session):
    if not is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return
    balance = await get_balances(MTLAddresses.public_bod_eur)
    if int(balance.get('EURMTL', 0)) < 10:
        await message.reply(f'Low balance at {MTLAddresses.public_bod_eur} can`t pay BIM')
        return

    # новая запись
    list_id = cmd_create_list(session, datetime.now().strftime('Basic Income %d/%m/%Y'), 1)  # ('mtl div 17/12/2021')
    lines = []
    msg = await message.answer(add_text(lines, 1, f"Start BDM pays. PayID №{list_id}. Step (1/7)"))
    result = await cmd_calc_bim_pays(session, list_id)
    await msg.edit_text(add_text(lines, 2, f"Found {len(result)} addresses. Try gen xdr. Step (2/7)"))

    i = 1
    while i > 0:
        i = cmd_gen_xdr(session, list_id)
        await msg.edit_text(add_text(lines, 3, f"Part done. Need {i} more. Step (3/7)"))

    await msg.edit_text(add_text(lines, 4, f"Try send transactions. Step (4/7)"))
    i = 1
    e = 1
    while i > 0:
        try:
            i = await cmd_send_by_list_id(session, list_id)
            await msg.edit_text(add_text(lines, 5, f"Part done. Need {i} more. Step (5/7)"))
        except Exception as err:
            await msg.edit_text(add_text(lines, 6, f"Got error. New attempt {e}. Step (6/7)"))
            e += 1
    await msg.edit_text(add_text(lines, 7, f"BDM. Work done. Step (7/7)"))


@update_command_info("/do_resend", "Переотправить транзакцию. Только для админов")
@router.message(Command(commands=["do_resend"]))
async def cmd_do_key_rate(message: Message, session: Session):
    if not is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return False

    if len(message.text.split()) > 1:
        list_id = int(message.text.split()[1])
        lines = []
        msg = await message.answer(add_text(lines, 1, f"Start resend. PayID №{list_id}. Step (1/6)"))

        await msg.edit_text(add_text(lines, 3, f"Try send transactions. Step (2/6)"))
        i = 1
        e = 1
        while i > 0:
            try:
                i = await cmd_send_by_list_id(session, list_id)
                await msg.edit_text(add_text(lines, 4, f"Part done. Need {i} more. Step (3/6)"))
            except Exception as err:
                await msg.edit_text(add_text(lines, 5, f"Got error. New attempt {e}. Step (4/6)"))
                logger.info(f'249 line error {err}')
                e += 1
        await msg.edit_text(add_text(lines, 6, f"Resend. Work done. Step (5/6)"))


@router.message(Command(commands=["do_all"]))
async def cmd_do_all(message: Message):
    if not is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return False

    await cmd_do_div(message)
    await cmd_do_sats_div(message)
    await rt_show_bim_msg(message)
    await cmd_do_bim(message)


@update_command_info("/do_div", "начать выплаты дивидентов")
@router.message(Command(commands=["do_div"]))
async def cmd_do_div(message: Message, session: Session):
    if not is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return

    balance = await get_balances(MTLAddresses.public_div)
    if int(balance.get('EURMTL', 0)) < 10:
        await message.reply(f'Low balance at {MTLAddresses.public_div} can`t pay divs')
        return

    # новая запись
    # ('mtl div 17/12/2021')
    div_list_id = cmd_create_list(session, datetime.now().strftime('mtl div %d/%m/%Y'), 0)
    donate_list_id = cmd_create_list(session, datetime.now().strftime('donate %d/%m/%Y'), 0)
    lines = []
    msg = await message.answer(
        add_text(lines, 1, f"Start div pays №{div_list_id} donate pays №{donate_list_id}. Step (1/12)"))
    result = await cmd_calc_divs(session, div_list_id, donate_list_id)
    await msg.edit_text(add_text(lines, 2, f"Found {len(result)} addresses. Try gen xdr. Step (2/12)"))

    i = 1

    while i > 0:
        i = cmd_gen_xdr(session, div_list_id)
        await msg.edit_text(add_text(lines, 3, f"Div part done. Need {i} more. Step (3/12)"))

    i = 1
    while i > 0:
        i = cmd_gen_xdr(session, donate_list_id)
        await msg.edit_text(add_text(lines, 4, f"Donate part done. Need {i} more. Step (4/12)"))

    await msg.edit_text(add_text(lines, 5, f"Try send div transactions. Step (5/12)"))
    i = 1
    e = 1
    while i > 0:
        try:
            i = await cmd_send_by_list_id(session, div_list_id)
            await msg.edit_text(add_text(lines, 6, f"Part done. Need {i} more. Step (6/12)"))
        except Exception as err:
            logger.info(str(err))
            await msg.edit_text(add_text(lines, 7, f"Got error. New attempt {e}. Step (7/12)"))
            e += 1
    await msg.edit_text(add_text(lines, 8, f"All work done. Step (8/12)"))

    await msg.edit_text(add_text(lines, 9, f"Try send donate transactions. Step (9/12)"))
    i = 1
    e = 1
    while i > 0:
        try:
            i = await cmd_send_by_list_id(session, donate_list_id)
            await msg.edit_text(add_text(lines, 10, f"Part done. Need {i} more. Step (10/12)"))
        except Exception as err:
            await msg.edit_text(add_text(lines, 11, f"Got error. New attempt {e}. Step (11/12)"))
            e += 1
    await msg.edit_text(add_text(lines, 12, f"All work done. Step (12/12)"))


@update_command_info("/do_sats_div", "выплата дивидентов в satsmtl")
@router.message(Command(commands=["do_sats_div"]))
async def cmd_do_sats_div(message: Message, session: Session):
    if not is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return

    balance = await get_balances(MTLAddresses.public_div)
    if int(balance.get('SATSMTL', 0)) < 100:
        await message.reply(f'Low sats balance at {MTLAddresses.public_div} can`t pay divs')
        return

    # новая запись
    # ('mtl div 17/12/2021')
    div_list_id = cmd_create_list(session, datetime.now().strftime('mtl div %d/%m/%Y'), 4)
    lines = []
    msg = await message.answer(
        add_text(lines, 1, f"Start div pays №{div_list_id}. Step (1/12)"))
    result = await cmd_calc_sats_divs(session, div_list_id)
    await msg.edit_text(add_text(lines, 2, f"Found {len(result)} addresses. Try gen xdr. Step (2/12)"))

    i = 1

    while i > 0:
        i = cmd_gen_xdr(session, div_list_id)
        await msg.edit_text(add_text(lines, 3, f"Div part done. Need {i} more. Step (3/12)"))

    await msg.edit_text(add_text(lines, 4, f"Try send div transactions. Step (4/12)"))
    i = 1
    e = 1
    while i > 0:
        try:
            i = await cmd_send_by_list_id(session, div_list_id)
            await msg.edit_text(add_text(lines, 5, f"Part done. Need {i} more. Step (5/12)"))
        except Exception as err:
            logger.info(str(err))
            await msg.edit_text(add_text(lines, 6, f"Got error. New attempt {e}. Step (6/12)"))
            e += 1
    await msg.edit_text(add_text(lines, 7, f"All work done. Step (7/12)"))


@router.message(Command(commands=["do_usdm_div"]))
async def cmd_do_usdm_div(message: Message, session: Session):
    if not is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return

    balance = await get_balances(MTLAddresses.public_div)
    if int(balance.get('USDM', 0)) < 10:
        await message.reply(f'Low usdm balance at {MTLAddresses.public_div} can`t pay divs')
        return

    # новая запись
    # ('mtl div 17/12/2021')
    div_list_id = cmd_create_list(session, datetime.now().strftime('mtl div %d/%m/%Y'), 5)
    lines = []
    msg = await message.answer(
        add_text(lines, 1, f"Start div pays №{div_list_id}. Step (1/12)"))
    result = await cmd_calc_usdm_divs(session, div_list_id)
    await msg.edit_text(add_text(lines, 2, f"Found {len(result)} addresses. Try gen xdr. Step (2/12)"))

    i = 1

    while i > 0:
        i = cmd_gen_xdr(session, div_list_id)
        await msg.edit_text(add_text(lines, 3, f"Div part done. Need {i} more. Step (3/12)"))

    await msg.edit_text(add_text(lines, 4, f"Try send div transactions. Step (4/12)"))
    i = 1
    e = 1
    while i > 0:
        try:
            i = await cmd_send_by_list_id(session, div_list_id)
            await msg.edit_text(add_text(lines, 5, f"Part done. Need {i} more. Step (5/12)"))
        except Exception as err:
            logger.info(str(err))
            await msg.edit_text(add_text(lines, 6, f"Got error. New attempt {e}. Step (6/12)"))
            e += 1
    await msg.edit_text(add_text(lines, 7, f"All work done. Step (7/12)"))


@update_command_info("/do_usdm_usdm_div", "выплата дивидентов в usdm от usdm")
@router.message(Command(commands=["do_usdm_usdm_div"]))
async def cmd_do_usdm_usdm_div(message: Message, session: Session):
    if not is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return

    balance = await get_balances(MTLAddresses.public_usdm_div)
    if int(balance.get('USDM', 0)) < 100:
        await message.reply(f'Low usdm balance at {MTLAddresses.public_usdm_div} can`t pay divs')
        return

    # новая запись
    # ('mtl div 17/12/2021')
    div_list_id = cmd_create_list(session, datetime.now().strftime('usdm div %d/%m/%Y'), 6)
    lines = []
    msg = await message.answer(
        add_text(lines, 1, f"Start div pays №{div_list_id}. Step (1/12)"))
    result = await cmd_calc_usdm_usdm_divs(session, div_list_id)
    await msg.edit_text(add_text(lines, 2, f"Found {len(result)} addresses. Try gen xdr. Step (2/12)"))

    i = 1

    while i > 0:
        i = cmd_gen_xdr(session, div_list_id)
        await msg.edit_text(add_text(lines, 3, f"Div part done. Need {i} more. Step (3/12)"))

    await msg.edit_text(add_text(lines, 4, f"Try send div transactions. Step (4/12)"))
    i = 1
    e = 1
    while i > 0:
        try:
            i = await cmd_send_by_list_id(session, div_list_id)
            await msg.edit_text(add_text(lines, 5, f"Part done. Need {i} more. Step (5/12)"))
        except Exception as err:
            logger.info(str(err))
            await msg.edit_text(add_text(lines, 6, f"Got error. New attempt {e}. Step (6/12)"))
            e += 1
    await msg.edit_text(add_text(lines, 7, f"All work done. Step (7/12)"))


@update_command_info("/get_vote_fund_xdr", "сделать транзакцию на обновление голосов фонда")
@router.message(Command(commands=["get_vote_fund_xdr"]))
async def cmd_get_vote_fund_xdr(message: Message):
    if len(message.text.split()) > 1:
        arr2 = await cmd_get_new_vote_all_mtl(message.text.split()[1])
        await message.answer(arr2[0])
    else:
        await message.answer('Делаю транзакции подождите несколько секунд')
        arr2 = await cmd_get_new_vote_all_mtl('')
        await message.answer('for FUND')
        await multi_answer(message, arr2[0])


@update_command_info("/get_btcmtl_xdr",
                     "use - /get_btcmtl_xdr 0.001 XXXXXXX \n where 0.001 sum, XXXXXXXX address to send BTCMTL")
@router.message(Command(commands=["get_btcmtl_xdr"]))
async def cmd_get_defi_xdr_(message: Message):
    arg = message.text.split()
    if len(arg) > 1:
        memo = None if len(arg) < 3 else ' '.join(arg[3:])
        xdr = await get_btcmtl_xdr(float2str(arg[1]), arg[2], memo)
        await multi_answer(message, xdr)
        await multi_answer(message, '\n'.join(decode_xdr(xdr=xdr)))
    else:
        await multi_answer(message,
                           'use -  /get_btcmtl_xdr 0.001 XXXXXXX \n where 0.001 sum, XXXXXXXX address to send BTCMTL')


@router.message(Command(commands=["get_damircoin_xdr"]))
async def cmd_get_damircoin_xdr(message: Message):
    arg = message.text.split()
    if len(arg) > 1:
        xdr = await get_damircoin_xdr(int(arg[1]))
        await multi_answer(message, xdr)
        await multi_answer(message, '\n'.join(decode_xdr(xdr=xdr)))
    else:
        await multi_answer(message,
                           'use -  /get_damircoin_xdr 123 \n where 123 sum in EURMTL')


@router.message(Command(commands=["get_agora_xdr"]))
async def cmd_get_damircoin_xdr(message: Message):
    xdr = await get_agora_xdr()
    await multi_answer(message, xdr)
    await multi_answer(message, '\n'.join(decode_xdr(xdr=xdr)))


@update_command_info("/get_chicago_xdr", "Делает транзакцию кешбека для chicago")
@router.message(Command(commands=["get_chicago_xdr"]))
async def cmd_get_damircoin_xdr(message: Message):
    result = await get_chicago_xdr()
    xdr = result[-1]
    await multi_answer(message, '\n'.join(result[:-1]))
    await multi_answer(message, xdr)
    await multi_answer(message, '\n'.join(decode_xdr(xdr=xdr)))


@router.message(Command(commands=["get_toc_xdr"]))
async def cmd_get_toc_xdr(message: Message):
    arg = message.text.split()
    if len(arg) > 1:
        xdr = await get_toc_xdr(int(arg[1]))
        await multi_answer(message, xdr)
        await multi_answer(message, '\n'.join(decode_xdr(xdr=xdr)))
    else:
        await multi_answer(message,
                           'use -  /get_toc_xdr 123 \n where 123 sum in EURMTL')


@update_command_info("/update_airdrops", "Обновить файл airdrops")
@router.message(Command(commands=["update_airdrops"]))
async def cmd_update_airdrops(message: Message):
    if not is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return False

    await message.answer('Запускаю полное обновление')
    await update_airdrop()
    await message.answer('Обновление завершено')


@router.message(Command(commands=["update_fest"]))
async def cmd_update_fest(message: Message, session: Session):
    await message.answer('Запускаю полное обновление')
    await update_fest(session)
    await message.answer('Обновление завершено')


@update_command_info("/show_data", "Показать какие данные есть в стеларе на этот адрес. Use: /show_data public_key")
@update_command_info("/show_data bdm", "Показать какие данные есть в стеларе по боду")
@update_command_info("/show_data delegate", "Показать какие данные есть в стеларе по делегированию")
@update_command_info("/show_data donate", "Показать какие данные есть в стеларе по донатам в правительство")
@router.message(Command(commands=["show_data"]))
async def route_show_data(message: Message):
    if len(message.text.split()) > 1:
        arg = message.text.split()
        result = await cmd_show_data(arg[1])
        if len(result) == 0:
            await message.reply('Data not found')
        else:
            await multi_reply(message, '\n'.join(result))
        return
    # else
    await message.reply('Wrong format. Use: /show_data public_key')


@router.message(Command(commands=["update_bim1"]))
async def cmd_update_bim1(message: Message, bot: Bot):
    if not is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return

    agc = await agcm.authorize()

    wks = await agc.open("MTL_BIM_register").worksheet("List")
    update_list = []
    data = await wks.get_all_values()
    for record in data[2:]:
        new_data = None
        if record[3]:
            try:
                chat_member = await bot.get_chat_member(chat_id=MTLChats.ShareholderGroup, user_id=int(record[3]))
                new_data = chat_member.is_member
            except:
                new_data = False
        update_list.append([new_data])

    await wks.update('S3', update_list)
    await message.reply('Done')


@router.message(Command(commands=["check_bim"]))
async def cmd_check_bim(message: Message):
    cmd = message.text.split()
    if len(cmd) > 1 and cmd[1][0] == '@':
        if not is_skynet_admin(message):
            await message.reply('You are not my admin.')
            return
        msg = await gs_check_bim(user_name=cmd[1][1:])
    else:
        msg = await gs_check_bim(message.from_user.id)

    await message.reply(msg)


@router.message(Command(commands=["check_mtlap"]))
async def cmd_check_bim(message: Message):
    if not is_skynet_admin(message):
        await message.reply('You are not my admin.')
        return
    key = find_stellar_public_key(message.text)
    if key is None and message.reply_to_message:
        key = find_stellar_public_key(message.reply_to_message.text)

    if key is None:
        await message.reply('Wrong format. Use: /check_mtlap public_key')
        return

    msg = await check_mtlap(key)
    await message.reply(msg)
