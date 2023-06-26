import asyncio
from utils.stellar_utils import *
from db.quik_pool import quik_pool

max_eurmtl = 10000.0  # max offer
max_btcmtl = 0.1  # max offer
max_satsmtl = 1000000  # max offer
sats_cost = 100000000

min_xlm = 50.0
persent_eurmtl = 1.03  # 1.03 =  5% наценки
persent_btc = 1.01  #
persent_xlm = 1.002  #
persent_usdc = 1.002  # 0.975 for fund exchange
persent_cost = 1.01  # 1% изменения цены для обновления
persent_btc_cost = 1.001  # 0,1% изменения цены для обновления

server = Server(horizon_url="https://horizon.stellar.org")


# server = Server(horizon_url="http://158.58.231.224:8000/")
# server = Server(horizon_url="https://horizon.publicnode.org")


def get_offers(address: str):
    call = server.offers().for_account(address).limit(200).call()

    records = {}
    for record in call['_embedded']['records']:
        selling_name = 'XLM' if record["selling"]["asset_type"] == 'native' else record["selling"]["asset_code"]
        buying_name = 'XLM' if record["buying"]["asset_type"] == 'native' else record["buying"]["asset_code"]
        records[f'{selling_name}-{buying_name}'] = record

    return records


@logger.catch
async def update_offer(account_key, price_min, price_max, price, selling_asset, buying_asset, amount,
                       check_persent, record):
    test_record = {'id': '1086147610', 'paging_token': '1086147610',
                   'seller': 'GCVF74HQRLPAGTPFSYUAKGHSDSMBQTMVSLKWKUU65ULEN7TL4N56IPZ7',
                   'selling': {'asset_type': 'native'},
                   'buying': {'asset_type': 'credit_alphanum12', 'asset_code': 'EURMTL',
                              'asset_issuer': 'GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V'},
                   'amount': '20000.0000000', 'price_r': {'n': 557511, 'd': 5000000},
                   'price': '0.1115022', 'last_modified_ledger': 43210436,
                   'last_modified_time': '2022-10-21T08:15:53Z'}
    account = server.load_account(account_key)
    offer_id = int(record["id"]) if record else 0
    current_amount = float(record["amount"]) if record else 0
    current_price = float(record["price_r"]['n']) / float(record["price_r"]['d']) if record else 0

    stellar_transaction = None
    # if offer and bad price need zero offer
    if (price > price_max) or (price < price_min):
        if offer_id > 0:
            logger.info(f'need cancel {selling_asset.code} for {buying_asset.code} price {price} amount {amount}')
            stellar_transaction = TransactionBuilder(source_account=account,
                                                     network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                                     base_fee=base_fee)
            stellar_transaction.append_manage_sell_offer_op(selling=selling_asset, buying=buying_asset, amount='0',
                                                            price=Price.from_raw_price('1'), offer_id=offer_id)
    elif (amount > 0) and (price > 0) and (
            (price > current_price * check_persent) or (price * check_persent < current_price) or
            (amount > current_amount * 1.1) or (amount * 1.1 < current_amount)):
        logger.info(f'need sale {selling_asset.code} for {buying_asset.code} price {price} amount {amount}')
        stellar_transaction = TransactionBuilder(source_account=account,
                                                 network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                                 base_fee=base_fee)
        stellar_transaction.append_manage_sell_offer_op(selling=selling_asset, buying=buying_asset, amount=str(amount),
                                                        price=Price.from_raw_price(str(price)), offer_id=offer_id)
    if stellar_transaction:
        stellar_transaction.set_timeout(250)
        stellar_transaction = stellar_transaction.build()
        stellar_transaction.sign(get_private_sign())
        xdr = stellar_transaction.to_xdr()
        logger.info(f"xdr: {xdr}")

        server.submit_transaction(stellar_transaction)


