from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import ParseMode
from aiogram.utils.callback_data import CallbackData

from enum import Enum, unique
from MyMTLWalletBot_main import dp
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
    Setting = 'Setting'
    WalletSetting = 'WalletSetting'
    Support = 'Support'
    Return = 'Return'
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
    StateSendFor = 'StateSendFor'
    StateSendSum = 'StateSendSum'
    StateSendConfirm = 'StateSendConfirm'
    StateSign = 'StateSign'
    StateAddWalletPrivate = 'StateAddWalletPrivate'
    StateAddWalletPIN = 'StateAddWalletPIN'
    StatePIN = 'StatePIN'
    send_account = 'send_account'
    assets = 'assets'
    send_asset = 'send_asset'
    send_asset_max_sum = 'send_asset_max_sum'
    send_sum = 'send_sum'
    public_key = 'public_key'
    message_id = 'message_id'
    wallets = 'wallets'
    pin_type = 'pin_type'
    pin = 'pin'
    pin2 = 'pin2'
    xdr = 'xdr'


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

kb_default = types.InlineKeyboardMarkup()
kb_default.add(types.InlineKeyboardButton(text="Receive", callback_data=cb_default.new(answer=MyButtons.Receive.value)),
               types.InlineKeyboardButton(text="Send", callback_data=cb_default.new(answer=MyButtons.Send.value)))
kb_default.add(
    types.InlineKeyboardButton(text="Change wallet", callback_data=cb_default.new(answer=MyButtons.Setting.value)))
kb_default.add(
    types.InlineKeyboardButton(text="Wallet setting",
                               callback_data=cb_default.new(answer=MyButtons.WalletSetting.value)))
kb_default.add(types.InlineKeyboardButton(text="Support", callback_data=cb_default.new(answer=MyButtons.Support.value)))
kb_default.add(types.InlineKeyboardButton(text="Sign", callback_data=cb_default.new(answer=MyButtons.Sign.value)))

kb_return = types.InlineKeyboardMarkup()
kb_return.add(types.InlineKeyboardButton(text="<-Back", callback_data=cb_default.new(answer=MyButtons.Return.value)))

kb_send = types.InlineKeyboardMarkup()
kb_send.add(types.InlineKeyboardButton(text="Send", callback_data=cb_default.new(answer=MyButtons.SendTr.value)))
kb_send.add(types.InlineKeyboardButton(text="<-Back", callback_data=cb_default.new(answer=MyButtons.Return.value)))

cb_send_1 = CallbackData("kb_send_1", "answer")
cb_send_4 = CallbackData("kb_send_4", "answer")
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


@dp.message_handler(state='*', commands="start")
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    # check address
    msg = await message.answer('Loading')
    if fb.execsql1(f"select count(*) from MyMTLWalletBot where user_id = {message.from_user.id}") > 0:
        await cmd_show_start(message.from_user.id, msg.message_id, message.chat.id, state)
    else:
        await cmd_show_create(message.from_user.id, msg.message_id, message.chat.id, kb_add0)
    first_id = message.message_id - 10 if message.message_id > 100 else 1
    for idx in reversed(range(first_id, message.message_id + 1)):
        try:
            await dp.bot.delete_message(message.chat.id, idx)
            print(idx)
        except Exception as ex:
            len(ex.args)
            pass


async def cmd_show_start(user_id: int, msg_id: int, chat_id: int, state: FSMContext):
    try:
        async with state.proxy() as data:
            data[MyState.pin_type] = stellar_get_pin_type(user_id)

        msg = "Ваш баланс \n" + stellar_get_balance(user_id)
        await dp.bot.edit_message_text(msg, chat_id, msg_id, reply_markup=kb_default)
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


async def cmd_info_message(user_id: int, msg_id: int, chat_id: int, msg):
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
        data[MyState.wallets] = wallets


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
        data[MyState.MyState] = MyState.StateSign
        data[MyState.message_id] = msg_id
    if use_send:
        kb = kb_send
    else:
        kb = kb_return

    await dp.bot.edit_message_text(msg, chat_id, msg_id, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)


