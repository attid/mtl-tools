from MyMTLWalletBot_handlers import *
from MyMTLWalletBot_main import change_user_lang
from stellar_sdk.exceptions import BadRequestError


def good_id(user_id, msg_id):
    last_message_id = get_last_message_id(user_id)
    logger.info(['good_id', last_message_id])
    if msg_id == last_message_id:
        return True
    elif last_message_id == 0:
        return True
    else:
        return False


@dp.callback_query_handler(cb_add.filter())
async def cq_add(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    logger.info(f'{query.from_user.id}, {callback_data}')
    if not good_id(query.from_user.id, query.message.message_id):
        await query.answer("Old button =(", show_alert=True)
        return True

    answer = callback_data["answer"]
    user_id = query.from_user.id
    if answer == MyButtons.HaveKey.value:  # have key
        await cmd_show_add_wallet_private(query.message.chat.id, state)
    elif answer == MyButtons.NewKey.value:  # new
        if stellar_can_new(user_id):
            stellar_create_new(query.from_user.id, query.from_user.username)
            await cmd_show_start(query.message.chat.id, state)
        else:
            await query.answer(my_gettext(query.message.chat.id, "max_wallets"), show_alert=True)
    else:
        await query.answer("Bad answer!", show_alert=True)
    return True


@dp.callback_query_handler(cb_default.filter())
async def cq_def(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    logger.info([query.from_user.id, callback_data])
    if not good_id(query.from_user.id, query.message.message_id):
        await query.answer("Old button =(", show_alert=True)
        return True

    answer = callback_data["answer"]
    user_id = query.from_user.id

    if answer == MyButtons.Receive.value:  # receive
        msg = my_gettext(query.message.chat.id, "my_address").format(
            stellar_get_user_account(user_id).account.account_id)
        send_file = f'qr/{stellar_get_user_account(user_id).account.account_id}.png'
        qr = pyqrcode.create(stellar_get_user_account(user_id).account.account_id)
        qr.png(send_file, scale=6)

        await cmd_info_message(query.message.chat.id, msg, state, send_file=send_file)
        # await query.message.edit_text(msg, reply_markup=1)
    elif answer == MyButtons.Send.value:  # Send
        await cmd_send_01(query.message.chat.id, state)

    elif answer == MyButtons.Setting.value:
        await cmd_setting(query.message.chat.id, state)
    elif answer == MyButtons.WalletSetting.value:
        await cmd_wallet_setting(query.message.chat.id, state)
    elif answer == MyButtons.AddNew.value:
        await cmd_show_create(query.message.chat.id, get_kb_add1(query.from_user.id))
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
            await cmd_info_message(query.message.chat.id, my_gettext(query.message.chat.id, "resend"), state)
            stellar_send(xdr)
            await cmd_info_message(query.message.chat.id,
                                   my_gettext(query.message.chat.id, "send_good"), state)
        except BaseHorizonError as ex:
            logger.info(['ReSend BaseHorizonError', ex])
            msg = f"{ex.title}, error {ex.status}"
            await cmd_info_message(query.message.chat.id, f"{my_gettext(query.message.chat.id, 'send_error')}\n{msg}",
                                   state,
                                   resend_transaction=True)
        except Exception as ex:
            logger.info(['ReSend unknown error', ex])
            msg = 'unknown error'
            async with state.proxy() as data:
                data[MyState.xdr.value] = xdr
            await cmd_info_message(query.message.chat.id, f"{my_gettext(query.message.chat.id, 'send_error')}\n{msg}",
                                   state,
                                   resend_transaction=True)
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
    elif answer == MyButtons.AddAsset.value:
        await cmd_add_asset(query.message.chat.id, state)
    elif answer == MyButtons.Support.value:
        await cmd_info_message(query.message.chat.id, my_gettext(query.message.chat.id, "support_bot"), state)
    elif answer == MyButtons.ChangeLang.value:
        change_user_lang(query.message.chat.id)
        await cmd_wallet_setting(query.message.chat.id, state)
    elif answer == MyButtons.Market.value:
        await send_message(query.message.chat.id, my_gettext(query.message.chat.id, 'kb_market'),
                           reply_markup=get_kb_market(query.message.chat.id))
    elif answer == MyButtons.NewOrder.value:
        await cmd_sale_01(query.message.chat.id, state)
    elif answer == MyButtons.ShowOrders.value:
        await cmd_show_orders(query.message.chat.id, state)
    elif answer == MyButtons.EditOrderCost.value:
        await cmd_edit_order_price(query.message.chat.id, state)
    elif answer == MyButtons.EditOrderAmount.value:
        await cmd_edit_order_amount(query.message.chat.id, state)
    elif answer == MyButtons.DeleteOrder.value:
        await cmd_delete_order(query.message.chat.id, state)
    elif answer == MyButtons.NotImplemented.value:
        await query.answer(my_gettext(query.message.chat.id, "not_implemented"), show_alert=True)
    else:
        await query.answer("Bad answer!", show_alert=True)
    return True


@dp.callback_query_handler(cb_send_1.filter())
async def cq_send1(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    logger.info(f'{query.from_user.id}, {callback_data}')
    if not good_id(query.from_user.id, query.message.message_id):
        await query.answer("Old button =(", show_alert=True)
        return True

    answer = callback_data["answer"]
    async with state.proxy() as data:
        logger.info(f'**** call , {data}')
        asset_list: List[Balance] = data[MyState.assets.value]
    for asset in asset_list:
        if asset.asset_code == answer:
            if float(asset.balance) == 0.0:
                await query.answer(my_gettext(query.message.chat.id, "zero_sum"), show_alert=True)
            else:
                async with state.proxy() as data:
                    data[MyState.send_asset_code.value] = asset.asset_code
                    data[MyState.send_asset_issuer.value] = asset.asset_issuer
                    data[MyState.send_asset_max_sum.value] = asset.balance
                await cmd_send_03(query.message.chat.id, state)

    return True


@dp.callback_query_handler(cb_send_xdr.filter())
async def cq_send4(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    logger.info(f'{query.from_user.id}, {callback_data}')
    if not good_id(query.from_user.id, query.message.message_id):
        await query.answer("Old button =(", show_alert=True)
        return True

    answer = callback_data["answer"]
    if answer == MyButtons.Yes.value:
        async with state.proxy() as data:
            data[MyState.StatePIN.value] = 15
        await cmd_ask_pin(query.message.chat.id, state)
    elif answer == MyButtons.Return.value:  #
        await cmd_show_start(query.message.chat.id, state)
    else:
        await query.answer("Bad answer!", show_alert=True)
    return True


@dp.callback_query_handler(cb_swap_1.filter())
async def cq_swap1(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    logger.info(f'{query.from_user.id}, {callback_data}')
    if not good_id(query.from_user.id, query.message.message_id):
        await query.answer("Old button =(", show_alert=True)
        return True

    answer = callback_data["answer"]
    async with state.proxy() as data:
        asset_list: List[Balance] = data[MyState.assets.value]
    for asset in asset_list:
        if asset.asset_code == answer:
            if float(asset.balance) == 0.0:
                await query.answer(my_gettext(query.message.chat.id, "zero_sum"), show_alert=True)
            else:
                async with state.proxy() as data:
                    data[MyState.send_asset_code.value] = asset.asset_code
                    data[MyState.send_asset_issuer.value] = asset.asset_issuer
                    data[MyState.send_asset_max_sum.value] = asset.balance
                await cmd_swap_02(query.message.chat.id, state)

    return True


@dp.callback_query_handler(cb_swap_2.filter())
async def cq_swap2(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    logger.info(f'{query.from_user.id}, {callback_data}')
    if not good_id(query.from_user.id, query.message.message_id):
        await query.answer("Old button =(", show_alert=True)
        return True

    answer = callback_data["answer"]
    async with state.proxy() as data:
        asset_list: List[Balance] = data[MyState.assets.value]
    for asset in asset_list:
        if asset.asset_code == answer:
            async with state.proxy() as data:
                data[MyState.receive_asset_code.value] = asset.asset_code
                data[MyState.receive_asset_issuer.value] = asset.asset_issuer
                data[MyState.receive_asset_min_sum.value] = asset.balance
            await cmd_swap_03(query.message.chat.id, state)

    return True


@dp.callback_query_handler(cb_sale_1.filter())
async def cq_sale1(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    logger.info(f'{query.from_user.id}, {callback_data}')
    if not good_id(query.from_user.id, query.message.message_id):
        await query.answer("Old button =(", show_alert=True)
        return True

    answer = callback_data["answer"]
    async with state.proxy() as data:
        asset_list: List[Balance] = data[MyState.assets.value]
    for asset in asset_list:
        if asset.asset_code == answer:
            if float(asset.balance) == 0.0:
                await query.answer(my_gettext(query.message.chat.id, "zero_sum"), show_alert=True)
            else:
                async with state.proxy() as data:
                    data[MyState.send_asset_code.value] = asset.asset_code
                    data[MyState.send_asset_issuer.value] = asset.asset_issuer
                    data[MyState.send_asset_max_sum.value] = asset.balance
                await cmd_sale_02(query.message.chat.id, state)

    return True


@dp.callback_query_handler(cb_sale_2.filter())
async def cq_sale2(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    logger.info(f'{query.from_user.id}, {callback_data}')
    if not good_id(query.from_user.id, query.message.message_id):
        await query.answer("Old button =(", show_alert=True)
        return True

    answer = callback_data["answer"]
    async with state.proxy() as data:
        asset_list: List[Balance] = data[MyState.assets.value]
    for asset in asset_list:
        if asset.asset_code == answer:
            async with state.proxy() as data:
                data[MyState.receive_asset_code.value] = asset.asset_code
                data[MyState.receive_asset_issuer.value] = asset.asset_issuer
                data[MyState.receive_asset_min_sum.value] = asset.balance
            await cmd_sale_03(query.message.chat.id, state)

    return True


@dp.callback_query_handler(cb_setting.filter())
async def cq_setting(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    logger.info(f'{query.from_user.id}, {callback_data}')
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
            msg = f"{wallets[idx][0]}\n" + my_gettext(query.message.chat.id, 'your_balance') + stellar_get_balance_str(
                user_id, wallets[idx][0])
            await query.answer(msg[:200], show_alert=True)
    return True


@dp.callback_query_handler(cb_pin.filter())
async def cq_pin(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    logger.info(f'{query.from_user.id}, *')
    if not good_id(query.from_user.id, query.message.message_id):
        await query.answer("Old button =(", show_alert=True)
        return True

    answer = callback_data["answer"]
    user_id = query.from_user.id
    async with state.proxy() as data:
        pin = data.get(MyState.pin.value, '')
        pin_state = data.get(MyState.StatePIN.value, 1)
    logger.info(f'{query.from_user.id}, 1')
    if answer in '1234567890ABCDEF':
        pin += answer
        async with state.proxy() as data:
            data[MyState.pin.value] = pin
        logger.info(f'{query.from_user.id}, 2')
        await cmd_ask_pin(query.message.chat.id, state)
    logger.info(f'{query.from_user.id}, 3')

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
            await cmd_ask_pin(query.message.chat.id, state, my_gettext(query.message.chat.id, "resend_password"))
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
                await query.answer(my_gettext(query.message.chat.id, "bad_passwords"), show_alert=True)
        if pin_state == 13:  # send
            async with state.proxy() as data:
                data[MyState.pin.value] = ''
                data[MyState.StatePIN.value] = 0
                if data.get(MyState.MyState.value) == MyState.StateActivateConfirm.value:
                    send_address = data.get(MyState.send_address.value)
                    create = True
                if data.get(MyState.MyState.value) == MyState.StateSendConfirm.value:
                    send_address = data.get(MyState.send_address.value)
                    create = False
                send_asset_code = data.get(MyState.send_asset_code.value)
                send_asset_issuer = data.get(MyState.send_asset_issuer.value)
                send_sum = data.get(MyState.send_sum.value)
            try:
                xdr = stellar_pay(stellar_get_user_account(user_id).account.account_id,
                                  send_address,
                                  Asset(send_asset_code, send_asset_issuer), send_sum, create=create)
                if user_id > 0:
                    xdr = stellar_sign(xdr, stellar_get_user_keypair(user_id, str(pin)).secret)
                    async with state.proxy() as data:
                        data[MyState.xdr.value] = xdr
                    await cmd_info_message(query.message.chat.id,
                                           my_gettext(query.message.chat.id, "try_send"),
                                           state)
                    stellar_send(xdr)
                    await cmd_info_message(query.message.chat.id,
                                           my_gettext(query.message.chat.id, "send_good"), state)
                    await state.finish()
            except BaseHorizonError as ex:
                # logger.info('pin_state == 13 BaseHorizonError', ex)
                msg = f"{ex.title}, error {ex.status}"
                logger.info(['pin_state == 13', msg])
                await cmd_info_message(query.message.chat.id,
                                       f"{my_gettext(query.message.chat.id, 'send_error')}\n{msg}", state,
                                       resend_transaction=True)
            except Exception as ex:
                logger.info(['pin_state == 13 unknown error', ex])
                msg = 'unknown error'
                await cmd_info_message(query.message.chat.id,
                                       f"{my_gettext(query.message.chat.id, 'send_error')}\n{msg}", state,
                                       resend_transaction=True)
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
                    await cmd_show_sign(query.message.chat.id, state,
                                        my_gettext(query.message.chat.id, "your_xdr").format(xdr),
                                        use_send=True)
            except BaseHorizonError as ex:
                # logger.info(['pin_state == 13 BaseHorizonError', ex])
                msg = f"{ex.title}, error {ex.status}"
                logger.info(['pin_state == 14', msg])
                await cmd_info_message(query.message.chat.id,
                                       f"{my_gettext(query.message.chat.id, 'send_error')}\n{msg}", state)
            except Exception as ex:
                logger.info(['pin_state == 14', ex])
                await cmd_info_message(query.message.chat.id,
                                       my_gettext(query.message.chat.id, "bad_password"), state)
        if pin_state == 15:  # sign and send
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
                    await cmd_info_message(query.message.chat.id,
                                           my_gettext(query.message.chat.id, "try_send"),
                                           state)
                    stellar_send(xdr)
                    await cmd_info_message(query.message.chat.id, my_gettext(query.message.chat.id, "send_good"), state)
                    await state.finish()
            except BadRequestError as ex:
                # print(ex.extras.get("result_codes", '=( eror not found'))
                msg = f"{ex.title}, error {ex.status}, {ex.extras.get('result_codes', 'no extras')}"
                logger.info(['pin_state == 15, first', msg])
                await cmd_info_message(query.message.chat.id,
                                       f"{my_gettext(query.message.chat.id, 'send_error')}\n{msg}", state)
            except BaseHorizonError as ex:
                msg = f"{ex.title}, error {ex.status}, {ex.extras.get('result_codes', 'no extras')}"
                logger.info(['pin_state == 15', msg])
                await cmd_info_message(query.message.chat.id,
                                       f"{my_gettext(query.message.chat.id, 'send_error')}\n{msg}", state)
            except Exception as ex:
                logger.info(['pin_state == 15', ex])
                await cmd_info_message(query.message.chat.id, my_gettext(query.message.chat.id, "bad_password"), state)
        return True


@dp.callback_query_handler(cb_assets.filter())
async def cq_setting(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    logger.info(f'{query.from_user.id}, {callback_data}')
    if not good_id(query.from_user.id, query.message.message_id):
        await query.answer("Old button =(", show_alert=True)
        return True

    answer = callback_data["answer"]
    # user_id = query.from_user.id
    if answer == MyButtons.DeleteAsset.value:
        await cmd_add_asset_del(query.from_user.id, state)
    elif answer == MyButtons.AddAsset.value:
        await cmd_add_asset_add(query.from_user.id, state)
    elif answer == MyButtons.AddAssetExpert.value:
        await cmd_add_asset_expert(query.from_user.id, state)
    else:
        await query.answer("Bad answer!", show_alert=True)
    return True


@dp.callback_query_handler(cb_add_asset.filter())
async def cq_add_asset(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    logger.info(f'{query.from_user.id}, {callback_data}')
    if not good_id(query.from_user.id, query.message.message_id):
        await query.answer("Old button =(", show_alert=True)
        return True

    answer = callback_data["answer"]
    async with state.proxy() as data:
        asset_list: List[Balance] = data[MyState.assets.value]

    asset = list(filter(lambda x: x.asset_code == answer, asset_list))
    if asset:
        async with state.proxy() as data:
            data[MyState.send_asset_code.value] = asset[0].asset_code
            data[MyState.send_asset_issuer.value] = asset[0].asset_issuer
        await cmd_add_asset_end(query.message.chat.id, state)
    else:
        await query.answer(my_gettext(query.message.chat.id, "bad_data"), show_alert=True)
        logger.info(f'error add asset {query.from_user.id} {answer}')

    return True


@dp.callback_query_handler(cb_del_asset.filter())
async def cq_del_asset(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    logger.info(f'{query.from_user.id}, {callback_data}')
    if not good_id(query.from_user.id, query.message.message_id):
        await query.answer("Old button =(", show_alert=True)
        return True

    answer = callback_data["answer"]
    async with state.proxy() as data:
        asset_list: List[Balance] = data[MyState.assets.value]

    asset = list(filter(lambda x: x.asset_code == answer, asset_list))
    if asset:
        async with state.proxy() as data:
            data[MyState.send_asset_code.value] = asset[0].asset_code
            data[MyState.send_asset_issuer.value] = asset[0].asset_issuer
        await cmd_del_asset_end(query.message.chat.id, state)
    else:
        await query.answer(my_gettext(query.message.chat.id, "bad_data"), show_alert=True)
        logger.info(f'error add asset {query.from_user.id} {answer}')

    return True


@dp.callback_query_handler(cb_edit_order.filter())
async def cq_edit_order(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    logger.info(f'{query.from_user.id}, {callback_data}')
    if not good_id(query.from_user.id, query.message.message_id):
        await query.answer("Old button =(", show_alert=True)
        return True

    answer = callback_data["answer"]
    async with state.proxy() as data:
        data[MyState.edit_offer_id.value] = answer
        # asset_list: List[MyOffer] = data[MyState.offers.value]

    await cmd_edit_order(query.message.chat.id, state)

    return True