@logger.catch
def fire_mtl(account, amount):
    stellar_transaction = TransactionBuilder(source_account=account,
                                             network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                             base_fee=base_fee)
    stellar_transaction.append_payment_op(destination=MTLAssets.mtl_asset.issuer, asset=MTLAssets.mtl_asset,
                                          amount=str(amount))
    stellar_transaction = stellar_transaction.build()
    stellar_transaction.sign(get_private_sign())
    xdr = stellar_transaction.to_xdr()
    logger.info(f"xdr: {xdr}")

    server.submit_transaction(stellar_transaction)


@logger.catch
async def check_exchange():
    # account_exchange = server.load_account(public_exchange)
    # get balance
    balances_eurmtl_xlm = await get_balances(MTLAddresses.public_exchange_eurmtl_xlm)
    balances_eurmtl_btc = await get_balances(MTLAddresses.public_exchange_eurmtl_btc)
    balances_eurmtl_sats = await get_balances(MTLAddresses.public_exchange_eurmtl_sats)
    balances_eurmtl_usdc = await get_balances(MTLAddresses.public_exchange_eurmtl_usdc)

    sum_eurmtl_xlm = float(balances_eurmtl_xlm['EURMTL'])
    sum_xlm = float(balances_eurmtl_xlm['XLM'])
    sum_btcmtl = float(balances_eurmtl_btc['BTCMTL'])
    sum_eurmtl_btc = float(balances_eurmtl_btc['EURMTL'])
    sum_satsmtl_eur = float(balances_eurmtl_sats['SATSMTL'])
    sum_eurmtl_sats = float(balances_eurmtl_sats['EURMTL'])
    sum_eurmtl_usdc = float(balances_eurmtl_usdc['EURMTL'])
    sum_usdc = float(balances_eurmtl_usdc['USDC'])

    # get offers
    offers_eurmtl_xlm = get_offers(MTLAddresses.public_exchange_eurmtl_xlm)
    offers_eurmtl_btc = get_offers(MTLAddresses.public_exchange_eurmtl_btc)
    offers_eurmtl_sats = get_offers(MTLAddresses.public_exchange_eurmtl_sats)
    offers_eurmtl_usdc = get_offers(MTLAddresses.public_exchange_eurmtl_usdc)

    # EUR cost
    rq = requests.get('https://api.binance.com/api/v3/ticker/price?symbol=EURUSDT').json()
    eur_cost = 1 / float(rq['price'])

    rq = requests.get('https://api.binance.com/api/v3/ticker/price?symbol=XLMUSDT').json()
    stl = 1 / float(rq['price'])
    cost_eurmtl = stl / eur_cost

    rq = requests.get('https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT').json()
    cost_btc = float(rq['price']) * eur_cost
    logger.info(['eur_cost', eur_cost, 'xlm_cost', cost_eurmtl, cost_eurmtl * persent_eurmtl, 'btc_cost', cost_btc])

    sum_eurmtl_xlm = int(sum_eurmtl_xlm) if sum_eurmtl_xlm < max_eurmtl else max_eurmtl
    sum_eurmtl_btc = int(sum_eurmtl_btc) if sum_eurmtl_btc < max_eurmtl else max_eurmtl

    sum_btcmtl = sum_btcmtl if sum_btcmtl < max_btcmtl else max_btcmtl
    max_xlm = int(max_eurmtl * cost_eurmtl / 1000) * 1000
    sum_xlm = int(sum_xlm) if sum_xlm < max_xlm else max_xlm
    sum_xlm -= min_xlm

    sum_satsmtl_eur = int(sum_satsmtl_eur) if sum_satsmtl_eur < max_satsmtl else max_satsmtl
    sum_eurmtl_sats = int(sum_eurmtl_sats) if sum_eurmtl_sats < max_eurmtl else max_eurmtl
    sum_eurmtl_usdc = int(sum_eurmtl_usdc) if sum_eurmtl_usdc < max_eurmtl else max_eurmtl
    sum_usdc = int(sum_usdc) if sum_usdc < max_eurmtl else max_eurmtl

    await update_offer(account_key=MTLAddresses.public_exchange_eurmtl_xlm, price_min=5, price_max=15,
                       price=cost_eurmtl * persent_eurmtl,
                       selling_asset=MTLAssets.eurmtl_asset, buying_asset=MTLAssets.xlm_asset, amount=sum_eurmtl_xlm,
                       check_persent=persent_cost,
                       record=offers_eurmtl_xlm.get('EURMTL-XLM'))

    await update_offer(account_key=MTLAddresses.public_exchange_eurmtl_xlm, price_min=1 / 15, price_max=1 / 5,
                       price=round((1 / cost_eurmtl) * persent_xlm, 5),
                       selling_asset=MTLAssets.xlm_asset, buying_asset=MTLAssets.eurmtl_asset, amount=sum_xlm,
                       check_persent=persent_cost,
                       record=offers_eurmtl_xlm.get('XLM-EURMTL'))

    # btc
    await update_offer(account_key=MTLAddresses.public_exchange_eurmtl_btc, price_min=15000, price_max=30000,
                       price=round(cost_btc * persent_btc),
                       selling_asset=MTLAssets.btcmtl_asset, buying_asset=MTLAssets.eurmtl_asset, amount=sum_btcmtl,
                       check_persent=persent_btc_cost, record=offers_eurmtl_btc.get('BTCMTL-EURMTL'))

    await update_offer(account_key=MTLAddresses.public_exchange_eurmtl_btc, price_min=1 / 30000, price_max=1 / 15000,
                       price=round((1 / cost_btc) * persent_btc, 7),
                       selling_asset=MTLAssets.eurmtl_asset, buying_asset=MTLAssets.btcmtl_asset, amount=sum_eurmtl_btc,
                       check_persent=persent_btc_cost, record=offers_eurmtl_btc.get('EURMTL-BTCMTL'))

    # sats
    await update_offer(account_key=MTLAddresses.public_exchange_eurmtl_sats, price_min=15000 / sats_cost,
                       price_max=30000 / sats_cost,
                       price=round(cost_btc * persent_btc / sats_cost, 8),
                       selling_asset=MTLAssets.satsmtl_asset, buying_asset=MTLAssets.eurmtl_asset,
                       amount=sum_satsmtl_eur,
                       check_persent=persent_btc_cost, record=offers_eurmtl_sats.get('SATSMTL-EURMTL'))

    await update_offer(account_key=MTLAddresses.public_exchange_eurmtl_sats, price_min=1 / 30000 * sats_cost,
                       price_max=1 / 15000 * sats_cost,
                       price=round(1 / cost_btc * sats_cost * persent_btc),
                       selling_asset=MTLAssets.eurmtl_asset, buying_asset=MTLAssets.satsmtl_asset,
                       amount=sum_eurmtl_sats,
                       check_persent=persent_btc_cost, record=offers_eurmtl_sats.get('EURMTL-SATSMTL'))

    # eurmtl 2 usdc
    await update_offer(account_key=MTLAddresses.public_exchange_eurmtl_usdc, price_min=0.8, price_max=1.3,
                       price=round(1 / eur_cost * persent_eurmtl, 4),
                       selling_asset=MTLAssets.eurmtl_asset, buying_asset=MTLAssets.usdc_asset, amount=sum_eurmtl_usdc,
                       check_persent=persent_cost,
                       record=offers_eurmtl_usdc.get('EURMTL-USDC'))
    await update_offer(account_key=MTLAddresses.public_exchange_eurmtl_usdc, price_min=0.8, price_max=1.3,
                       price=round(eur_cost * persent_usdc, 4),
                       selling_asset=MTLAssets.usdc_asset, buying_asset=MTLAssets.eurmtl_asset, amount=sum_usdc,
                       check_persent=persent_cost,
                       record=offers_eurmtl_usdc.get('USDC-EURMTL'))

    # # update_offer(account=account_exchange, price_min=15000 * cost_eurmtl, price_max=1 * cost_eurmtl,
    # #             price=round(cost_btc * cost_eurmtl * persent_btc),
    # #             selling_asset=asset_btcmtl, buying_asset=asset_xlm, amount=sum_btcmtl, check_persent=persent_cost,
    # #             record=records.get('BTCMTL-XLM'))