async def cmd_show_send_tr(user_id: int, msg_id: int, chat_id: int, state: FSMContext):
    async with state.proxy() as data:
        xdr = data.get(MyState.xdr)
    try:
        stellar_send(xdr)
        await cmd_info_message(user_id, msg_id, chat_id, 'Успешно отправлено')
    except Exception as ex:
        print('send ', ex)
        await cmd_info_message(user_id, msg_id, chat_id, 'Ошибка с отправкой =(')


async def cmd_show_add_wallet_private(user_id: int, msg_id: int, chat_id: int, state: FSMContext, msg=''):
    msg = msg + "\nПришлите ваш приватный ключ"
    async with state.proxy() as data:
        data[MyState.MyState] = MyState.StateAddWalletPrivate
        data[MyState.message_id] = msg_id
    await dp.bot.edit_message_text(msg, chat_id, msg_id, reply_markup=kb_return, parse_mode=ParseMode.MARKDOWN)


async def cmd_show_add_wallet_choose_pin(user_id: int, msg_id: int, chat_id: int, state: FSMContext, msg=''):
    msg = msg + "Выберите варианты защиты ключа\n\n" \
                "PIN будет показана цифровая клавиатура при каждой операции(рекомендуется)\n\n" \
                "Пароль. Нужно будет присылать пароль из любых букв и цифр (В разработке)\n\n" \
                "Без пароля. Не нужно будет указывать пароль.\n\n"
    await dp.bot.edit_message_text(msg, chat_id, msg_id, reply_markup=kb_choose_pin, parse_mode=ParseMode.MARKDOWN)


async def cmd_send_1(user_id: int, msg_id: int, chat_id: int, state: FSMContext):
    msg = "Выберите токен"
    kb_tmp = types.InlineKeyboardMarkup()
    asset_list = stellar_get_balance_list(user_id)
    for token in asset_list:
        kb_tmp.add(types.InlineKeyboardButton(text=f"{token[0]} ({token[1]})",
                                              callback_data=cb_send_1.new(answer=token[0])))
    kb_tmp.add(types.InlineKeyboardButton(text="<-Back", callback_data=cb_default.new(answer=MyButtons.Return.value)))
    await dp.bot.edit_message_text(msg, chat_id, msg_id, reply_markup=kb_tmp)
    async with state.proxy() as data:
        data[MyState.assets] = asset_list


async def cmd_send_2(user_id: int, msg_id: int, chat_id: int, state: FSMContext, msg=''):
    msg = msg + "\nПришлите получателя \nсейчас поддерживаются только прямые адреса типа \n" \
                "GDX23CPGMQ4LN55VGEDVFZPAJMAUEHSHAMJ2GMCU2ZSHN5QF4TMZYPIS"
    async with state.proxy() as data:
        data[MyState.MyState] = MyState.StateSendFor
        data[MyState.message_id] = msg_id
    await dp.bot.edit_message_text(msg, chat_id, msg_id, reply_markup=kb_return)


async def cmd_send_3(user_id: int, msg_id: int, chat_id: int, state: FSMContext, msg=''):
    async with state.proxy() as data:
        data[MyState.MyState] = MyState.StateSendSum
        data[MyState.message_id] = msg_id
        msg = msg + f"\nПришлите сумму в {data.get(MyState.send_asset).code}\nДоступно\n" \
                    f"{data.get(MyState.send_asset_max_sum, 0.0)}"
    await dp.bot.edit_message_text(msg, chat_id, msg_id, reply_markup=kb_return)


async def cmd_send_4(user_id: int, msg_id: int, chat_id: int, state: FSMContext):
    async with state.proxy() as data:
        send_sum = data.get(MyState.send_sum)
        send_asset = data.get(MyState.send_asset)
        send_account = data.get(MyState.send_account)

        msg = f"\nВы хотите отправить {send_sum} {send_asset.code}\n" \
              f"На адрес\n{send_account.account.account_id}"
        data[MyState.MyState] = MyState.StateSendConfirm
        data[MyState.message_id] = msg_id
    await dp.bot.edit_message_text(msg, chat_id, msg_id, reply_markup=kb_yesno_send)


