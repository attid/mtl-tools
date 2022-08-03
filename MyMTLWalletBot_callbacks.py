from MyMTLWalletBot_handlers import *


def good_id(user_id, msg_id):
    if msg_id == get_last_message_id(user_id):
        return True
    else:
        return False


@dp.callback_query_handler(cb_add.filter())
async def cq_add(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    add_info_log(f'{query.from_user.id}, {callback_data}')
    if not good_id(query.from_user.id, query.message.message_id):
        await query.answer("Old button =(", show_alert=True)
        return True

    answer = callback_data["answer"]
    user_id = query.from_user.id
    if answer == MyButtons.HaveKey.value:  # have key
        await cmd_show_add_wallet_private(query.message.chat.id, state)
    elif answer == MyButtons.NewKey.value:  # new
        if stellar_can_new(user_id):
            stellar_create_new(query.from_user.id)
            await cmd_show_start(query.message.chat.id, state)
        else:
            await query.answer("Sorry you can't create more accounts!", show_alert=True)
    else:
        await query.answer("Bad answer!", show_alert=True)
    return True


@dp.callback_query_handler(cb_default.filter())
async def cq_def(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    add_info_log(query.from_user.id, callback_data)
    if not good_id(query.from_user.id, query.message.message_id):
        await query.answer("Old button =(", show_alert=True)
        return True

    answer = callback_data["answer"]
    user_id = query.from_user.id

    if answer == MyButtons.Receive.value:  # receive
        msg = f"Сообщите этот **адрес** для отправки \n\n`{stellar_get_user_account(user_id).account.account_id}`"
        send_file = f'qr/{stellar_get_user_account(user_id).account.account_id}.png'
        qr = pyqrcode.create(stellar_get_user_account(user_id).account.account_id)
        qr.png(send_file, scale=6)

        await cmd_info_message(query.message.chat.id, msg, send_file)
        # await query.message.edit_text(msg, reply_markup=1)
    elif answer == MyButtons.Send.value:  # Send
        await cmd_send_01(query.message.chat.id, state)

    elif answer == MyButtons.Setting.value:
        await cmd_setting(query.message.chat.id, state)
    elif answer == MyButtons.WalletSetting.value:
        await cmd_wallet_setting(query.message.chat.id, state)
    elif answer == MyButtons.AddNew.value:
        await cmd_show_create(query.message.chat.id, kb_add1)
    elif answer == MyButtons.Return.value:
        await cmd_show_start(query.message.chat.id, state)
    elif answer == MyButtons.ReturnNew.value:
        await cmd_show_start(query.message.chat.id, state, need_new=True)
    elif answer == MyButtons.Sign.value:
        await cmd_show_sign(query.message.chat.id, state)
    elif answer == MyButtons.SendTr.value:
        await cmd_show_send_tr(query.message.chat.id, state)
    elif answer == MyButtons.SendTools.value:
        await cmd_show_send_tr(query.message.chat.id, state, tools='tools')
    elif answer == MyButtons.ReSend.value:
        async with state.proxy() as data:
            xdr = data.get(MyState.xdr.value)
        try:
            await cmd_info_message(user_id, query.message.message_id, query.message.chat.id,
                                   'Пробуем повторно отправить в блокчейн, ожидание до 5 минут'
                                   'пожалуйста не создавайте новых транзакций и дождитесь ответа')
            stellar_send(xdr)
            await cmd_info_message(user_id, query.message.message_id, query.message.chat.id,
                                   'Успешно отправлено')
        except BaseHorizonError as ex:
            add_info_log('ReSend BaseHorizonError', ex)
            msg = f"{ex.title}, error {ex.status}"
            await cmd_info_message(query.message.chat.id, f'Ошибка с отправкой =(\n{msg}', resend_transaction=True)
        except Exception as ex:
            add_info_log('ReSend unknown error', ex)
            msg = 'unknown error'
            async with state.proxy() as data:
                data[MyState.xdr.value] = xdr
            await cmd_info_message(query.message.chat.id, f'Ошибка с отправкой =(\n{msg}', resend_transaction=True)
    elif answer == MyButtons.PIN.value:
        async with state.proxy() as data:
            data[MyState.pin_type.value] = 1
            data[MyState.StatePIN.value] = 12
        await cmd_ask_pin(query.message.chat.id, state)
    elif answer == MyButtons.Password.value:
        await query.answer("Not ready!", show_alert=True)
        # async with state.proxy() as data:
        #    data[MyState.pin_type.value] = 2
        #    data[MyState.StatePIN.value] = 12
    elif answer == MyButtons.NoPassword.value:
        async with state.proxy() as data:
            data[MyState.pin_type.value] = 0
        await cmd_show_start(query.message.chat.id, state)
    elif answer == MyButtons.Swap.value:
        await cmd_swap_01(query.message.chat.id, state)
    elif answer == MyButtons.Support.value:
        await cmd_info_message(query.message.chat.id, 'Бот поддержки @MyMTLWalletSupportBot')
    else:
        await query.answer("Bad answer!", show_alert=True)
    return True


@dp.callback_query_handler(cb_send_1.filter())
async def cq_send1(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    add_info_log(f'{query.from_user.id}, {callback_data}')
    if not good_id(query.from_user.id, query.message.message_id):
        await query.answer("Old button =(", show_alert=True)
        return True

    answer = callback_data["answer"]
    async with state.proxy() as data:
        asset_list = data[MyState.assets.value]
    for asset in asset_list:
        if asset[0] == answer:
            if float(asset[1]) == 0.0:
                await query.answer("sum 0 =( \n маловато будет", show_alert=True)
            else:
                async with state.proxy() as data:
                    data[MyState.send_asset_name.value] = asset[2]
                    data[MyState.send_asset_code.value] = asset[3]
                    data[MyState.send_asset_max_sum.value] = asset[1]
                await cmd_send_03(query.message.chat.id, state)

    return True


@dp.callback_query_handler(cb_swap_1.filter())
async def cq_swap1(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    add_info_log(f'{query.from_user.id}, {callback_data}')
    if not good_id(query.from_user.id, query.message.message_id):
        await query.answer("Old button =(", show_alert=True)
        return True

    answer = callback_data["answer"]
    async with state.proxy() as data:
        asset_list = data[MyState.assets.value]
    for asset in asset_list:
        if asset[0] == answer:
            if float(asset[1]) == 0.0:
                await query.answer("sum 0 =( \n маловато будет", show_alert=True)
            else:
                async with state.proxy() as data:
                    data[MyState.send_asset_name.value] = asset[2]
                    data[MyState.send_asset_code.value] = asset[3]
                    data[MyState.send_asset_max_sum.value] = asset[1]
                await cmd_swap_02(query.message.chat.id, state)

    return True


@dp.callback_query_handler(cb_swap_2.filter())
async def cq_swap2(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    add_info_log(f'{query.from_user.id}, {callback_data}')
    if not good_id(query.from_user.id, query.message.message_id):
        await query.answer("Old button =(", show_alert=True)
        return True

    answer = callback_data["answer"]
    async with state.proxy() as data:
        asset_list = data[MyState.assets.value]
    for asset in asset_list:
        if asset[0] == answer:
            async with state.proxy() as data:
                data[MyState.receive_asset_name.value] = asset[2]
                data[MyState.receive_asset_code.value] = asset[3]
                data[MyState.receive_asset_min_sum.value] = asset[1]
            await cmd_swap_03(query.message.chat.id, state)

    return True


@dp.callback_query_handler(cb_send_4.filter())
async def cq_send4(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    add_info_log(f'{query.from_user.id}, {callback_data}')
    if not good_id(query.from_user.id, query.message.message_id):
        await query.answer("Old button =(", show_alert=True)
        return True

    answer = callback_data["answer"]
    if answer == MyButtons.Yes.value:
        async with state.proxy() as data:
            if data.get(MyState.MyState.value) == MyState.StateSwapConfirm.value:
                data[MyState.StatePIN.value] = 15
            else:
                data[MyState.StatePIN.value] = 13
        await cmd_ask_pin(query.message.chat.id, state)
    elif answer == MyButtons.Return.value:  #
        await cmd_show_start(query.message.chat.id, state)
    else:
        await query.answer("Bad answer!", show_alert=True)
    return True


@dp.callback_query_handler(cb_setting.filter())
async def cq_setting(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    add_info_log(f'{query.from_user.id}, {callback_data}')
    if not good_id(query.from_user.id, query.message.message_id):
        await query.answer("Old button =(", show_alert=True)
        return True

    answer = callback_data["answer"]
    idx = int(callback_data["id"])
    user_id = query.from_user.id
    async with state.proxy() as data:
        wallets = data[MyState.wallets.value]
    if idx < len(wallets):
        if answer == 'DELETE':
            stellar_delete_wallets(user_id, wallets[idx][0])
            await cmd_setting(query.message.chat.id, state)
        if answer == 'DEFAULT':
            stellar_set_default_wallets(user_id, wallets[idx][0])
            await cmd_setting(query.message.chat.id, state)
        if answer == 'NAME':
            msg = f"{wallets[idx][0]}\nБаланс \n" + stellar_get_balance(user_id, wallets[idx][0])
            await query.answer(msg[:200], show_alert=True)
    return True


@dp.callback_query_handler(cb_pin.filter())
async def cq_pin(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    add_info_log(f'{query.from_user.id}, *')
    if not good_id(query.from_user.id, query.message.message_id):
        await query.answer("Old button =(", show_alert=True)
        return True

    answer = callback_data["answer"]
    user_id = query.from_user.id
    async with state.proxy() as data:
        pin = data.get(MyState.pin.value, '')
        pin_state = data.get(MyState.StatePIN.value, 1)
    add_info_log(f'{query.from_user.id}, 1')
    if answer in '1234567890ABCDEF':
        pin += answer
        async with state.proxy() as data:
            data[MyState.pin.value] = pin
        add_info_log(f'{query.from_user.id}, 2')
        await cmd_ask_pin(query.message.chat.id, state)
    add_info_log(f'{query.from_user.id}, 3')

    if answer == 'Del':
        pin = pin[:len(pin) - 1]
        async with state.proxy() as data:
            data[MyState.pin.value] = pin
        await cmd_ask_pin(query.message.chat.id, state)

    if answer == 'Enter':
        if pin_state == 12:  # ask for save need pin2
            async with state.proxy() as data:
                data[MyState.pin2.value] = pin
                data[MyState.pin.value] = ''
                data[MyState.StatePIN.value] = 11
            await cmd_ask_pin(query.message.chat.id, state, 'Повторите пароль\n')
        if pin_state == 11:  # ask pin2 for save
            async with state.proxy() as data:
                pin2 = data.get(MyState.pin2.value, '')
                public_key = data.get(MyState.public_key.value, '')
                data[MyState.StatePIN.value] = 0
                pin_type = data.get(MyState.pin_type.value, '')
            if pin == pin2:
                stellar_change_password(user_id, public_key, str(user_id), pin, pin_type)
                await cmd_show_start(query.message.chat.id, state)
                await state.finish()
            else:
                async with state.proxy() as data:
                    data[MyState.pin2.value] = ''
                    data[MyState.pin.value] = ''
                    data[MyState.StatePIN.value] = 12
                await query.answer('Пароли не совпадают, повторите заново', show_alert=True)
        if pin_state == 13:  # send
            async with state.proxy() as data:
                data[MyState.pin.value] = ''
                data[MyState.StatePIN.value] = 0
                if data.get(MyState.MyState.value) == MyState.StateActivateConfirm.value:
                    send_address = data.get(MyState.send_address.value)
                    create = 1
                if data.get(MyState.MyState.value) == MyState.StateSendConfirm.value:
                    send_address = data.get(MyState.send_address.value)
                    create = 0
                send_asset_name = data.get(MyState.send_asset_name.value)
                send_asset_code = data.get(MyState.send_asset_code.value)
                send_sum = data.get(MyState.send_sum.value)
            try:
                xdr = stellar_pay(stellar_get_user_account(user_id).account.account_id,
                                  send_address,
                                  Asset(send_asset_name, send_asset_code), send_sum, create=create)
                if user_id > 0:
                    xdr = stellar_sign(xdr, stellar_get_user_keypair(user_id, str(pin)).secret)
                    async with state.proxy() as data:
                        data[MyState.xdr.value] = xdr
                    await cmd_info_message(user_id, query.message.message_id, query.message.chat.id,
                                           'Успешно подписано, пробуем отправить в блокчейн, ожидание до 5 минут')
                    stellar_send(xdr)
                    await cmd_info_message(user_id, query.message.message_id, query.message.chat.id,
                                           'Успешно отправлено')
                    await state.finish()
            except BaseHorizonError as ex:
                # add_info_log('pin_state == 13 BaseHorizonError', ex)
                msg = f"{ex.title}, error {ex.status}"
                add_info_log('pin_state == 13', msg)
                await cmd_info_message(query.message.chat.id, f'Ошибка с отправкой =(\n' + msg, resend_transaction=True)
            except Exception as ex:
                add_info_log('pin_state == 13 unknown error', ex)
                msg = 'unknown error'
                await cmd_info_message(query.message.chat.id, f'Ошибка с отправкой =(\n{msg}', resend_transaction=True)
        if pin_state == 14:  # sign
            async with state.proxy() as data:
                data[MyState.pin.value] = ''
                data[MyState.StatePIN.value] = 0
                xdr = data.get(MyState.xdr.value)
            try:
                if user_id > 0:
                    xdr = stellar_user_sign(xdr, user_id, str(pin))
                    async with state.proxy() as data:
                        data[MyState.MyState.value] = '0'
                        data[MyState.xdr.value] = xdr
                    await cmd_show_sign(query.message.chat.id, state, f"Ваша транзакция c подписью: \n\n`{xdr}`\n\n",
                                        use_send=True)
            except Exception as ex:
                add_info_log('pin_state == 14', ex)
                await cmd_info_message(user_id, query.message.message_id, query.message.chat.id,
                                       'Ошибка при подписании, вероятно не правильный пароль. =(')
        if pin_state == 15:  # sign
            async with state.proxy() as data:
                data[MyState.pin.value] = ''
                data[MyState.StatePIN.value] = 0
                xdr = data.get(MyState.xdr.value)
            try:
                if user_id > 0:
                    xdr = stellar_user_sign(xdr, user_id, str(pin))
                    async with state.proxy() as data:
                        data[MyState.MyState.value] = '0'
                        data[MyState.xdr.value] = xdr
                    await cmd_info_message(user_id, query.message.message_id, query.message.chat.id,
                                           'Успешно подписано, пробуем отправить в блокчейн, ожидание до 5 минут')
                    stellar_send(xdr)
                    await cmd_info_message(user_id, query.message.message_id, query.message.chat.id,
                                           'Успешно отправлено')
                    await state.finish()
            except Exception as ex:
                add_info_log('pin_state == 15', ex)
                await cmd_info_message(user_id, query.message.message_id, query.message.chat.id,
                                       'Ошибка при подписании, вероятно не правильный пароль. =(')
        return True
