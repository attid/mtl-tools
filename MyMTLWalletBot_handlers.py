import pyqrcode
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import ParseMode, InputMedia, InputMediaPhoto
from aiogram.types.base import InputFile
from aiogram.utils.callback_data import CallbackData
from PIL import Image
from enum import Enum, unique

from stellar_sdk.exceptions import BaseHorizonError

from MyMTLWalletBot_main import dp, logger
from MyMTLWalletBot_stellar import *


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
    StateSendSumSwap = 'StateSendSumSwap'
    StateSwapConfirm = 'StateSwapConfirm'
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
    message_id = 'message_id'
    wallets = 'wallets'
    pin_type = 'pin_type'
    pin = 'pin'
    pin2 = 'pin2'
    xdr = 'xdr'
    tools = 'tools'


cb_add = CallbackData("kb_add", "answer")
cb_default = CallbackData("kb_def", "answer")
kb_add0 = types.InlineKeyboardMarkup(row_width=1)
kb_add0.add(
    types.InlineKeyboardButton(text="У меня есть ключ", callback_data=cb_add.new(answer=MyButtons.HaveKey.value)))
kb_add0.add(
    types.InlineKeyboardButton(text="Создать бесплатный аккаунт",
                               callback_data=cb_add.new(answer=MyButtons.NewKey.value)))

kb_add1 = types.InlineKeyboardMarkup(row_width=1)
kb_add1.add(
    types.InlineKeyboardButton(text="У меня есть ключ", callback_data=cb_add.new(answer=MyButtons.HaveKey.value)))
kb_add1.add(
    types.InlineKeyboardButton(text="Создать бесплатный аккаунт",
                               callback_data=cb_add.new(answer=MyButtons.NewKey.value)))
kb_add1.add(types.InlineKeyboardButton(text="<-Back", callback_data=cb_default.new(answer=MyButtons.Return.value)))

kb_resend = types.InlineKeyboardMarkup()
kb_resend.add(types.InlineKeyboardButton(text="Попробовать отправить еще раз",
                                         callback_data=cb_default.new(answer=MyButtons.ReSend.value)))
kb_resend.add(types.InlineKeyboardButton(text="<-Back", callback_data=cb_default.new(answer=MyButtons.Return.value)))

kb_return = types.InlineKeyboardMarkup()
kb_return.add(types.InlineKeyboardButton(text="<-Back", callback_data=cb_default.new(answer=MyButtons.Return.value)))

kb_return_new = types.InlineKeyboardMarkup()
kb_return_new.add(
    types.InlineKeyboardButton(text="<-Back", callback_data=cb_default.new(answer=MyButtons.ReturnNew.value)))

kb_send = types.InlineKeyboardMarkup()
kb_send.add(types.InlineKeyboardButton(text="Send", callback_data=cb_default.new(answer=MyButtons.SendTr.value)))
kb_send.add(types.InlineKeyboardButton(text="<-Back", callback_data=cb_default.new(answer=MyButtons.Return.value)))

kb_send_tools = types.InlineKeyboardMarkup()
kb_send_tools.add(types.InlineKeyboardButton(text="Send", callback_data=cb_default.new(answer=MyButtons.SendTr.value)))
kb_send_tools.add(
    types.InlineKeyboardButton(text="Send to tools", callback_data=cb_default.new(answer=MyButtons.SendTools.value)))
kb_send_tools.add(
    types.InlineKeyboardButton(text="<-Back", callback_data=cb_default.new(answer=MyButtons.Return.value)))

cb_send_1 = CallbackData("kb_send_1", "answer")
cb_send_4 = CallbackData("kb_send_4", "answer")
cb_swap_1 = CallbackData("kb_swap_1", "answer")
cb_swap_2 = CallbackData("kb_swap_2", "answer")
kb_yesno_send = types.InlineKeyboardMarkup()
kb_yesno_send.add(types.InlineKeyboardButton(text="Yes", callback_data=cb_send_4.new(answer=MyButtons.Yes.value)),
                  types.InlineKeyboardButton(text="No", callback_data=cb_send_4.new(answer=MyButtons.Return.value)))
kb_yesno_send.add(types.InlineKeyboardButton(text="<-Back", callback_data=cb_send_4.new(answer=MyButtons.Return.value)))
cb_setting = CallbackData("kb_setting", "answer", "id")

