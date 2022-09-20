from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import ParseMode
from aiogram.utils.callback_data import CallbackData
from enum import Enum, unique
from stellar_sdk.exceptions import BaseHorizonError
from MyMTLWalletBot_main import dp, my_gettext
from MyMTLWalletBot_stellar import *
import pyqrcode


# from aiogram.utils.markdown import bold, code, italic, text, link

# https://docs.aiogram.dev/en/latest/quick_start.html
# https://surik00.gitbooks.io/aiogram-lessons/content/chapter3.html

@unique
class MyButtons(Enum):
    HaveKey = 'HaveKey'
    NewKey = 'NewKey'
    Receive = 'Receive'
    Send = 'Send'
    SendTr = 'SendTr'
    SendTools = 'SendTools'
    Setting = 'Setting'
    Swap = 'Swap'
    WalletSetting = 'WalletSetting'
    Support = 'Support'
    Return = 'Return'
    ReturnNew = 'ReturnNew'
    ReSend = 'ReSend'
    Yes = 'Yes'
    No = 'No'
    AddNew = 'AddNew'
    Sign = 'Sign'
    PIN = 'PIN'
    Password = 'Password'
    NoPassword = 'NoPassword'
    AddAsset = 'AddAsset'
    DeleteAsset = 'DeleteAsset'
    AddAssetExpert = 'AddAssetExpert'
    NotImplemented = 'NotImplemented'
    ChangeLang = 'ChangeLang'


@unique
class MyState(Enum):
    MyState = 'MyState'
    StateExit = 'StateExit'
    StateSendFor = 'StateSendFor'
    StateSendSum = 'StateSendSum'
    StateSendConfirm = 'StateSendConfirm'
    StateActivateConfirm = 'StateActivateConfirm'
    StateSign = 'StateSign'
    StateAddWalletPrivate = 'StateAddWalletPrivate'
    StateAddWalletPIN = 'StateAddWalletPIN'
    StatePIN = 'StatePIN'
    StatePassword = 'StatePassword'
    StateSendSumSwap = 'StateSendSumSwap'
    StateSwapConfirm = 'StateSwapConfirm'
    StateAddExpert1 = 'StateAddExpert1'
    StateAddExpert2 = 'StateAddExpert2'
    # send_account = 'send_account'
    send_address = 'send_address'
    Free_Wallet = 'Free_Wallet'
    assets = 'assets'
    send_asset_name = 'send_asset_name'
    send_asset_code = 'send_asset_code'
    send_asset_max_sum = 'send_asset_max_sum'
    receive_asset_name = 'receive_asset_name'
    receive_asset_code = 'receive_asset_code'
    receive_asset_min_sum = 'receive_asset_min_sum'
    send_sum = 'send_sum'
    public_key = 'public_key'
    wallets = 'wallets'
    pin_type = 'pin_type'
    pin = 'pin'
    pin2 = 'pin2'
    xdr = 'xdr'
    tools = 'tools'


cb_add = CallbackData("kb_add", "answer")
cb_default = CallbackData("kb_def", "answer")
cb_send_1 = CallbackData("kb_send_1", "answer")
cb_send_xdr = CallbackData("kb_send_xdr", "answer")
cb_swap_1 = CallbackData("kb_swap_1", "answer")
cb_swap_2 = CallbackData("kb_swap_2", "answer")
cb_add_asset = CallbackData("kb_add_asset", "answer")
cb_del_asset = CallbackData("kb_del_asset", "answer")
cb_setting = CallbackData("kb_setting", "answer", "id")
cb_pin = CallbackData("pin", "answer")
cb_assets = CallbackData("kb_assets", "answer")


def get_kb_add0(chat_id: int) -> types.InlineKeyboardMarkup:
    kb_add0 = types.InlineKeyboardMarkup(row_width=1)
    kb_add0.add(
        types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_have_key'),
                                   callback_data=cb_add.new(answer=MyButtons.HaveKey.value)))
    kb_add0.add(
        types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_get_free'),
                                   callback_data=cb_add.new(answer=MyButtons.NewKey.value)))
    return kb_add0


def get_kb_add1(chat_id: int) -> types.InlineKeyboardMarkup:
    kb_add1 = types.InlineKeyboardMarkup(row_width=1)
    kb_add1.add(
        types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_have_key'),
                                   callback_data=cb_add.new(answer=MyButtons.HaveKey.value)))
    kb_add1.add(
        types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_get_free'),
                                   callback_data=cb_add.new(answer=MyButtons.NewKey.value)))
    kb_add1.add(types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_back'),
                                           callback_data=cb_default.new(answer=MyButtons.Return.value)))
    kb_add1.as_json()
    return kb_add1


def get_kb_resend(chat_id: int) -> types.InlineKeyboardMarkup:
    kb_resend = types.InlineKeyboardMarkup()
    kb_resend.add(types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_resend'),
                                             callback_data=cb_default.new(answer=MyButtons.ReSend.value)))
    kb_resend.add(
        types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_back'),
                                   callback_data=cb_default.new(answer=MyButtons.Return.value)))
    return kb_resend


