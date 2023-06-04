from stellar_sdk import exceptions
from mystellar import *
import sys

chat_id_test = -1001767165598
chat_id_signs = -1001239694752
chat_id_guarantors = -1001169382324
chat_id_defi = -1001876391583
chat_id_fcm = -1001637378851
chat_id_mmwb = -1001729647273


@logger.catch
def cmd_add_message(user_id, text, use_alarm=0):
    fb.execsql('insert into t_message (user_id, text, use_alarm) values (?,?,?)', (user_id, text, use_alarm))


@logger.catch
def cmd_check_cron_ledger():
    with suppress(NotFoundError, requests.exceptions.ConnectionError, exceptions.ConnectionError,
                  exceptions.BadResponseError, asyncio.exceptions.TimeoutError):
        asyncio.run(asyncio.wait_for(cmd_check_ledger(), timeout=55))


@logger.catch
def cmd_check_cron_transaction():
    # logger.info('cmd_check_new_transaction')
    # FUND
    result = cmd_check_new_transaction(ignore_operation=['CreateClaimableBalance'], stellar_address=public_issuer,
                                       value_id=BotValueTypes.LastFondTransaction)
    if len(result) > 0:
        cmd_add_message(chat_id_signs, "Получены новые транзакции")
        for transaction in result:
            msg = f'\n'.join(transaction)
            if len(msg) > 4096:
                cmd_add_message(chat_id_signs, "Слишком много операций показаны первые ")
            cmd_add_message(chat_id_signs, msg[0:4000])
    # DEFI
    result = cmd_check_new_transaction(ignore_operation=['CreateClaimableBalance'], stellar_address=public_defi,
                                       value_id=BotValueTypes.LastDefiTransaction)
    if len(result) > 0:
        cmd_add_message(chat_id_defi, "Получены новые транзакции")
        for transaction in result:
            msg = f'\n'.join(transaction)
            if len(msg) > 4096:
                cmd_add_message(chat_id_defi, "Слишком много операций показаны первые ")
            cmd_add_message(chat_id_defi, msg[0:4000])

    assets_config = [
        ['MMWB', BotValueTypes.LastMMWBTransaction, chat_id_mmwb, 0],
        ['FCM', BotValueTypes.LastFCMTransaction, chat_id_fcm, 0],
        # GDIE253MSIYMFUS3VHRGEQPIBG7VAIPSMATWLTBF73UPOLBUH5RV2FCM
        ['MTLand', BotValueTypes.LastMTLandTransaction, chat_id_signs, 10],
        ['MTL', BotValueTypes.LastMTLTransaction, chat_id_signs, 10],
        ['MTLRECT', BotValueTypes.LastRectTransaction, chat_id_signs, 10],
        ['EURMTL', BotValueTypes.LastEurTransaction, chat_id_guarantors, 900],
        ['EURDEBT', BotValueTypes.LastDebtTransaction, chat_id_guarantors, 0],
    ]
    for assets in assets_config:
        result = cmd_check_new_asset_transaction(asset_name=assets[0], save_id=assets[1], filter_sum=assets[3])
        if len(result) > 0:
            msg = f"Обнаружены новые операции для {assets[0]}\n"
            msg = msg + f'\n'.join(result)
            if len(msg) > 4096:
                cmd_add_message(assets[2], "Слишком много операций показаны первые ")
            cmd_add_message(assets[2], msg[0:4000])


@logger.catch
async def cmd_check_bot():
    # balance Wallet
    balance = await get_balances(public_wallet)
    if int(balance['XLM']) < 100:
        cmd_add_message(chat_id_signs, 'Внимание Баланс MyMTLWallet меньше 100 !')

    # bot1
    now = datetime.now()
    for bot_address in exchange_bots:
        if bot_address == public_fire:
            dt = cmd_check_last_operation(bot_address)
            delta = now - dt
            if delta.days > 15:
                cmd_add_message(chat_id_signs,
                                f'Внимание по боту обмена {bot_address} нет операций {delta.days} дней !')
        elif bot_address == public_exchange_eurmtl_usdc:
            dt = cmd_check_last_operation(bot_address)
            delta = now - dt
            if delta.days > 3:
                cmd_add_message(chat_id_signs,
                                f'Внимание по боту обмена {bot_address} нет операций {delta.days} дней !')
        else:
            dt = cmd_check_last_operation(bot_address)
            delta = now - dt
            if delta.days > 0:
                cmd_add_message(chat_id_signs,
                                f'Внимание по боту обмена {bot_address} нет операций {delta.days} дней !')

    # key rate
    # dt = fb.execsql1('select max(t.dt_add) from t_keyrate t', [], datetime.now())
    # dt = datetime.combine(dt, datetime.min.time())
    # now = datetime.now()
    # delta = now - dt
    # if delta.days > 0:
    #    cmd_add_message(chat_id_signs, 'Внимание начислению key rate нет операций больше суток !')


@logger.catch
async def cmd_check_price():
    # "message_id": 6568,  "chat": {"id": -1001707489173,
    cb_cb = Server(horizon_url="https://horizon.stellar.org").orderbook(usdc_asset, eurmtl_asset).limit(200).call()
    msg = ['Продают <b>EURMTL</b> за <b>USDC</b>']
    for idx, price in enumerate(cb_cb['bids']):
        if idx < 3:
            msg.append(f'{round(float(price["amount"]))} по {round(float(price["price"]), 3)}')
    msg.append('')
    msg.append('Покупают <b>EURMTL</b> за <b>USDC</b>')
    for idx, price in enumerate(cb_cb['asks']):
        if idx < 3:
            msg.append(f'{round(float(price["amount"]))} по {round(float(price["price"]), 3)}')

    bt = {'text': f'{round(float(cb_cb["bids"][0]["price"]), 3)}/{round(float(cb_cb["asks"][0]["price"]), 3)}',
          'link': 'https://stellar.expert/explorer/public/market/EURMTL-GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V/USDC-GA5ZSEJYB37JRC5AVCIA5MOP4RHTM335X2KGX3IHOJAPP5RE34K4KZVN'}
    msg.append('')
    rq = requests.get('https://api.binance.com/api/v3/ticker/price?symbol=EURUSDT').json()
    eur_cost = 1 / float(rq['price'])

    msg.append(f'Курс USD к EUR {round(eur_cost, 3)}')
    msg.append('Обновлено ' + datetime.now().strftime('%d.%m.%Y %H:%M:%S'))
    # print('\n'.join(msg))
    # print(bt)

    fb.execsql('insert into t_message (user_id, text, use_alarm, update_id, button_json) values (?,?,?,?,?)',
               (-1001707489173, '\n'.join(msg), False, 6568, json.dumps(bt)))


if __name__ == "__main__":
    logger.add("check_stellar.log", rotation="1 MB")

    if 'check_transaction' in sys.argv:
        cmd_check_cron_transaction()
    elif 'check_bot' in sys.argv:
        asyncio.run(cmd_check_bot())
    elif 'check_price' in sys.argv:
        asyncio.run(cmd_check_price())
    elif 'check_ledger' in sys.argv:
        cmd_check_cron_ledger()
    else:
        print('need more parameters')