kb_choose_pin = types.InlineKeyboardMarkup()
kb_choose_pin.add(types.InlineKeyboardButton(text="PIN", callback_data=cb_default.new(answer=MyButtons.PIN.value)))
kb_choose_pin.add(
    types.InlineKeyboardButton(text="Password", callback_data=cb_default.new(answer=MyButtons.Password.value)))
kb_choose_pin.add(
    types.InlineKeyboardButton(text="No password", callback_data=cb_default.new(answer=MyButtons.NoPassword.value)))

cb_pin = CallbackData("pin", "answer")
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
kb_pin.add(types.InlineKeyboardButton(text="<-Back", callback_data=cb_default.new(answer=MyButtons.Return.value)))

kb_nopassword = types.InlineKeyboardMarkup()
kb_nopassword.add(types.InlineKeyboardButton(text="Yes, do it.", callback_data=cb_pin.new(answer='Enter')))
kb_nopassword.add(
    types.InlineKeyboardButton(text="<-Back", callback_data=cb_default.new(answer=MyButtons.Return.value)))


@dp.message_handler(state='*', commands="start")
async def cmd_start(message: types.Message, state: FSMContext):
    logger.info(message.from_user.id, 'cmd_start')
    await state.finish()
    # check address
    msg = await message.answer('Loading')
    if fb.execsql1(f"select count(*) from MyMTLWalletBot where user_id = {message.from_user.id}") > 0:
        await cmd_show_start(message.from_user.id, msg.message_id, message.chat.id, state)
    else:
        await cmd_show_create(message.from_user.id, msg.message_id, message.chat.id, kb_add0)
    # first_id = message.message_id - 10 if message.message_id > 100 else 1
    # for idx in reversed(range(first_id, message.message_id + 1)):
    #    try:
    #        await dp.bot.delete_message(message.chat.id, idx)
    #        print(idx)
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


def get_kb_default(user_id: int) -> types.InlineKeyboardMarkup:
    kb_default = types.InlineKeyboardMarkup()
    kb_default.add(
        types.InlineKeyboardButton(text="Receive", callback_data=cb_default.new(answer=MyButtons.Receive.value)),
        types.InlineKeyboardButton(text="Send", callback_data=cb_default.new(answer=MyButtons.Send.value)))
    kb_default.add(
        types.InlineKeyboardButton(text="Swap Assets", callback_data=cb_default.new(answer=MyButtons.Swap.value)))
    kb_default.add(
        types.InlineKeyboardButton(text="Change wallet", callback_data=cb_default.new(answer=MyButtons.Setting.value)))
    kb_default.add(
        types.InlineKeyboardButton(text="Wallet setting",
                                   callback_data=cb_default.new(answer=MyButtons.WalletSetting.value)))
    kb_default.add(
        types.InlineKeyboardButton(text="Support", callback_data=cb_default.new(answer=MyButtons.Support.value)))
    if stellar_is_free_wallet(user_id) == 0:
        kb_default.add(
            types.InlineKeyboardButton(text="Sign", callback_data=cb_default.new(answer=MyButtons.Sign.value)))
    return kb_default


async def cmd_show_start(user_id: int, msg_id: int, chat_id: int, state: FSMContext, NeedNew=None):
    try:
        async with state.proxy() as data:
            data[MyState.pin_type.value] = stellar_get_pin_type(user_id)

        msg = "Ваш баланс \n" + stellar_get_balance(user_id)
        if NeedNew:
            await dp.bot.send_message(chat_id, msg, reply_markup=get_kb_default(user_id))
            await dp.bot.delete_message(chat_id, msg_id)
        else:
            await dp.bot.edit_message_text(msg, chat_id, msg_id, reply_markup=get_kb_default(user_id))
    except Exception as ex:
        print('cmd_show_start', user_id, ex)
        await cmd_setting(user_id, msg_id, chat_id, state)