def get_kb_return(chat_id: int) -> types.InlineKeyboardMarkup:
    kb_return = types.InlineKeyboardMarkup()
    kb_return.add(
        types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_back'),
                                   callback_data=cb_default.new(answer=MyButtons.Return.value)))
    return kb_return


def get_kb_return_new(chat_id: int) -> types.InlineKeyboardMarkup:
    kb_return_new = types.InlineKeyboardMarkup()
    kb_return_new.add(
        types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_back'),
                                   callback_data=cb_default.new(answer=MyButtons.ReturnNew.value)))
    return kb_return_new


def get_kb_send(chat_id: int) -> types.InlineKeyboardMarkup:
    kb_send = types.InlineKeyboardMarkup()
    kb_send.add(types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_send'),
                                           callback_data=cb_default.new(answer=MyButtons.SendTr.value)))
    kb_send.add(types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_back'),
                                           callback_data=cb_default.new(answer=MyButtons.Return.value)))
    return kb_send


def get_kb_send_tools(chat_id: int) -> types.InlineKeyboardMarkup:
    kb_send_tools = types.InlineKeyboardMarkup()
    kb_send_tools.add(
        types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_send'),
                                   callback_data=cb_default.new(answer=MyButtons.SendTr.value)))
    kb_send_tools.add(
        types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_send_tools'),
                                   callback_data=cb_default.new(answer=MyButtons.SendTools.value)))
    kb_send_tools.add(
        types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_back'),
                                   callback_data=cb_default.new(answer=MyButtons.Return.value)))
    return kb_send_tools


def get_kb_yesno_send_xdr(chat_id: int) -> types.InlineKeyboardMarkup:
    kb_yesno_send_xdr = types.InlineKeyboardMarkup()
    kb_yesno_send_xdr.add(
        types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_yes'),
                                   callback_data=cb_send_xdr.new(answer=MyButtons.Yes.value)),
        types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_no'),
                                   callback_data=cb_send_xdr.new(answer=MyButtons.Return.value)))
    kb_yesno_send_xdr.add(
        types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_back'),
                                   callback_data=cb_send_xdr.new(answer=MyButtons.Return.value)))
    return kb_yesno_send_xdr


def get_kb_choose_pin(chat_id: int) -> types.InlineKeyboardMarkup:
    kb_choose_pin = types.InlineKeyboardMarkup()
    kb_choose_pin.add(types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_pin'),
                                                 callback_data=cb_default.new(answer=MyButtons.PIN.value)))
    kb_choose_pin.add(
        types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_password'),
                                   callback_data=cb_default.new(answer=MyButtons.Password.value)))
    kb_choose_pin.add(
        types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_no_password'),
                                   callback_data=cb_default.new(answer=MyButtons.NoPassword.value)))
    return kb_choose_pin


def get_kb_pin(chat_id: int) -> types.InlineKeyboardMarkup:
    kb_pin = types.InlineKeyboardMarkup(row_width=4)
    kb_pin.add(types.InlineKeyboardButton(text="1", callback_data=cb_pin.new(answer=1)),
               types.InlineKeyboardButton(text="2", callback_data=cb_pin.new(answer=2)),
               types.InlineKeyboardButton(text="3", callback_data=cb_pin.new(answer=3)),
               types.InlineKeyboardButton(text="A", callback_data=cb_pin.new(answer="A")))
    kb_pin.add(types.InlineKeyboardButton(text="4", callback_data=cb_pin.new(answer=4)),
               types.InlineKeyboardButton(text="5", callback_data=cb_pin.new(answer=5)),
               types.InlineKeyboardButton(text="6", callback_data=cb_pin.new(answer=6)),
               types.InlineKeyboardButton(text="B", callback_data=cb_pin.new(answer="B")))
    kb_pin.add(types.InlineKeyboardButton(text="7", callback_data=cb_pin.new(answer=7)),
               types.InlineKeyboardButton(text="8", callback_data=cb_pin.new(answer=8)),
               types.InlineKeyboardButton(text="9", callback_data=cb_pin.new(answer=9)),
               types.InlineKeyboardButton(text="C", callback_data=cb_pin.new(answer="C")))
    kb_pin.add(types.InlineKeyboardButton(text="0", callback_data=cb_pin.new(answer=0)),
               types.InlineKeyboardButton(text="D", callback_data=cb_pin.new(answer="D")),
               types.InlineKeyboardButton(text="E", callback_data=cb_pin.new(answer="E")),
               types.InlineKeyboardButton(text="F", callback_data=cb_pin.new(answer="F")))
    kb_pin.add(types.InlineKeyboardButton(text="Del", callback_data=cb_pin.new(answer='Del')),
               types.InlineKeyboardButton(text="Enter", callback_data=cb_pin.new(answer='Enter')))
    kb_pin.add(types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_back'),
                                          callback_data=cb_default.new(answer=MyButtons.Return.value)))
    return kb_pin


