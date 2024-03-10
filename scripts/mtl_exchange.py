from utils.stellar_utils import *
from db.quik_pool import quik_pool
from collections import namedtuple

max_eurmtl = 10000.0  # max offer
# max_btcmtl = 0.1  # max offer
# max_satsmtl = 1000000  # max offer
sats_cost = 100000000

# min_xlm = 50.0
persent_eurmtl = 1.03  # 1.03 =  5% наценки
persent_btc = 1.01  #
persent_xlm = 1.03  #
persent_usdc = 1.002  # 0.975 for fund exchange
persent_cost = 1.01  # 1% изменения цены для обновления
persent_btc_cost = 1.001  # 0,1% изменения цены для обновления

# Создаем кортеж для хранения параметров
AddressConfig = namedtuple('AddressConfig', [
    'address', 'asset_a', 'asset_b', 'price_min', 'price_max',
    'price_a', 'price_b', 'check_persent', 'max_a', 'max_b'
])

# server = Server(horizon_url="http://158.58.231.224:8000/")
# server = Server(horizon_url="https://horizon.publicnode.org")
server = Server(horizon_url="https://horizon.stellar.org")


def get_offers(address: str):
    call = server.offers().for_account(address).limit(200).call()

    records = {}
    for record in call['_embedded']['records']:
        selling_name = 'XLM' if record["selling"]["asset_type"] == 'native' else record["selling"]["asset_code"]
        buying_name = 'XLM' if record["buying"]["asset_type"] == 'native' else record["buying"]["asset_code"]
        records[f'{selling_name}-{buying_name}'] = record

    return records


def get_sum(amount, max_value):
    return int(amount) if amount < max_value else max_value


async def update_offers(update_config):
    offers = get_offers(update_config.address)
    balances = await get_balances(update_config.address)
    balances['XLM'] = float(balances['XLM']) - 50  # оставляем минимум 50
    amount_a = get_sum(float(balances[update_config.asset_a.code]), update_config.max_a)
    amount_b = get_sum(float(balances[update_config.asset_b.code]), update_config.max_b)
    await update_offer(account_key=update_config.address, price_min=update_config.price_min,
                       price_max=update_config.price_max,
                       price=update_config.price_a, selling_asset=update_config.asset_a,
                       buying_asset=update_config.asset_b,
                       amount=amount_a, check_persent=update_config.check_persent,
                       record=offers.get(f'{update_config.asset_a.code}-{update_config.asset_b.code}'))

    await update_offer(account_key=update_config.address, price_min=1 / update_config.price_max,
                       price_max=1 / update_config.price_min,
                       price=update_config.price_b, selling_asset=update_config.asset_b,
                       buying_asset=update_config.asset_a,
                       amount=amount_b, check_persent=update_config.check_persent,
                       record=offers.get(f'{update_config.asset_b.code}-{update_config.asset_a.code}'))