async def cmd_show_create(user_id: int, msg_id: int, chat_id: int, kb_tmp):
    msg = "Если у вас есть кошелек вы можете ввести приватный ключ и использовать свой кошелек в этом боте." \
          "Так же вы можете указать пинкод и ключ будет хранится в шифрованом виде. " \
          "В случае потери пинкода вы не сможете использовать свой кошелек.\n\n" \
          "Вы так же можете создать бесплатный кошелек, но в нем будут доступны только токены MTL и EURMTL" \
          "В случае неипользования бесплатного кошелька более полугода," \
          " администрация оставляет за собой право удаления вашего аккаунта."
    await dp.bot.edit_message_text(msg, chat_id, msg_id, reply_markup=kb_tmp)


async def cmd_info_message(user_id: int, msg_id: int, chat_id: int, msg: str, send_file=None, resend_transaction=None):
    if send_file:
        photo = types.InputFile(send_file)
        # await bot.send_photo(chat_id=message.chat.id, photo=photo)
        # file = InputMedia(media=types.InputFile(send_file))
        await dp.bot.send_photo(chat_id, photo=photo, caption=msg, reply_markup=kb_return_new,
                                parse_mode=ParseMode.MARKDOWN)
        await dp.bot.delete_message(chat_id, msg_id)
    elif resend_transaction:
        await dp.bot.edit_message_text(msg, chat_id, msg_id, reply_markup=kb_resend, parse_mode=ParseMode.MARKDOWN)
    else:
        await dp.bot.edit_message_text(msg, chat_id, msg_id, reply_markup=kb_return, parse_mode=ParseMode.MARKDOWN)


async def cmd_setting(user_id: int, msg_id: int, chat_id: int, state: FSMContext):
    msg = "Настройка кошельков, тут вы можете выбрать дефолтный кошелк, добавить новый," \
          " сменить пин или удалить кошелек"
    kb_tmp = types.InlineKeyboardMarkup()
    wallets = stellar_get_wallets_list(user_id)
    for idx, wallet in enumerate(wallets):
        default_name = 'default' if wallet[1] == 1 else 'Set default'
        kb_tmp.add(types.InlineKeyboardButton(text=f"{wallet[0][:4]}..{wallet[0][-4:]}",
                                              callback_data=cb_setting.new(answer='NAME', id=idx)),
                   types.InlineKeyboardButton(text=f"{default_name}",
                                              callback_data=cb_setting.new(answer='DEFAULT', id=idx)),
                   types.InlineKeyboardButton(text=f"Delete",
                                              callback_data=cb_setting.new(answer='DELETE', id=idx))
                   )
    kb_tmp.add(types.InlineKeyboardButton(text="Add New", callback_data=cb_default.new(answer=MyButtons.AddNew.value)))
    kb_tmp.add(types.InlineKeyboardButton(text="<-Back", callback_data=cb_default.new(answer=MyButtons.Return.value)))
    await dp.bot.edit_message_text(msg, chat_id, msg_id, reply_markup=kb_tmp)
    async with state.proxy() as data:
        data[MyState.wallets.value] = wallets


async def cmd_wallet_setting(user_id: int, msg_id: int, chat_id: int, state: FSMContext):
    msg = "Настройка кошелька, тут вы добавить линии доверия(asset), получить свой приватный ключ для бекапа," \
          " удалить пин или установить новый. Для смены пина удалите старый. "
    kb_wallet_setting = types.InlineKeyboardMarkup()
    kb_wallet_setting.add(
        types.InlineKeyboardButton(text="Add asset", callback_data=cb_default.new(answer=MyButtons.Return.value)))
    kb_wallet_setting.add(
        types.InlineKeyboardButton(text="Buy this address",
                                   callback_data=cb_default.new(answer=MyButtons.Return.value)))
    kb_wallet_setting.add(
        types.InlineKeyboardButton(text="Get Private Key", callback_data=cb_default.new(answer=MyButtons.Return.value)))
    kb_wallet_setting.add(
        types.InlineKeyboardButton(text="Set password", callback_data=cb_default.new(answer=MyButtons.Return.value)))
    kb_wallet_setting.add(
        types.InlineKeyboardButton(text="Remove password", callback_data=cb_default.new(answer=MyButtons.Return.value)))
    kb_wallet_setting.add(
        types.InlineKeyboardButton(text="<-Back", callback_data=cb_default.new(answer=MyButtons.Return.value)))
    await dp.bot.edit_message_text(msg, chat_id, msg_id, reply_markup=kb_wallet_setting)