def get_kb_nopassword(chat_id: int) -> types.InlineKeyboardMarkup:
    kb_nopassword = types.InlineKeyboardMarkup()
    kb_nopassword.add(
        types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_yes_do'), callback_data=cb_pin.new(answer='Enter')))
    kb_nopassword.add(
        types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_back'),
                                   callback_data=cb_default.new(answer=MyButtons.Return.value)))
    return kb_nopassword


def get_kb_assets(chat_id: int) -> types.InlineKeyboardMarkup:
    kb_assets = types.InlineKeyboardMarkup()
    kb_assets.add(
        types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_delete_one'),
                                   callback_data=cb_assets.new(answer=MyButtons.DeleteAsset.value)))
    kb_assets.add(
        types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_add_list'),
                                   callback_data=cb_assets.new(answer=MyButtons.AddAsset.value)))
    kb_assets.add(types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_add_expert'),
                                             callback_data=cb_assets.new(answer=MyButtons.AddAssetExpert.value)))
    kb_assets.add(
        types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_back'),
                                   callback_data=cb_default.new(answer=MyButtons.Return.value)))
    return kb_assets


async def send_message(user_id: int, msg: str, reply_markup=None, need_new=None, parse_mode=None):
    msg_id = get_last_message_id(user_id)
    if need_new:
        new_msg = await dp.bot.send_message(user_id, msg, reply_markup=reply_markup, parse_mode=parse_mode)
        if msg_id > 0:
            try:
                await dp.bot.delete_message(user_id, msg_id)
            except Exception as ex:
                logger.info(['await send_message, del', user_id, ex])
        set_last_message_id(user_id, new_msg.message_id)
    else:
        try:
            await dp.bot.edit_message_text(msg, user_id, msg_id, reply_markup=reply_markup, parse_mode=parse_mode)
        except Exception as ex:
            new_msg = await dp.bot.send_message(user_id, msg, reply_markup=reply_markup, parse_mode=parse_mode)
            set_last_message_id(user_id, new_msg.message_id)


@dp.message_handler(state='*', commands="start")
async def cmd_start(message: types.Message, state: FSMContext):
    logger.info([message.from_user.id, ' cmd_start'])
    await state.finish()
    # check address
    set_last_message_id(message.from_user.id, 0)
    await send_message(message.from_user.id, 'Loading')

    if fb.execsql1(f"select count(*) from MyMTLWalletBot where user_id = {message.from_user.id}") > 0:
        await cmd_show_start(message.chat.id, state)
    else:
        await cmd_show_create(message.chat.id, get_kb_add0(message.chat.id))
    # first_id = message.message_id - 10 if message.message_id > 100 else 1
    # for idx in reversed(range(first_id, message.message_id + 1)):
    #    try:
    #        await dp.bot.delete_message(message.chat.id, idx)
    #        logger.info(idx)
    #    except Exception as ex:
    #        len(ex.args)
    #        pass


@dp.message_handler(commands="exit")
@dp.message_handler(commands="restart")
async def cmd_exit(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        my_state = data.get(MyState.MyState.value)

    if message.from_user.username == "itolstov":
        if my_state == MyState.StateExit.value:
            async with state.proxy() as data:
                data[MyState.MyState.value] = None
            await message.reply(":[[[")
            exit()
        else:
            async with state.proxy() as data:
                data[MyState.MyState.value] = MyState.StateExit.value
            await message.reply(":'[")


@dp.message_handler(commands="log")
async def cmd_log(message: types.Message):
    if message.from_user.username == "itolstov":
        await dp.bot.send_document(message.chat.id, open('MyMTLWallet_bot.log', 'rb'))


@dp.message_handler(commands="err")
async def cmd_log(message: types.Message):
    if message.from_user.username == "itolstov":
        await dp.bot.send_document(message.chat.id, open('MyMTLWallet_bot.err', 'rb'))


def get_kb_default(chat_id: int) -> types.InlineKeyboardMarkup:
    kb_default = types.InlineKeyboardMarkup()
    kb_default.add(
        types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_receive'),
                                   callback_data=cb_default.new(answer=MyButtons.Receive.value)),
        types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_send'),
                                   callback_data=cb_default.new(answer=MyButtons.Send.value)))
    kb_default.add(types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_swap'),
                                              callback_data=cb_default.new(answer=MyButtons.Swap.value)))
    kb_default.add(types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_setting'),
                                              callback_data=cb_default.new(answer=MyButtons.WalletSetting.value)))
    kb_default.add(types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_change_wallet'),
                                              callback_data=cb_default.new(answer=MyButtons.Setting.value)))
    kb_default.add(types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_support'),
                                              callback_data=cb_default.new(answer=MyButtons.Support.value)))
    if not stellar_is_free_wallet(chat_id):
        kb_default.add(types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_sign'),
                                                  callback_data=cb_default.new(answer=MyButtons.Sign.value)))
    return kb_default


async def cmd_show_start(chat_id: int, state: FSMContext, need_new=None):
    try:
        await state.finish()
        async with state.proxy() as data:
            data[MyState.pin_type.value] = stellar_get_pin_type(chat_id)

        msg = my_gettext(chat_id, 'your_balance') + stellar_get_balance(chat_id)
        await send_message(chat_id, msg, reply_markup=get_kb_default(chat_id), need_new=need_new)
    except Exception as ex:
        logger.info(['cmd_show_start ', chat_id, ex])
        await cmd_setting(chat_id, state)