async def check_exchange():
    # EUR cost
    rq = requests.get('https://api.binance.com/api/v3/ticker/price?symbol=EURUSDT').json()
    usdt_eur_cost = 1 / float(rq['price'])

    rq = requests.get('https://api.binance.com/api/v3/ticker/price?symbol=XLMUSDT').json()
    stl = 1 / float(rq['price'])
    usd_xlm_cost = stl
    eurmtl_xlm_cost = stl / usdt_eur_cost

    rq = requests.get('https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT').json()
    btc_eur_cost = float(rq['price']) * usdt_eur_cost
    logger.info(['eur_cost', usdt_eur_cost, 'eurmtl_xlm_cost', eurmtl_xlm_cost, eurmtl_xlm_cost * persent_eurmtl,
                 'usd_xlm_cost', usd_xlm_cost, 'btc_eur_cost', btc_eur_cost])

    configs = [
        # EURMTL - XLM
        AddressConfig(address=MTLAddresses.public_exchange_eurmtl_xlm,
                      asset_a=MTLAssets.eurmtl_asset, asset_b=MTLAssets.xlm_asset,
                      price_min=5, price_max=15,
                      price_a=eurmtl_xlm_cost * persent_eurmtl,
                      price_b=round((1 / eurmtl_xlm_cost) * persent_xlm, 5),
                      check_persent=persent_cost,
                      max_a=max_eurmtl, max_b=round(max_eurmtl * eurmtl_xlm_cost)
                      ),
        # MTL - XLM
        AddressConfig(address=MTLAddresses.public_exchange_mtl_xlm,
                      asset_a=MTLAssets.mtl_asset, asset_b=MTLAssets.xlm_asset,
                      price_min=5 * 4, price_max=15 * 4,
                      price_a=eurmtl_xlm_cost * persent_eurmtl * 4,
                      price_b=round((1 / eurmtl_xlm_cost / 3) * persent_xlm, 5),
                      check_persent=persent_cost,
                      max_a=max_eurmtl, max_b=max_eurmtl
                      ),
        # EURMTL - BTC
        AddressConfig(address=MTLAddresses.public_exchange_eurmtl_btc,
                      asset_a=MTLAssets.btcmtl_asset, asset_b=MTLAssets.eurmtl_asset,
                      price_min=30000, price_max=60000,
                      price_a=round(btc_eur_cost * 1.01),
                      price_b=round((1 / btc_eur_cost) * 1.03, 7),
                      check_persent=persent_btc_cost,
                      max_a=round(max_eurmtl / btc_eur_cost, 5), max_b=max_eurmtl
                      ),
        # EURMTL - SATS
        AddressConfig(address=MTLAddresses.public_exchange_eurmtl_sats,
                      asset_a=MTLAssets.satsmtl_asset, asset_b=MTLAssets.eurmtl_asset,
                      price_min=30000 / sats_cost, price_max=60000 / sats_cost,
                      price_a=round(btc_eur_cost * 1.01 / sats_cost, 8),
                      price_b=round(1 / btc_eur_cost * sats_cost * 1.03),
                      check_persent=persent_cost,
                      max_a=round(max_eurmtl / btc_eur_cost, 5) * sats_cost, max_b=max_eurmtl
                      ),
        # EURMTL - USDM
        AddressConfig(address=MTLAddresses.public_exchange_eurmtl_usdm,
                      asset_a=MTLAssets.eurmtl_asset, asset_b=MTLAssets.usdm_asset,
                      price_min=0.8, price_max=1.3,
                      price_a=round(1 / usdt_eur_cost * persent_eurmtl, 4),
                      price_b=round(usdt_eur_cost * persent_usdc, 4),
                      check_persent=persent_cost,
                      max_a=max_eurmtl, max_b=round(max_eurmtl * (1 / usdt_eur_cost))
                      ),
        # USDM - USDC
        AddressConfig(address=MTLAddresses.public_exchange_usdm_usdc,
                      asset_a=MTLAssets.usdm_asset, asset_b=MTLAssets.usdc_asset,
                      price_min=0.9, price_max=1.1,
                      price_a=round(0.999999, 7),
                      price_b=round(1.01, 4),
                      check_persent=persent_cost,
                      max_a=max_eurmtl, max_b=max_eurmtl
                      ),
        # USDM - XLM
        AddressConfig(address=MTLAddresses.public_exchange_usdm_xlm,
                      asset_a=MTLAssets.usdm_asset, asset_b=MTLAssets.xlm_asset,
                      price_min=5, price_max=15,
                      price_a=usd_xlm_cost * 1.02,
                      price_b=round((1 / usd_xlm_cost) * 1.03, 5),
                      check_persent=persent_cost,
                      max_a=max_eurmtl, max_b=round(max_eurmtl * usd_xlm_cost)
                      ),

    ]

    for update_config in configs:
        await update_offers(update_config)


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


if __name__ == "__main__":
    logger.add("mtl_exchange.log", rotation="1 MB")
    if db_load_bot_value(quik_pool(), 0, BotValueTypes.StopExchange, None):
        exit()
    asyncio.run(check_exchange())
    # check_fire(1.5)