async def cmd_show_sign(user_id: int, msg_id: int, chat_id: int, state: FSMContext, msg='', use_send=False):
    msg = msg + "\nПришлите транзакцию в xdr для подписи"

    async with state.proxy() as data:
        data[MyState.MyState.value] = MyState.StateSign.value
        data[MyState.message_id.value] = msg_id
        tools = data.get(MyState.tools.value)
    if use_send:
        kb = kb_send
        if tools:
            kb = kb_send_tools
            kb["inline_keyboard"][1][0]["text"] = f'Send to {tools}'

    else:
        kb = kb_return

    await dp.bot.edit_message_text(msg, chat_id, msg_id, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)


async def cmd_show_send_tr(user_id: int, msg_id: int, chat_id: int, state: FSMContext, tools=None):
    async with state.proxy() as data:
        xdr = data.get(MyState.xdr.value)
    try:
        if tools:
            try:
                # print({"tx_body": xdr})
                rq = requests.post("https://mtl.ergvein.net/update", data={"tx_body": xdr})
                result = rq.text[rq.text.find('<section id="main">'):rq.text.find("</section>")]
                await cmd_info_message(user_id, msg_id, chat_id, result[:4000])
            except Exception as ex:
                print('cmd_show_send_tr', user_id, ex)
                await cmd_info_message(user_id, msg_id, chat_id, 'Ошибка с отправкой =(')

        else:
            stellar_send(xdr)
            await cmd_info_message(user_id, msg_id, chat_id, 'Успешно отправлено')
    except BaseHorizonError as ex:
        logger.info('send BaseHorizonError', ex)
        msg = f"{ex.title}, error {ex.status}"
        await cmd_info_message(user_id, msg_id, chat_id,
                               f'Ошибка с отправкой =(\n{msg}', resend_transaction=True)
    except Exception as ex:
        logger.info('send unknown error', ex)
        msg = 'unknown error'
        async with state.proxy() as data:
            data[MyState.xdr.value] = xdr
        await cmd_info_message(user_id, msg_id, chat_id,
                               f'Ошибка с отправкой =(\n{msg}', resend_transaction=True)


async def cmd_show_add_wallet_private(user_id: int, msg_id: int, chat_id: int, state: FSMContext, msg=''):
    msg = msg + "\nПришлите ваш приватный ключ"
    async with state.proxy() as data:
        data[MyState.MyState.value] = MyState.StateAddWalletPrivate.value
        data[MyState.message_id.value] = msg_id
    await dp.bot.edit_message_text(msg, chat_id, msg_id, reply_markup=kb_return, parse_mode=ParseMode.MARKDOWN)


async def cmd_show_add_wallet_choose_pin(user_id: int, msg_id: int, chat_id: int, state: FSMContext, msg=''):
    msg = msg + "Выберите варианты защиты ключа\n\n" \
                "PIN будет показана цифровая клавиатура при каждой операции(рекомендуется)\n\n" \
                "Пароль. Нужно будет присылать пароль из любых букв и цифр (В разработке)\n\n" \
                "Без пароля. Не нужно будет указывать пароль.\n\n"
    await dp.bot.edit_message_text(msg, chat_id, msg_id, reply_markup=kb_choose_pin, parse_mode=ParseMode.MARKDOWN)


async def cmd_send_01(user_id: int, msg_id: int, chat_id: int, state: FSMContext, msg=''):
    msg = msg + "\nПришлите адрес получателя \nможно федеральный или полный адрес \n" \
                "также можно прислать QRcode с адресом"
    async with state.proxy() as data:
        data[MyState.MyState.value] = MyState.StateSendFor.value
        data[MyState.message_id.value] = msg_id
        data[MyState.Free_Wallet.value] = stellar_is_free_wallet(user_id)
    await dp.bot.edit_message_text(msg, chat_id, msg_id, reply_markup=kb_return)


async def cmd_send_02(user_id: int, msg_id: int, chat_id: int, state: FSMContext):
    async with state.proxy() as data:
        address = data.get(MyState.send_address.value)

    msg = f"Выберите токен для отправки на адрес \n{address}"
    kb_tmp = types.InlineKeyboardMarkup()
    asset_list = stellar_get_balance_list(user_id)
    for token in asset_list:
        kb_tmp.add(types.InlineKeyboardButton(text=f"{token[0]} ({token[1]})",
                                              callback_data=cb_send_1.new(answer=token[0])))
    kb_tmp.add(types.InlineKeyboardButton(text="<-Back", callback_data=cb_default.new(answer=MyButtons.Return.value)))
    await dp.bot.edit_message_text(msg, chat_id, msg_id, reply_markup=kb_tmp)
    async with state.proxy() as data:
        data[MyState.assets.value] = asset_list