async def cmd_show_create(chat_id: int, kb_tmp):
    msg = my_gettext(chat_id, 'create_msg')
    await send_message(chat_id, msg, reply_markup=kb_tmp)


async def cmd_info_message(chat_id: int, msg: str, state: FSMContext, send_file=None, resend_transaction=None):
    if send_file:
        photo = types.InputFile(send_file)
        # await bot.send_photo(chat_id=message.chat.id, photo=photo)
        # file = InputMedia(media=types.InputFile(send_file))
        await dp.bot.send_photo(chat_id, photo=photo, caption=msg, parse_mode=ParseMode.MARKDOWN)
        await dp.bot.delete_message(chat_id, get_last_message_id(chat_id))
        await cmd_show_start(chat_id, state, need_new=True)
    elif resend_transaction:
        await send_message(chat_id, msg, reply_markup=get_kb_resend(chat_id), parse_mode=ParseMode.MARKDOWN)
    else:
        await send_message(chat_id, msg, reply_markup=get_kb_return(chat_id), parse_mode=ParseMode.MARKDOWN)


async def cmd_setting(chat_id: int, state: FSMContext):
    msg = my_gettext(chat_id, 'setting_msg')
    kb_tmp = types.InlineKeyboardMarkup()
    wallets = stellar_get_wallets_list(chat_id)
    for idx, wallet in enumerate(wallets):
        default_name = 'default' if wallet[1] == 1 else 'Set default'
        kb_tmp.add(types.InlineKeyboardButton(text=f"{wallet[0][:4]}..{wallet[0][-4:]}",
                                              callback_data=cb_setting.new(answer='NAME', id=idx)),
                   types.InlineKeyboardButton(text=f"{default_name}",
                                              callback_data=cb_setting.new(answer='DEFAULT', id=idx)),
                   types.InlineKeyboardButton(text=f"Delete",
                                              callback_data=cb_setting.new(answer='DELETE', id=idx))
                   )
    kb_tmp.add(types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_add_new'),
                                          callback_data=cb_default.new(answer=MyButtons.AddNew.value)))
    kb_tmp.add(types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_back'),
                                          callback_data=cb_default.new(answer=MyButtons.Return.value)))
    await send_message(chat_id, msg, reply_markup=kb_tmp)
    async with state.proxy() as data:
        data[MyState.wallets.value] = wallets


async def cmd_wallet_setting(chat_id: int, state: FSMContext):
    msg = my_gettext(chat_id, 'wallet_setting_msg')
    kb_wallet_setting = types.InlineKeyboardMarkup()
    kb_wallet_setting.add(
        types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_add_asset'),
                                   callback_data=cb_default.new(answer=MyButtons.AddAsset.value)))
    kb_wallet_setting.add(
        types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_buy'),
                                   callback_data=cb_default.new(answer=MyButtons.NotImplemented.value)))
    kb_wallet_setting.add(
        types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_get_key'),
                                   callback_data=cb_default.new(answer=MyButtons.NotImplemented.value)))
    kb_wallet_setting.add(
        types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_set_password'),
                                   callback_data=cb_default.new(answer=MyButtons.NotImplemented.value)))
    kb_wallet_setting.add(
        types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_remove_password'),
                                   callback_data=cb_default.new(answer=MyButtons.NotImplemented.value)))
    kb_wallet_setting.add(
        types.InlineKeyboardButton(text=my_gettext(chat_id, "change_lang"),
                                   callback_data=cb_default.new(answer=MyButtons.ChangeLang.value)))
    kb_wallet_setting.add(
        types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_back'),
                                   callback_data=cb_default.new(answer=MyButtons.Return.value)))
    await send_message(chat_id, msg, reply_markup=kb_wallet_setting)


async def cmd_show_sign(chat_id: int, state: FSMContext, msg='', use_send=False):
    msg = msg + my_gettext(chat_id, 'send_xdr')
    async with state.proxy() as data:
        data[MyState.MyState.value] = MyState.StateSign.value
        tools = data.get(MyState.tools.value)
    if use_send:
        kb = get_kb_send(chat_id)
        if tools:
            kb = get_kb_send_tools(chat_id)
            kb["inline_keyboard"][1][0]["text"] = f'Send to {tools}'
    else:
        kb = get_kb_return(chat_id)

    if len(msg) > 4000:
        await send_message(chat_id, my_gettext(chat_id, 'big_xdr'), reply_markup=kb,
                           parse_mode=ParseMode.MARKDOWN)
    else:
        await send_message(chat_id, msg, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)


