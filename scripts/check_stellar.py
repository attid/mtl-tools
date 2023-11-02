from utils.stellar_utils import *
import sys
from db.quik_pool import quik_pool


@logger.catch
def cmd_check_cron_transaction(session: Session):
    # logger.info('cmd_check_new_transaction')
    # by assets
    assets_config = [
        ['MMWB', BotValueTypes.LastMMWBTransaction, MTLChats.MMWBGroup, 0],
        ['FCM', BotValueTypes.LastFCMTransaction, MTLChats.FCMGroup, 0],
        # GDIE253MSIYMFUS3VHRGEQPIBG7VAIPSMATWLTBF73UPOLBUH5RV2FCM
        ['MTLand', BotValueTypes.LastMTLandTransaction, MTLChats.SignGroup, 10],
        ['MTL', BotValueTypes.LastMTLTransaction, MTLChats.SignGroup, 10],
        ['MTLRECT', BotValueTypes.LastRectTransaction, MTLChats.SignGroup, 10],
        ['EURMTL', BotValueTypes.LastEurTransaction, MTLChats.GuarantorGroup, 900],
        ['EURDEBT', BotValueTypes.LastDebtTransaction, MTLChats.GuarantorGroup, 0],
    ]
    for assets in assets_config:
        result = cmd_check_new_asset_transaction(session, asset_name=assets[0], save_id=assets[1], filter_sum=assets[3])
        if len(result) > 0:
            msg = f"Обнаружены новые операции для {assets[0]}\n"
            msg = msg + f'\n'.join(result)
            if len(msg) > 4096:
                db_cmd_add_message(session, assets[2], "Слишком много операций показаны первые ")
            db_cmd_add_message(session, assets[2], msg[0:4000])
    # FUND
    result = cmd_check_new_transaction(session, ignore_operation=['CreateClaimableBalance', 'SPAM'],
                                       stellar_address=MTLAddresses.public_issuer,
                                       value_id=BotValueTypes.LastFondTransaction)
    if len(result) > 0:
        db_cmd_add_message(session, MTLChats.SignGroup, "Получены новые транзакции")
        for transaction in result:
            msg = f'\n'.join(transaction)
            if len(msg) > 4096:
                db_cmd_add_message(session, MTLChats.SignGroup, "Слишком много операций показаны первые ")
            db_cmd_add_message(session, MTLChats.SignGroup, msg[0:4000])
    # DEFI
    asyncio.run(asyncio.sleep(10))
    result = cmd_check_new_transaction(session, ignore_operation=['CreateClaimableBalance', 'SPAM'],
                                       stellar_address=MTLAddresses.public_defi,
                                       value_id=BotValueTypes.LastDefiTransaction)
    if len(result) > 0:
        db_cmd_add_message(session, MTLChats.DefiGroup, "Получены новые транзакции")
        for transaction in result:
            msg = f'\n'.join(transaction)
            if len(msg) > 4096:
                db_cmd_add_message(session, MTLChats.DefiGroup, "Слишком много операций показаны первые ")
            db_cmd_add_message(session, MTLChats.DefiGroup, msg[0:4000])

    # USDM
    asyncio.run(asyncio.sleep(10))
    result = cmd_check_new_transaction(session, ignore_operation=['CreateClaimableBalance', 'SPAM'],
                                       stellar_address=MTLAddresses.public_usdm,
                                       value_id=BotValueTypes.LastUSDMFundTransaction)
    if len(result) > 0:
        db_cmd_add_message(session, MTLChats.USDMMGroup, "Получены новые транзакции")
        for transaction in result:
            msg = f'\n'.join(transaction)
            if len(msg) > 4096:
                db_cmd_add_message(session, MTLChats.USDMMGroup, "Слишком много операций показаны первые ")
            db_cmd_add_message(session, MTLChats.USDMMGroup, msg[0:4000])

    # FIN
    asyncio.run(asyncio.sleep(10))
    result = cmd_check_new_transaction(session, ignore_operation=['CreateClaimableBalance', 'SPAM'],
                                       stellar_address=MTLAddresses.public_fin,
                                       value_id=BotValueTypes.LastFINFundTransaction)
    if len(result) > 0:
        db_cmd_add_message(session, MTLChats.FinGroup, "Получены новые транзакции")
        for transaction in result:
            msg = f'\n'.join(transaction)
            if len(msg) > 4096:
                db_cmd_add_message(session, MTLChats.FinGroup, "Слишком много операций показаны первые ")
            db_cmd_add_message(session, MTLChats.FinGroup, msg[0:4000])
    # TFM
    asyncio.run(asyncio.sleep(10))
    result = cmd_check_new_transaction(session, ignore_operation=['CreateClaimableBalance', 'SPAM'],
                                       stellar_address=MTLAddresses.public_tfm,
                                       value_id=BotValueTypes.LastTFMFundTransaction)
    if len(result) > 0:
        db_cmd_add_message(session, MTLChats.FinGroup, "Получены новые транзакции")
        for transaction in result:
            msg = f'\n'.join(transaction)
            if len(msg) > 4096:
                db_cmd_add_message(session, MTLChats.FinGroup, "Слишком много операций показаны первые ")
            db_cmd_add_message(session, MTLChats.FinGroup, msg[0:4000])