@logger.catch
async def check_fire(cost_fire):
    account_fire = server.load_account(MTLAddresses.public_fire)
    # get balance
    balances = await get_balances(MTLAddresses.public_fire)

    sum_eurmtl = float(balances['EURMTL'])
    sum_mtl = float(balances['MTL'])
    logger.info(['fire', 'sum_eurmtl', sum_eurmtl, 'sum_mtl', sum_mtl])

    # get offers
    rq = requests.get(f'https://horizon.stellar.org/accounts/{MTLAddresses.public_fire}/offers').json()
    # print(json.dumps(rq["_embedded"]["records"], indent=4))
    records = {}
    if len(rq["_embedded"]["records"]) > 0:
        for record in rq["_embedded"]["records"]:
            selling_name = 'XLM' if record["selling"]["asset_type"] == 'native' else record["selling"]["asset_code"]
            buying_name = 'XLM' if record["buying"]["asset_type"] == 'native' else record["buying"]["asset_code"]
            records[f'{selling_name}-{buying_name}'] = record

    await update_offer(account_key=account_fire.account, price_min=0.3, price_max=1, price=round(1 / cost_fire, 5),
                       selling_asset=MTLAssets.eurmtl_asset, buying_asset=MTLAssets.mtl_asset, amount=sum_eurmtl,
                       check_persent=1.01,
                       record=records.get('EURMTL-MTL'))

    if sum_mtl > 0:
        fire_mtl(account_fire, sum_mtl)