async def cmd_show_send_tr(chat_id: int, state: FSMContext, tools=None):
    async with state.proxy() as data:
        xdr = data.get(MyState.xdr.value)
        tools_url = data.get(MyState.tools.value, 'bad url')
    try:
        if tools:
            try:
                # logger.info({"tx_body": xdr})
                rq = requests.post("https://mtl.ergvein.net/update", data={"tx_body": xdr})
                parse_text = rq.text
                if parse_text.find('Transaction history') > 0:
                    await cmd_info_message(chat_id, my_gettext(chat_id, 'check_here').format(tools_url), state)
                else:
                    parse_text = parse_text[parse_text.find('<section id="main">'):parse_text.find("</section>")]
                    await cmd_info_message(chat_id, parse_text[:4000], state)
            except Exception as ex:
                logger.info(['cmd_show_send_tr', chat_id, ex])
                await cmd_info_message(chat_id, my_gettext(chat_id, 'send_error'), state)

        else:
            stellar_send(xdr)
            await cmd_info_message(chat_id, my_gettext(chat_id, 'send_good'), state)
    except BaseHorizonError as ex:
        logger.info(['send BaseHorizonError', ex])
        msg = f"{ex.title}, error {ex.status}"
        await cmd_info_message(chat_id, f"{my_gettext(chat_id, 'send_error')}\n{msg}", state, resend_transaction=True)
    except Exception as ex:
        logger.info(['send unknown error', ex])
        msg = 'unknown error'
        async with state.proxy() as data:
            data[MyState.xdr.value] = xdr
        await cmd_info_message(chat_id, f"{my_gettext(chat_id, 'send_error')}\n{msg}", state, resend_transaction=True)


async def cmd_show_add_wallet_private(chat_id: int, state: FSMContext, msg=''):
    msg = msg + my_gettext(chat_id, 'send_key')
    async with state.proxy() as data:
        data[MyState.MyState.value] = MyState.StateAddWalletPrivate.value
    await send_message(chat_id, msg, reply_markup=get_kb_return(chat_id), parse_mode=ParseMode.MARKDOWN)


async def cmd_show_add_wallet_choose_pin(chat_id: int, state: FSMContext, msg=''):
    msg = msg + my_gettext(chat_id, 'choose_protect')
    await send_message(chat_id, msg, reply_markup=get_kb_choose_pin(chat_id), parse_mode=ParseMode.MARKDOWN)


async def cmd_send_01(chat_id: int, state: FSMContext, msg=''):
    msg = msg + my_gettext(chat_id, 'send_address')
    async with state.proxy() as data:
        data[MyState.MyState.value] = MyState.StateSendFor.value
        data[MyState.Free_Wallet.value] = stellar_is_free_wallet(chat_id)
    await send_message(chat_id, msg, reply_markup=get_kb_return(chat_id))


async def cmd_send_02(chat_id: int, state: FSMContext):
    async with state.proxy() as data:
        address = data.get(MyState.send_address.value)

    msg = my_gettext(chat_id, 'choose_token').format(address)
    kb_tmp = types.InlineKeyboardMarkup()
    asset_list = stellar_get_balance_list(chat_id)
    sender_asset_list = stellar_get_balance_list(chat_id, address)
    for token in asset_list:
        for sender_token in sender_asset_list:
            if token[0] == sender_token[0]:
                kb_tmp.add(types.InlineKeyboardButton(text=f"{token[0]} ({token[1]})",
                                                      callback_data=cb_send_1.new(answer=token[0])))
    kb_tmp.add(types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_back'),
                                          callback_data=cb_default.new(answer=MyButtons.Return.value)))
    await send_message(chat_id, msg, reply_markup=kb_tmp, need_new=True)
    async with state.proxy() as data:
        data[MyState.assets.value] = asset_list


async def cmd_send_03(chat_id: int, state: FSMContext, msg=''):
    async with state.proxy() as data:
        data[MyState.MyState.value] = MyState.StateSendSum.value
        msg = msg + my_gettext(chat_id, 'send_sum').format(data.get(MyState.send_asset_name.value),
                                                           data.get(MyState.send_asset_max_sum.value, 0.0))
    await send_message(chat_id, msg, reply_markup=get_kb_return(chat_id))


async def cmd_send_04(chat_id: int, state: FSMContext):
    async with state.proxy() as data:
        send_sum = data.get(MyState.send_sum.value)
        send_asset = data.get(MyState.send_asset_name.value)
        send_address = data.get(MyState.send_address.value)

        msg = my_gettext(chat_id, 'confirm_send').format(send_sum, send_asset, send_address)
        data[MyState.MyState.value] = MyState.StateSendConfirm.value
        send_asset_name = data[MyState.send_asset_name.value]
        send_asset_code = data[MyState.send_asset_code.value]

    xdr = stellar_pay(stellar_get_user_account(chat_id).account.account_id,
                      send_address,
                      Asset(send_asset_name, send_asset_code), send_sum)

    async with state.proxy() as data:
        data[MyState.xdr.value] = xdr

    await send_message(chat_id, msg, reply_markup=get_kb_yesno_send_xdr(chat_id))