async def cmd_ask_pin(user_id: int, msg_id: int, chat_id: int, state: FSMContext, msg='Введите пароль\n'):
    async with state.proxy() as data:
        pin_type = data.get(MyState.pin_type)
        pin = data.get(MyState.pin, '')
        pin2 = data.get(MyState.pin2)
        pin_state = data.get(MyState.StatePIN, 1)

    if pin_type == 1:
        msg = msg + "\n" + ''.ljust(len(pin), '*')
        await dp.bot.edit_message_text(msg, chat_id, msg_id, reply_markup=kb_pin)

    if pin_type == 2:
        pass


@dp.callback_query_handler(cb_add.filter())
async def cq_add(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    answer = callback_data["answer"]
    user_id = query.from_user.id
    if answer == MyButtons.HaveKey.value:  # have key
        await cmd_show_add_wallet_private(user_id, query.message.message_id, query.message.chat.id, state)
    elif answer == MyButtons.NewKey.value:  # new
        if stellar_can_new(user_id):
            stellar_create_new(query.from_user.id)
            await cmd_show_start(user_id, query.message.message_id, query.message.chat.id, state)
        else:
            await query.answer("Sorry you can't create more accounts!", show_alert=True)
    else:
        await query.answer("Bad answer!", show_alert=True)
    return True


@dp.callback_query_handler(cb_default.filter())
async def cq_def(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    answer = callback_data["answer"]
    user_id = query.from_user.id

    if answer == MyButtons.Receive.value:  # receive
        msg = f"Сообщите этот **адрес** для отправки \n\n`{stellar_get_user_account(user_id).account.account_id}`"
        await cmd_info_message(user_id, query.message.message_id, query.message.chat.id, msg)
        # await query.message.edit_text(msg, reply_markup=1)
    elif answer == MyButtons.Send.value:  # Send
        await cmd_send_1(user_id, query.message.message_id, query.message.chat.id, state)

    elif answer == MyButtons.Setting.value:
        await cmd_setting(user_id, query.message.message_id, query.message.chat.id, state)
    elif answer == MyButtons.WalletSetting.value:
        await cmd_wallet_setting(user_id, query.message.message_id, query.message.chat.id, state)
    elif answer == MyButtons.Support.value:
        await query.answer("Not ready!", show_alert=True)
        # №async with state.proxy() as data:
        # №    data[MyState.pin_type] = 1
        # №await cmd_ask_pin(user_id, query.message.message_id, query.message.chat.id, state)

    elif answer == MyButtons.AddNew.value:
        await cmd_show_create(user_id, query.message.message_id, query.message.chat.id, kb_add1)
    elif answer == MyButtons.Return.value:
        await cmd_show_start(user_id, query.message.message_id, query.message.chat.id, state)
    elif answer == MyButtons.Sign.value:
        await cmd_show_sign(user_id, query.message.message_id, query.message.chat.id, state)
    elif answer == MyButtons.SendTr.value:
        await cmd_show_send_tr(user_id, query.message.message_id, query.message.chat.id, state)

    elif answer == MyButtons.PIN.value:
        async with state.proxy() as data:
            data[MyState.pin_type] = 1
            data[MyState.StatePIN] = 12
        await cmd_ask_pin(user_id, query.message.message_id, query.message.chat.id, state)
    elif answer == MyButtons.Password.value:
        await query.answer("Not ready!", show_alert=True)
        # async with state.proxy() as data:
        #    data[MyState.pin_type] = 2
        #    data[MyState.StatePIN] = 12
    elif answer == MyButtons.NoPassword.value:
        async with state.proxy() as data:
            data[MyState.pin_type] = 0
        await cmd_show_start(user_id, query.message.message_id, query.message.chat.id, state)


    else:
        await query.answer("Bad answer!", show_alert=True)
    return True


@dp.callback_query_handler(cb_send_1.filter())
async def cq_def(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    answer = callback_data["answer"]
    user_id = query.from_user.id
    async with state.proxy() as data:
        asset_list = data[MyState.assets]
    for asset in asset_list:
        if asset[0] == answer:
            if float(asset[1]) == 0.0:
                await query.answer("sum 0 =( \n маловато будет", show_alert=True)
            else:
                async with state.proxy() as data:
                    data[MyState.send_asset] = asset[2]
                    data[MyState.send_asset_max_sum] = asset[1]
                await cmd_send_2(user_id, query.message.message_id, query.message.chat.id, state)

    return True


@dp.callback_query_handler(cb_send_4.filter())
async def cq_def(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    answer = callback_data["answer"]
    user_id = query.from_user.id
    if answer == MyButtons.Yes.value:
        async with state.proxy() as data:
            data[MyState.StatePIN] = 13
        await cmd_ask_pin(user_id, query.message.message_id, query.message.chat.id, state)
    elif answer == MyButtons.Return.value:  #
        await cmd_show_start(user_id, query.message.message_id, query.message.chat.id, state)
    else:
        await query.answer("Bad answer!", show_alert=True)
    return True


@dp.callback_query_handler(cb_setting.filter())
async def cq_def(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    answer = callback_data["answer"]
    idx = int(callback_data["id"])
    user_id = query.from_user.id
    async with state.proxy() as data:
        wallets = data[MyState.wallets]
    if idx < len(wallets):
        if answer == 'DELETE':
            stellar_delete_wallets(user_id, wallets[idx][0])
            await cmd_setting(user_id, query.message.message_id, query.message.chat.id, state)
        if answer == 'DEFAULT':
            stellar_set_default_wallets(user_id, wallets[idx][0])
            await cmd_setting(user_id, query.message.message_id, query.message.chat.id, state)
        if answer == 'NAME':
            msg = f"{wallets[idx][0]}\nБаланс \n" + stellar_get_balance(user_id, wallets[idx][0])
            await query.answer(msg[:200], show_alert=True)
    return True


@dp.callback_query_handler(cb_pin.filter())
async def cq_pin(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    answer = callback_data["answer"]
    user_id = query.from_user.id
    async with state.proxy() as data:
        pin = data.get(MyState.pin, '')
        pin_state = data.get(MyState.StatePIN, 1)
    if answer in '1234567890ABCDEF':
        pin += answer
        async with state.proxy() as data:
            data[MyState.pin] = pin
        await cmd_ask_pin(user_id, query.message.message_id, query.message.chat.id, state)

    if answer == 'Del':
        pin = pin[:len(pin) - 1]
        async with state.proxy() as data:
            data[MyState.pin] = pin
        await cmd_ask_pin(user_id, query.message.message_id, query.message.chat.id, state)

    if answer == 'Enter':
        if pin_state == 12:  # ask for save need pin2
            async with state.proxy() as data:
                data[MyState.pin2] = pin
                data[MyState.pin] = ''
                data[MyState.StatePIN] = 11
            await cmd_ask_pin(user_id, query.message.message_id, query.message.chat.id, state, 'Повторите пароль\n')
        if pin_state == 11:  # ask pin2 for save
            async with state.proxy() as data:
                pin2 = data.get(MyState.pin2, '')
                public_key = data.get(MyState.public_key, '')
                data[MyState.StatePIN] = 0
                pin_type = data.get(MyState.pin_type, '')
            if pin == pin2:
                stellar_change_password(user_id, public_key, str(user_id), pin, pin_type)
                await cmd_show_start(user_id, query.message.message_id, query.message.chat.id, state)
            else:
                async with state.proxy() as data:
                    data[MyState.pin2] = ''
                    data[MyState.pin] = ''
                    data[MyState.StatePIN] = 12
                await query.answer('Пароли не совпадают, повторите заново', show_alert=True)
        if pin_state == 13:  # send
            async with state.proxy() as data:
                data[MyState.pin] = ''
                data[MyState.StatePIN] = 0
                send_account = data.get(MyState.send_account)
                send_asset = data.get(MyState.send_asset)
                send_sum = data.get(MyState.send_sum)
            try:
                xdr = stellar_pay(stellar_get_user_account(user_id).account.account_id,
                                  send_account.account.account_id,
                                  send_asset, send_sum)
                stellar_send(stellar_sign(xdr, stellar_get_user_keypair(user_id, str(pin)).secret))
                await cmd_info_message(user_id, query.message.message_id, query.message.chat.id, 'Успешно отправлено')
            except Exception as ex:
                print('pin_state == 13', ex)
                await cmd_info_message(user_id, query.message.message_id, query.message.chat.id,
                                       'Ошибка с отправкой =(')
        if pin_state == 14:  # sign
            async with state.proxy() as data:
                data[MyState.pin] = ''
                data[MyState.StatePIN] = 0
                xdr = data.get(MyState.xdr)
            try:
                xdr = stellar_user_sign(xdr, user_id, str(pin))
                async with state.proxy() as data:
                    data[MyState.MyState] = '0'
                    data[MyState.xdr] = xdr
                await cmd_show_sign(user_id, query.message.message_id, query.message.chat.id, state,
                                    f"Ваша транзакция c подписью: \n\n`{xdr}`\n\n", use_send=True)
            except Exception as ex:
                print('pin_state == 14', ex)
                await cmd_info_message(user_id, query.message.message_id, query.message.chat.id,
                                       'Ошибка при подписании, вероятно не правильный пароль. =(')
        return True


@dp.message_handler(state='*')
async def cmd_all(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        my_state = data.get(MyState.MyState)
        master_msg_id = data.get(MyState.message_id)
    if my_state == MyState.StateSendFor:
        account = stellar_check_account(message.text)
        if account:
            async with state.proxy() as data:
                data[MyState.send_account] = account
                data[MyState.MyState] = '0'
            await cmd_send_3(message.from_user.id, master_msg_id, message.chat.id, state)
        else:
            await cmd_send_2(message.from_user.id, master_msg_id, message.chat.id, state,
                             "Не удалось распознать кошелек")
    elif my_state == MyState.StateSendSum:
        try:
            send_sum = float(message.text)
        except:
            send_sum = 0.0

        if send_sum > 0.0:
            async with state.proxy() as data:
                data[MyState.send_sum] = send_sum
                data[MyState.MyState] = '0'

            await cmd_send_4(message.from_user.id, master_msg_id, message.chat.id, state)
        else:
            await cmd_send_3(message.from_user.id, master_msg_id, message.chat.id, state,
                             "Не удалось распознать сумму")
    elif my_state == MyState.StateSign:
        try:
            xdr = stellar_check_xdr(message.text)
            if xdr:
                async with state.proxy() as data:
                    data[MyState.StatePIN] = 14
                    data[MyState.xdr] = xdr
                await cmd_ask_pin(message.from_user.id, master_msg_id, message.chat.id, state)
            else:
                raise Exception('Bad xdr')
        except Exception as ex:
            print('my_state == MyState.StateSign', ex)
            await cmd_show_sign(message.from_user.id, master_msg_id, message.chat.id, state,
                                f"Не удалось загрузить транзакцию\n\n{message.text}\n")
    elif my_state == MyState.StateAddWalletPrivate:
        try:
            public_key = stellar_save_new(message.from_user.id, message.text, False)
            async with state.proxy() as data:
                data[MyState.MyState] = '0'
                data[MyState.public_key] = public_key
            await cmd_show_add_wallet_choose_pin(message.from_user.id, master_msg_id, message.chat.id, state,
                                                 f"Для кошелька {public_key}\n")
        except Exception as ex:
            print(ex)
            await cmd_show_add_wallet_private(message.from_user.id, master_msg_id, message.chat.id, state,
                                              "Не удалось прочесть ключ\n\n")

    await message.delete()


if __name__ == "__main__":
    pass