async def cmd_send_03(user_id: int, msg_id: int, chat_id: int, state: FSMContext, msg=''):
    async with state.proxy() as data:
        data[MyState.MyState.value] = MyState.StateSendSum.value
        data[MyState.message_id.value] = msg_id
        msg = msg + f"\nПришлите сумму в {data.get(MyState.send_asset_name.value)}\nДоступно\n" \
                    f"{data.get(MyState.send_asset_max_sum.value, 0.0)}"
    await dp.bot.edit_message_text(msg, chat_id, msg_id, reply_markup=kb_return)


async def cmd_send_04(user_id: int, msg_id: int, chat_id: int, state: FSMContext):
    async with state.proxy() as data:
        send_sum = data.get(MyState.send_sum.value)
        send_asset = data.get(MyState.send_asset_name.value)
        send_address = data.get(MyState.send_address.value)

        msg = f"\nВы хотите отправить {send_sum} {send_asset}\n" \
              f"На адрес\n{send_address}"
        data[MyState.MyState.value] = MyState.StateSendConfirm.value
        data[MyState.message_id.value] = msg_id
    await dp.bot.edit_message_text(msg, chat_id, msg_id, reply_markup=kb_yesno_send)


async def cmd_send_11(user_id: int, msg_id: int, chat_id: int, state: FSMContext):
    async with state.proxy() as data:
        send_sum = 3
        asset_list = stellar_get_balance_list(user_id, 'XLM')
        send_asset_name = asset_list[0][2]
        send_asset_code = asset_list[0][3]
        send_address = data.get(MyState.send_address.value, 'None 0_0')
        msg = f"\nАккаунта не существует, если вы хотите активировать адрес {send_address}" \
              f"суммой {send_sum} XLM нажмите кнопку да"

        data[MyState.send_asset_name.value] = send_asset_name
        data[MyState.send_asset_code.value] = send_asset_code
        data[MyState.send_sum.value] = send_sum
        data[MyState.MyState.value] = MyState.StateActivateConfirm.value
        data[MyState.message_id.value] = msg_id
    await dp.bot.edit_message_text(msg, chat_id, msg_id, reply_markup=kb_yesno_send)


async def cmd_swap_01(user_id: int, msg_id: int, chat_id: int, state: FSMContext, msg=''):
    msg = f"Выберите токен для обмена"
    kb_tmp = types.InlineKeyboardMarkup()
    asset_list = stellar_get_balance_list(user_id)
    for token in asset_list:
        kb_tmp.add(types.InlineKeyboardButton(text=f"{token[0]} ({token[1]})",
                                              callback_data=cb_swap_1.new(answer=token[0])))
    kb_tmp.add(types.InlineKeyboardButton(text="<-Back", callback_data=cb_default.new(answer=MyButtons.Return.value)))
    await dp.bot.edit_message_text(msg, chat_id, msg_id, reply_markup=kb_tmp)
    async with state.proxy() as data:
        data[MyState.assets.value] = asset_list


async def cmd_swap_02(user_id: int, msg_id: int, chat_id: int, state: FSMContext, msg=''):
    async with state.proxy() as data:
        data[MyState.MyState.value] = MyState.StateSendSum.value
        data[MyState.message_id.value] = msg_id
        msg = f"Выберите токен, на который вы хотите обменять свои {data.get(MyState.send_asset_name.value)}"

    kb_tmp = types.InlineKeyboardMarkup()
    asset_list = stellar_get_balance_list(user_id)
    for token in asset_list:
        kb_tmp.add(types.InlineKeyboardButton(text=f"{token[0]} ({token[1]})",
                                              callback_data=cb_swap_2.new(answer=token[0])))
    kb_tmp.add(types.InlineKeyboardButton(text="<-Back", callback_data=cb_default.new(answer=MyButtons.Return.value)))
    await dp.bot.edit_message_text(msg, chat_id, msg_id, reply_markup=kb_tmp)
    async with state.proxy() as data:
        data[MyState.assets.value] = asset_list