async def cmd_send_11(chat_id: int, state: FSMContext):
    async with state.proxy() as data:
        send_sum = 3
        asset_list = stellar_get_balance_list(chat_id, asset_filter='XLM')
        send_asset_name = asset_list[0][2]
        send_asset_code = asset_list[0][3]
        send_address = data.get(MyState.send_address.value, 'None 0_0')
        msg = my_gettext(chat_id, 'confirm_activate').format(send_address, send_sum)

        data[MyState.send_asset_name.value] = send_asset_name
        data[MyState.send_asset_code.value] = send_asset_code
        data[MyState.send_sum.value] = send_sum
        data[MyState.MyState.value] = MyState.StateActivateConfirm.value

    xdr = stellar_pay(stellar_get_user_account(chat_id).account.account_id,
                      send_address,
                      Asset(send_asset_name, send_asset_code), send_sum, create=True)

    async with state.proxy() as data:
        data[MyState.xdr.value] = xdr

    await send_message(chat_id, msg, reply_markup=get_kb_yesno_send_xdr(chat_id))


async def cmd_swap_01(chat_id: int, state: FSMContext, msg=''):
    msg = my_gettext(chat_id, 'choose_token_swap')
    kb_tmp = types.InlineKeyboardMarkup()
    asset_list = stellar_get_balance_list(chat_id)
    for token in asset_list:
        kb_tmp.add(types.InlineKeyboardButton(text=f"{token[0]} ({token[1]})",
                                              callback_data=cb_swap_1.new(answer=token[0])))
    kb_tmp.add(types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_back'),
                                          callback_data=cb_default.new(answer=MyButtons.Return.value)))
    await send_message(chat_id, msg, reply_markup=kb_tmp)
    async with state.proxy() as data:
        data[MyState.assets.value] = asset_list


async def cmd_swap_02(chat_id: int, state: FSMContext, msg=''):
    async with state.proxy() as data:
        data[MyState.MyState.value] = MyState.StateSendSum.value
        send_asset = data.get(MyState.send_asset_name.value)
        send_asset_code = data.get(MyState.send_asset_code.value)

        msg = my_gettext(chat_id, 'choose_token_swap2').format(send_asset)

    kb_tmp = types.InlineKeyboardMarkup()
    asset_list = []
    for token in stellar_get_balance_list(chat_id):
        asset_list.append(Asset(token[2], token[3]))

    receive_asset = stellar_check_receive_asset(Asset(send_asset, send_asset_code), '0.1', asset_list)

    for asset in receive_asset:
        kb_tmp.add(types.InlineKeyboardButton(text=f"{asset}",
                                              callback_data=cb_swap_2.new(answer=asset)))
    kb_tmp.add(types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_back'),
                                          callback_data=cb_default.new(answer=MyButtons.Return.value)))
    await send_message(chat_id, msg, reply_markup=kb_tmp)
    # async with state.proxy() as data:
    #    data[MyState.assets.value] = asset_list


async def cmd_swap_03(chat_id: int, state: FSMContext, msg=''):
    async with state.proxy() as data:
        data[MyState.MyState.value] = MyState.StateSendSumSwap.value
        msg = msg + my_gettext(chat_id, 'send_sum_swap').format(data.get(MyState.send_asset_name.value),
                                                                data.get(MyState.send_asset_max_sum.value, 0.0),
                                                                data.get(MyState.receive_asset_name.value))
    await send_message(chat_id, msg, reply_markup=get_kb_return(chat_id))


async def cmd_swap_04(chat_id: int, state: FSMContext):
    async with state.proxy() as data:
        send_sum = data.get(MyState.send_sum.value)
        send_asset = data.get(MyState.send_asset_name.value)
        send_asset_code = data.get(MyState.send_asset_code.value)
        receive_asset = data.get(MyState.receive_asset_name.value)
        receive_asset_code = data.get(MyState.receive_asset_code.value)
        data[MyState.MyState.value] = MyState.StateSwapConfirm.value

    receive_sum = stellar_check_receive_sum(Asset(send_asset, send_asset_code), str(send_sum),
                                            Asset(receive_asset, receive_asset_code))
    xdr = stellar_swap(stellar_get_user_account(chat_id).account.account_id, Asset(send_asset, send_asset_code),
                       str(send_sum), Asset(receive_asset, receive_asset_code), str(receive_sum))

    msg = my_gettext(chat_id, 'confirm_swap').format(send_sum, send_asset, receive_sum, receive_asset)
    async with state.proxy() as data:
        data[MyState.xdr.value] = xdr

    await send_message(chat_id, msg, reply_markup=get_kb_yesno_send_xdr(chat_id))


async def cmd_add_asset(chat_id: int, state: FSMContext):
    msg = my_gettext(chat_id, 'delete_asset')
    await send_message(chat_id, msg, reply_markup=get_kb_assets(chat_id))


async def cmd_add_asset_del(chat_id: int, state: FSMContext):
    my_asset = {}
    kb_tmp = types.InlineKeyboardMarkup()
    for item in stellar_get_balance_list(chat_id):
        my_asset[item[0]] = item[3]
        kb_tmp.add(types.InlineKeyboardButton(text=f"{item[0]} ({item[1]})",
                                              callback_data=cb_del_asset.new(answer=item[0])))

    msg = my_gettext(chat_id, 'delete_asset2')

    kb_tmp.add(types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_back'),
                                          callback_data=cb_default.new(answer=MyButtons.Return.value)))
    await send_message(chat_id, msg, reply_markup=kb_tmp)
    async with state.proxy() as data:
        data[MyState.assets.value] = my_asset