def move_usdc():
    # swap usdc - xlm
    account = server.load_account(MTLAddresses.public_exchange_eurmtl_usdc)
    stellar_transaction = TransactionBuilder(source_account=account,
                                             network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                             base_fee=base_fee)

    stellar_transaction.append_payment_op(destination=MTLAddresses.public_exchange_eurmtl_usdc,
                                          asset=MTLAssets.eurmtl_asset,
                                          amount='15000',
                                          source=MTLAddresses.public_exchange_eurmtl_xlm)

    stellar_transaction.append_path_payment_strict_send_op(destination=MTLAddresses.public_exchange_eurmtl_xlm,
                                                           send_asset=MTLAssets.usdc_asset,
                                                           send_amount='15000',
                                                           source=MTLAddresses.public_exchange_eurmtl_usdc,
                                                           dest_asset=MTLAssets.xlm_asset,
                                                           dest_min='15000',
                                                           path=stellar_get_receive_path(MTLAssets.usdc_asset, '15000',
                                                                                         MTLAssets.xlm_asset))

    stellar_transaction.set_timeout(250)
    stellar_transaction = stellar_transaction.build()
    stellar_transaction.sign(get_private_sign())
    xdr = stellar_transaction.to_xdr()
    logger.info(f"xdr: {xdr}")

    server.submit_transaction(stellar_transaction)


if __name__ == "__main__":
    #move_usdc()
    #exit()
    # asyncio.run(update_offer(account_key=public_exchange_eurmtl_usdc, price_min=0.8, price_max=1.3,
    #                         price=1/1.109,
    #                         selling_asset=usdc_asset, buying_asset=eurmtl_asset, amount=52,
    #                         check_persent=persent_cost,
    #                         record=[])
    #            )
    # exit(0)
    logger.add("mtl_exchange.log", rotation="1 MB")
    if cmd_load_bot_value(quik_pool(), 0, BotValueTypes.StopExchange, None):
        exit()
    asyncio.run(check_exchange())
    # check_fire(1.5)