async def cmd_swap_03(user_id: int, msg_id: int, chat_id: int, state: FSMContext, msg=''):
    async with state.proxy() as data:
        data[MyState.MyState.value] = MyState.StateSendSumSwap.value
        data[MyState.message_id.value] = msg_id
        msg = msg + f"\nПришлите сумму в {data.get(MyState.send_asset_name.value)}\nДоступно\n" \
                    f"{data.get(MyState.send_asset_max_sum.value, 0.0)} \n" \
                    f"которая будет обменена на {data.get(MyState.receive_asset_name.value)}"
    await dp.bot.edit_message_text(msg, chat_id, msg_id, reply_markup=kb_return)


async def cmd_swap_04(user_id: int, msg_id: int, chat_id: int, state: FSMContext):
    async with state.proxy() as data:
        send_sum = data.get(MyState.send_sum.value)
        send_asset = data.get(MyState.send_asset_name.value)
        send_asset_code = data.get(MyState.send_asset_code.value)
        receive_asset = data.get(MyState.receive_asset_name.value)
        receive_asset_code = data.get(MyState.receive_asset_code.value)
        data[MyState.MyState.value] = MyState.StateSwapConfirm.value
        data[MyState.message_id.value] = msg_id

    receive_sum = stellar_check_receive_sum(Asset(send_asset, send_asset_code), str(send_sum),
                                            Asset(receive_asset, receive_asset_code))
    xdr = stellar_swap(stellar_get_user_account(user_id).account.account_id, Asset(send_asset, send_asset_code),
                       str(send_sum), Asset(receive_asset, receive_asset_code), str(receive_sum))

    msg = f"\nВы хотите обменять ваши {send_sum} {send_asset}\n" \
          f"На {receive_sum} {receive_asset} ?"
    async with state.proxy() as data:
        data[MyState.xdr.value] = xdr

    await dp.bot.edit_message_text(msg, chat_id, msg_id, reply_markup=kb_yesno_send)


async def cmd_ask_pin(user_id: int, msg_id: int, chat_id: int, state: FSMContext, msg='Введите пароль\n'):
    async with state.proxy() as data:
        pin_type = data.get(MyState.pin_type.value)
        pin = data.get(MyState.pin.value, '')
        pin2 = data.get(MyState.pin2.value)
        pin_state = data.get(MyState.StatePIN.value, 1)

    if pin_type == 1:  # pin
        msg = msg + "\n" + ''.ljust(len(pin), '*')
        await dp.bot.edit_message_text(msg, chat_id, msg_id, reply_markup=kb_pin)

    if pin_type == 2:  # password
        pass

    if pin_type == 0:  # password
        async with state.proxy() as data:
            data[MyState.pin.value] = user_id
        await dp.bot.edit_message_text('Подтвердите отправку', chat_id, msg_id, reply_markup=kb_nopassword)


@dp.message_handler(content_types=['photo'], state='*')
async def handle_docs_photo(message: types.Message, state: FSMContext):
    logger.info(f'{message.from_user.id}')
    async with state.proxy() as data:
        my_state = data.get(MyState.MyState.value)
        master_msg_id = data.get(MyState.message_id.value)
    if my_state == MyState.StateSendFor.value:
        if message.photo:
            await message.photo[-1].download(destination_file=f'qr/{message.from_user.id}.jpg')
            from PIL import Image
            from pyzbar.pyzbar import decode
            data = decode(Image.open(f"qr/{message.from_user.id}.jpg"))
            if data:
                print(data[0].data)
                message.text = data[0].data.decode()
                await cmd_all(message, state)
                return
    await message.delete()


