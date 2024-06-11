import sys
import sentry_sdk
from db.quik_pool import quik_pool
from utils.stellar_utils import *


@logger.catch
def cmd_check_cron_transaction(session: Session):
    assets_config = [
        ['MMWB', BotValueTypes.LastMMWBTransaction, MTLChats.MMWBGroup, 0],
        ['FCM', BotValueTypes.LastFCMTransaction, MTLChats.FCMGroup, 0],
        ['MTLand', BotValueTypes.LastMTLandTransaction, MTLChats.SignGroup, 10],
        ['MTL', BotValueTypes.LastMTLTransaction, MTLChats.SignGroup, 10],
        ['MTLRECT', BotValueTypes.LastRectTransaction, MTLChats.SignGroup, 10],
        ['EURMTL', BotValueTypes.LastEurTransaction, MTLChats.GuarantorGroup, 900],
        ['EURDEBT', BotValueTypes.LastDebtTransaction, MTLChats.GuarantorGroup, 0]
    ]
    process_transactions_by_assets(session, assets_config)
    asyncio.run(asyncio.sleep(10))
    address_config = [
        # address, value_id, chat
        (MTLAddresses.public_issuer, BotValueTypes.LastFondTransaction, MTLChats.SignGroup),
        (MTLAddresses.public_farm, BotValueTypes.LastFarmTransaction, MTLChats.FARMGroup),
        (MTLAddresses.public_usdm, BotValueTypes.LastUSDMFundTransaction, MTLChats.USDMMGroup),
        (MTLAddresses.public_fin, BotValueTypes.LastFINFundTransaction, MTLChats.FinGroup),
        (MTLAddresses.public_tfm, BotValueTypes.LastTFMFundTransaction, MTLChats.FinGroup),
        (MTLAddresses.public_mtla, BotValueTypes.LastMTLATransaction, MTLChats.MTLAAgoraGroup)
    ]
    process_specific_transactions(session, address_config, ['CreateClaimableBalance', 'SPAM'])


def process_transactions_by_assets(session, assets_config):
    for asset in assets_config:
        result = cmd_check_new_asset_transaction(session, asset_name=asset[0], save_id=asset[1], filter_sum=asset[3])
        if result:
            result.insert(0, f"Обнаружены новые операции для {asset[0]}")
            send_message_4000(session, asset[2], result)


def process_specific_transactions(session, address_config, ignore_operations):
    for address, value_id, chat in address_config:
        results = cmd_check_new_transaction(session, ignore_operation=ignore_operations,
                                            stellar_address=address, value_id=value_id)
        if results:
            for result in results:
                result.insert(0, f"Получены новые транзакции")
                send_message_4000(session, chat, result)


def send_message_4000(session, chat_id, messages):
    msg = '\n'.join(messages)
    if len(msg) > 4096:
        msg = "Слишком много операций показаны первые . . . \n" + msg[:4000]
    db_cmd_add_message(session, chat_id, msg)


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

    # USDM order
    params = [
        (MTLAddresses.public_usdm, MTLAssets.usdc_asset, MTLAssets.usdm_asset, 3000),
        (MTLAddresses.public_usdm, MTLAssets.yusdc_asset, MTLAssets.usdm_asset, 5000),
        (MTLAddresses.public_usdm, MTLAssets.usdm_asset, MTLAssets.usdc_asset, 50000),
    ]

    for address, selling_asset, buying_asset, order_min_sum in params:
        order_sum = await stellar_get_orders_sum(address, selling_asset, buying_asset)
        if order_sum < order_min_sum:
            db_cmd_add_message(session, MTLChats.USDMMGroup, f'Внимание ордер {selling_asset.code}/{buying_asset.code} {order_sum} !')


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
    cb_cb = Server(horizon_url=config.horizon_url).orderbook(MTLAssets.usdc_asset,
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
    sentry_sdk.init(
        dsn=config.sentry_report_dsn,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )

    if 'check_transaction' in sys.argv:
        cmd_check_cron_transaction(quik_pool())
    elif 'check_bot' in sys.argv:
        asyncio.run(cmd_check_bot(quik_pool()))
    elif 'check_price' in sys.argv:
        pass
        # asyncio.run(cmd_check_price(quik_pool()))
    else:
        print('need more parameters')