async def cmd_add_asset_add(chat_id: int, state: FSMContext, msg=''):
    if stellar_is_free_wallet(chat_id) and (len(stellar_get_balance_list(chat_id)) > 2):
        await send_message(chat_id, my_gettext(chat_id, 'only_3'), reply_markup=get_kb_return(chat_id))
        return False

    good_asset = get_good_asset_dict()
    for item in stellar_get_balance_list(chat_id):
        if good_asset.get(item[0]):
            good_asset.pop(item[0])

    if len(good_asset) == 0:
        await send_message(chat_id, my_gettext(chat_id, 'have_all'), reply_markup=get_kb_return(chat_id))
        return False

    kb_tmp = types.InlineKeyboardMarkup()
    for key in good_asset:
        kb_tmp.add(types.InlineKeyboardButton(text=f"{key}",
                                              callback_data=cb_add_asset.new(answer=key)))
    kb_tmp.add(types.InlineKeyboardButton(text=my_gettext(chat_id, 'kb_back'),
                                          callback_data=cb_default.new(answer=MyButtons.Return.value)))
    await send_message(chat_id, my_gettext(chat_id, 'open_asset'), reply_markup=kb_tmp)
    async with state.proxy() as data:
        data[MyState.assets.value] = good_asset


async def cmd_add_asset_expert(chat_id: int, state: FSMContext):
    if stellar_is_free_wallet(chat_id) and (len(stellar_get_balance_list(chat_id)) > 2):
        await send_message(chat_id, my_gettext(chat_id, 'only_3'), reply_markup=get_kb_return(chat_id))
        return False

    async with state.proxy() as data:
        data[MyState.MyState.value] = MyState.StateAddExpert1.value
    msg = my_gettext(chat_id, 'send_code')
    await send_message(chat_id, msg, reply_markup=get_kb_return(chat_id))


async def cmd_add_asset_expert2(chat_id: int, state: FSMContext):
    async with state.proxy() as data:
        data[MyState.MyState.value] = MyState.StateAddExpert2.value
    msg = my_gettext(chat_id, 'send_issuer').format(public_issuer)
    await send_message(chat_id, msg, reply_markup=get_kb_return(chat_id))


async def cmd_add_asset_end(chat_id: int, state: FSMContext, key: str):
    async with state.proxy() as data:
        my_asset: dict = data.get(MyState.assets.value, {})

    xdr = stellar_add_trust(stellar_get_user_account(chat_id).account.account_id, Asset(key, my_asset[key]))

    msg = my_gettext(chat_id, 'confirm_asset').format(key, my_asset[key])

    async with state.proxy() as data:
        data[MyState.xdr.value] = xdr

    await send_message(chat_id, msg, reply_markup=get_kb_yesno_send_xdr(chat_id))


async def cmd_del_asset_end(chat_id: int, state: FSMContext, key: str):
    async with state.proxy() as data:
        my_asset: dict = data.get(MyState.assets.value, {})

    # todo send last coins
    xdr = stellar_add_trust(stellar_get_user_account(chat_id).account.account_id, Asset(key, my_asset[key]),
                            delete=True)

    msg = my_gettext(chat_id, 'confirm_close_asset').format(key, my_asset[key])
    async with state.proxy() as data:
        data[MyState.xdr.value] = xdr

    await send_message(chat_id, msg, reply_markup=get_kb_yesno_send_xdr(chat_id))


async def cmd_ask_pin(chat_id: int, state: FSMContext, msg='Введите пароль\n'):
    async with state.proxy() as data:
        pin_type = data.get(MyState.pin_type.value)
        pin = data.get(MyState.pin.value, '')
        pin2 = data.get(MyState.pin2.value)
        pin_state = data.get(MyState.StatePIN.value, 1)

    if pin_type == 1:  # pin
        msg = msg + "\n" + ''.ljust(len(pin), '*')
        await send_message(chat_id, msg, reply_markup=get_kb_pin(chat_id))

    if pin_type == 2:  # password
        msg = my_gettext(chat_id, "send_password")

        await send_message(chat_id, msg, reply_markup=get_kb_return(chat_id))
        async with state.proxy() as data:
            data[MyState.MyState.value] = MyState.StatePassword.value

    if pin_type == 0:  # password
        async with state.proxy() as data:
            data[MyState.pin.value] = chat_id
        await send_message(chat_id, my_gettext(chat_id, 'confirm_send2'), reply_markup=get_kb_nopassword(chat_id))


@dp.message_handler(content_types=['photo'], state='*')
async def handle_docs_photo(message: types.Message, state: FSMContext):
    logger.info(f'{message.from_user.id}')
    async with state.proxy() as data:
        my_state = data.get(MyState.MyState.value)
    if my_state == MyState.StateSendFor.value:
        if message.photo:
            await message.photo[-1].download(destination_file=f'qr/{message.from_user.id}.jpg')
            from PIL import Image
            from pyzbar.pyzbar import decode
            data = decode(Image.open(f"qr/{message.from_user.id}.jpg"))
            if data:
                logger.info(str(data[0].data))
                message.text = data[0].data.decode()
                await cmd_all(message, state)
                return
    await message.delete()