@dp.message_handler(state='*')
async def cmd_all(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        my_state = data.get(MyState.MyState.value)
        master_msg_id = data.get(MyState.message_id.value)

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
            await cmd_send_02(message.from_user.id, master_msg_id, message.chat.id, state)
        else:
            async with state.proxy() as data:
                free_wallet = data.get(MyState.Free_Wallet.value, 1)
            address = message.text
            if address.find('*') > 0:
                try:
                    address = resolve_stellar_address(address).account_id
                except Exception as ex:
                    print("StateSendFor", address, ex)
            if (free_wallet == 0) and (len(address) == 56) and (address[0] == 'G'):  # need activate
                async with state.proxy() as data:
                    data[MyState.send_address.value] = address
                    data[MyState.MyState.value] = '0'
                await cmd_send_11(message.from_user.id, master_msg_id, message.chat.id, state)
            else:
                await cmd_swap_01(message.from_user.id, master_msg_id, message.chat.id, state,
                                  "Не удалось найти кошелек или он не активирован")
    elif my_state == MyState.StateSendSum.value:
        try:
            send_sum = float(message.text)
        except:
            send_sum = 0.0

        if send_sum > 0.0:
            async with state.proxy() as data:
                data[MyState.send_sum.value] = send_sum
                data[MyState.MyState.value] = '0'

            await cmd_send_04(message.from_user.id, master_msg_id, message.chat.id, state)
        else:
            await cmd_send_03(message.from_user.id, master_msg_id, message.chat.id, state,
                              "Не удалось распознать сумму")
    elif my_state == MyState.StateSign.value:
        try:
            xdr = stellar_check_xdr(message.text)
            if xdr:
                async with state.proxy() as data:
                    data[MyState.StatePIN.value] = 14
                    data[MyState.xdr.value] = xdr
                    if message.text.find('mtl.ergvein.net/view') > -1:
                        data[MyState.tools.value] = 'mtl.ergvein.net'
                await cmd_ask_pin(message.from_user.id, master_msg_id, message.chat.id, state)
            else:
                raise Exception('Bad xdr')
        except Exception as ex:
            print('my_state == MyState.StateSign', ex)
            await cmd_show_sign(message.from_user.id, master_msg_id, message.chat.id, state,
                                f"Не удалось загрузить транзакцию\n\n{message.text}\n")
    elif my_state == MyState.StateAddWalletPrivate.value:
        try:
            public_key = stellar_save_new(message.from_user.id, message.text, False)
            async with state.proxy() as data:
                data[MyState.MyState.value] = '0'
                data[MyState.public_key.value] = public_key
            await cmd_show_add_wallet_choose_pin(message.from_user.id, master_msg_id, message.chat.id, state,
                                                 f"Для кошелька {public_key}\n")
        except Exception as ex:
            print(ex)
            await cmd_show_add_wallet_private(message.from_user.id, master_msg_id, message.chat.id, state,
                                              "Не удалось прочесть ключ\n\n")
    elif my_state == MyState.StateSendSumSwap.value:
        try:
            send_sum = float(message.text)
        except:
            send_sum = 0.0

        if send_sum > 0.0:
            async with state.proxy() as data:
                data[MyState.send_sum.value] = send_sum
                data[MyState.MyState.value] = '0'

            await cmd_swap_04(message.from_user.id, master_msg_id, message.chat.id, state)
        else:
            await cmd_swap_03(message.from_user.id, master_msg_id, message.chat.id, state,
                              "Не удалось распознать сумму")

    await message.delete()


if __name__ == "__main__":
    # pass
    xdr = 'AAAAAgAAAADXM/FKYDkdJMoH7qR0azpDSfND7E9VelL2D5ys9ViskAAAAGQCGVTNAAABgQAAAAAAAAAAAAAAAQAAAAAAAAABAAAAAB8N4lXiL0FplpVrQ5iTsTwtOxUszs3AoRe4yFqUQzrxAAAAAUFRVUEAAAAAW5QuU6wzyP0KgMx8GxqF19g4qcQZd6rRizrwV/jjPfAAAAAAAJiWgAAAAAAAAAAB9ViskAAAAEDqf8NPOVPNfBdOFfg+0U8DFVblL2jJ7Tb6PQzWNpJMOG6+IEAW0xDUGl9kGFTv6ezJ+q8Jxf1MoZ3JsxtbqCwA'
    try:
        stellar_send(xdr)
    except BaseHorizonError as ex:
        msg = f"{ex.title}, error {ex.status}, {ex.extras['result_codes']}"
        logger.info('pin_state == 13 BaseHorizonError', msg)
        print(msg)
        print(2)
    except Exception as ex:
        # logger.info('pin_state == 13 unknown error', ex)
        # msg = 'unknown error'
        print(3)
