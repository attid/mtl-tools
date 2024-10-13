import json
import sys
import sentry_sdk
from db.quik_pool import quik_pool
from utils.grist_tools import load_notify_info_accounts, load_notify_info_assets, put_grist_data, grist_main_chat_info
from utils.stellar_utils import *


@logger.catch
async def cmd_check_cron_transaction(session: Session):
    assets_config = await load_notify_info_assets()
    await process_transactions_by_assets(session, assets_config)
    address_config = await load_notify_info_accounts()
    await process_specific_transactions(session, address_config, ['CreateClaimableBalance', 'SPAM'])


async def process_transactions_by_assets(session, assets_config):
    for asset_config in assets_config:
        # [{'chat_id': '-1001729647273', 'chat_info': 'MMWBGroup', 'min': 0, 'asset': 'MMWB-GBSNN2SPYZB2A5RPDTO3BLX4TP5KNYI7UMUABUS3TYWWEWAAM2D7CMMW'},
        asset = asset_config['asset']
        asset_name = asset.split('-')[0]

        result = await cmd_check_new_asset_transaction(session, asset=asset, filter_sum=int(asset_config['min']),
                                                       chat_id=asset_config['chat_id'])

        if result:
            result.insert(0, f"Обнаружены новые операции для {asset_name}")
            send_message_4000(session, int(asset_config['chat_id']), result)


async def process_specific_transactions(session, address_config, ignore_operations):
    # {'chat_id': '-1001239694752', 'account_id': 'GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V', 'chat_info': 'SignGroup', 'account_info': 'public_issuer'}
    cash = {}
    for address in address_config:
        account_id = address['account_id']
        results = await cmd_check_new_transaction(ignore_operation=ignore_operations,
                                                  account_id=account_id,
                                                  cash=cash, chat_id=address['chat_info'])
        if results:
            for result in results:
                result.insert(0, f"Получены новые транзакции")
                send_message_4000(session, int(address['chat_id']), result)
        await asyncio.sleep(3)


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
            db_cmd_add_message(session, MTLChats.USDMMGroup,
                               f'Внимание ордер {selling_asset.code}/{buying_asset.code} {order_sum} !')

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


async def grist_upload_users(table, data):
    json_data = {"records": []}
    if data:
        for user in data:
            json_data['records'].append({
                "require": {
                    "user_id": user.user_id
                },
                "fields": {
                    "user_id": user.user_id,
                    "username": user.username,
                    "full_name": user.full_name,
                    "income_at": user.created_at.strftime('%d.%m.%Y %H:%M:%S'),
                    "left_at": user.left_at.strftime('%d.%m.%Y %H:%M:%S') if user.left_at else None
                }
            })

        await put_grist_data(grist=grist_main_chat_info,
                             table_name='Main_chat_income',
                             json_data=json_data)


async def cmd_check_grist():
    data = await global_data.mongo_config.get_users_joined_last_day(-1001009485608)
    await grist_upload_users('Main_chat_income', data)
    data = await global_data.mongo_config.get_users_left_last_day(-1001009485608)
    await grist_upload_users('Main_chat_outcome', data)


if __name__ == "__main__":
    logger.add("logs/check_stellar.log", rotation="1 MB")
    sentry_sdk.init(
        dsn=config.sentry_report_dsn,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )

    if 'check_transaction' in sys.argv:
        # pass
        asyncio.run(cmd_check_cron_transaction(quik_pool()))
    elif 'check_bot' in sys.argv:
        asyncio.run(cmd_check_bot(quik_pool()))
    elif 'check_grist' in sys.argv:
        pass
        asyncio.run(cmd_check_grist())
    else:
        print('need more parameters')