@dp.message_handler(state='*')
async def cmd_all(message: types.Message, state: FSMContext):
    need_delete = True
    chat_id = message.chat.id
    async with state.proxy() as data:
        my_state = data.get(MyState.MyState.value)

    if my_state == MyState.StateAddWalletPrivate.value:
        logger.info(f"{message.from_user.id}, '****'")
    else:
        logger.info(f"{message.from_user.id}, {message.text[:10]}")

    if my_state == MyState.StateSendFor.value:
        account = stellar_check_account(message.text)
        if account:
            async with state.proxy() as data:
                data[MyState.send_address.value] = account.account.account_id
                data[MyState.MyState.value] = '0'
            await cmd_send_02(message.chat.id, state)
            need_delete = False
        else:
            async with state.proxy() as data:
                free_wallet = data.get(MyState.Free_Wallet.value, 1)
            address = message.text
            if address.find('*') > 0:
                try:
                    address = resolve_stellar_address(address).account_id
                except Exception as ex:
                    logger.info(["StateSendFor", address, ex])
            if (not free_wallet) and (len(address) == 56) and (address[0] == 'G'):  # need activate
                async with state.proxy() as data:
                    data[MyState.send_address.value] = address
                    data[MyState.MyState.value] = '0'
                await cmd_send_11(message.chat.id, state)
            else:
                await cmd_send_01(message.chat.id, state, my_gettext(chat_id, 'send_error2'))
    elif my_state == MyState.StateSendSum.value:
        try:
            send_sum = float(message.text)
        except:
            send_sum = 0.0

        if send_sum > 0.0:
            async with state.proxy() as data:
                data[MyState.send_sum.value] = send_sum
                data[MyState.MyState.value] = '0'

            await cmd_send_04(message.chat.id, state)
        else:
            await cmd_send_03(message.chat.id, state, my_gettext(chat_id, 'bad_sum'))
    elif my_state == MyState.StateSign.value:
        try:
            xdr = stellar_check_xdr(message.text)
            if xdr:
                async with state.proxy() as data:
                    data[MyState.StatePIN.value] = 14
                    data[MyState.xdr.value] = xdr
                    if message.text.find('mtl.ergvein.net/view') > -1:
                        data[MyState.tools.value] = message.text
                await cmd_ask_pin(message.chat.id, state)
            else:
                raise Exception('Bad xdr')
        except Exception as ex:
            logger.info(['my_state == MyState.StateSign', ex])
            await cmd_show_sign(message.chat.id, state, my_gettext(chat_id, 'bad_xdr').format(message.text))
    elif my_state == MyState.StateAddWalletPrivate.value:
        try:
            public_key = stellar_save_new(message.from_user.id, message.text, False)
            async with state.proxy() as data:
                data[MyState.MyState.value] = '0'
                data[MyState.public_key.value] = public_key
            await cmd_show_add_wallet_choose_pin(message.chat.id, state,
                                                 my_gettext(chat_id, 'for_address').format(public_key))
        except Exception as ex:
            logger.info(ex)
            await cmd_show_add_wallet_private(message.chat.id, state,
                                              my_gettext(chat_id, 'bad_key'))
    elif my_state == MyState.StatePassword.value:
        try:
            public_key = stellar_save_new(message.from_user.id, message.text, False)
            async with state.proxy() as data:
                data[MyState.MyState.value] = '0'
                data[MyState.public_key.value] = public_key
            await cmd_show_add_wallet_choose_pin(message.chat.id, state,
                                                 my_gettext(chat_id, 'for_address').format(public_key))
        except Exception as ex:
            logger.info(ex)
            await cmd_show_add_wallet_private(message.chat.id, state,
                                              my_gettext(chat_id, 'bad_key'))
    elif my_state == MyState.StateSendSumSwap.value:
        try:
            send_sum = float(message.text)
        except:
            send_sum = 0.0

        if send_sum > 0.0:
            async with state.proxy() as data:
                data[MyState.send_sum.value] = send_sum
                data[MyState.MyState.value] = '0'

            await cmd_swap_04(message.chat.id, state)
        else:
            await cmd_swap_03(message.chat.id, state, my_gettext(chat_id, 'bad_sum'))
    elif my_state == MyState.StateAddExpert1.value:
        asset_code = message.text
        my_asset = {asset_code: 'MyMTLWallet'}
        async with state.proxy() as data:
            data[MyState.assets.value] = my_asset
        await cmd_add_asset_expert2(message.chat.id, state)
    elif my_state == MyState.StateAddExpert2.value:
        async with state.proxy() as data:
            my_asset: dict = data.get(MyState.assets.value, {})
        my_key = ''
        for key in my_asset:
            my_asset[key] = message.text
            my_key = key
        async with state.proxy() as data:
            data[MyState.assets.value] = my_asset
        await cmd_add_asset_end(message.chat.id, state, my_key)

    if need_delete:
        await message.delete()


if __name__ == "__main__":
    pass