@logger.catch
async def cmd_check_bot(session: Session):
    # balance Wallet
    balance = await get_balances(MTLAddresses.public_wallet)
    if int(balance['XLM']) < 100:
        db_cmd_add_message(session, MTLChats.SignGroup, 'Внимание Баланс MyMTLWallet меньше 100 !')

    # bot1
    now = datetime.now()
    for bot_address in exchange_bots:
        if bot_address == MTLAddresses.public_fire:
            dt = cmd_check_last_operation(bot_address)
            delta = now - dt
            if delta.days > 15:
                db_cmd_add_message(session, MTLChats.SignGroup,
                                f'Внимание по боту обмена {bot_address} нет операций {delta.days} дней !')
        elif bot_address == MTLAddresses.public_exchange_eurmtl_usdm:
            dt = cmd_check_last_operation(bot_address)
            delta = now - dt
            if delta.days > 3:
                db_cmd_add_message(session, MTLChats.SignGroup,
                                f'Внимание по боту обмена {bot_address} нет операций {delta.days} дней !')
        else:
            dt = cmd_check_last_operation(bot_address)
            delta = now - dt
            if delta.days > 0:
                db_cmd_add_message(session, MTLChats.SignGroup,
                                f'Внимание по боту обмена {bot_address} нет операций {delta.days} дней !')

    # key rate
    # dt = fb.execsql1('select max(t.dt_add) from t_keyrate t', [], datetime.now())
    # dt = datetime.combine(dt, datetime.min.time())
    # now = datetime.now()
    # delta = now - dt
    # if delta.days > 0:
    #    db_cmd_add_message(MTLChats.SignGroup, 'Внимание начислению key rate нет операций больше суток !')


@logger.catch
async def cmd_check_price(session: Session):
    # "message_id": 6568,  "chat": {"id": -1001707489173,
    cb_cb = Server(horizon_url="https://horizon.stellar.org").orderbook(MTLAssets.usdc_asset,
                                                                        MTLAssets.eurmtl_asset).limit(200).call()
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

    db_cmd_add_message(session, MTLChats.EURMTLClubGroup, '\n'.join(msg), False, 6568, json.dumps(bt))


if __name__ == "__main__":
    logger.add("check_stellar.log", rotation="1 MB")
    if 'check_transaction' in sys.argv:
        cmd_check_cron_transaction(quik_pool())
    elif 'check_bot' in sys.argv:
        asyncio.run(cmd_check_bot(quik_pool()))
    elif 'check_price' in sys.argv:
        asyncio.run(cmd_check_price(quik_pool()))
    else:
        print('need more parameters')
