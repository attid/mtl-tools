from stellar_sdk import Network, Server, TransactionBuilder, Asset, Price
import json, requests

from mystellar import public_exchange, public_issuer, public_itolstov, public_sign, public_fire
from settings import private_sign, base_fee
import app_logger

# https://stellar-sdk.readthedocs.io/en/latest/

if 'logger' not in globals():
    logger = app_logger.get_logger("mtl_exchange")

max_eurmtl = 10000.0  # max offer
max_btcmtl = 0.1  # max offer

min_xlm = 5.0
persent_eurmtl = 1.05  # 5% наценки
persent_btc = 1.01  # 5% наценки
persent_xlm = 1.005  # 0,5% наценки
persent_cost = 1.01  # 1% изменения цены для обновления
persent_btc_cost = 1.001  # 1% изменения цены для обновления

server = Server(horizon_url="https://horizon.stellar.org")
account_exchange = server.load_account(public_exchange)
account_fire = server.load_account(public_fire)

asset_xlm = Asset("XLM")
asset_eurmtl = Asset("EURMTL", public_issuer)
asset_mtl = Asset("MTL", public_issuer)
asset_btcmtl = Asset("BTCMTL", public_issuer)


def update_offer(account, price_min, price_max, price, selling_asset, buying_asset, amount,
                 check_persent, record):
    test_record = {'id': '1086147610', 'paging_token': '1086147610',
                   'seller': 'GCVF74HQRLPAGTPFSYUAKGHSDSMBQTMVSLKWKUU65ULEN7TL4N56IPZ7',
                   'selling': {'asset_type': 'native'},
                   'buying': {'asset_type': 'credit_alphanum12', 'asset_code': 'EURMTL',
                              'asset_issuer': 'GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V'},
                   'amount': '20000.0000000', 'price_r': {'n': 557511, 'd': 5000000},
                   'price': '0.1115022', 'last_modified_ledger': 43210436,
                   'last_modified_time': '2022-10-21T08:15:53Z'}
    offer_id = int(record["id"]) if record else 0
    current_amount = float(record["amount"]) if record else 0
    current_price = float(record["price"]) if record else 0

    stellar_transaction = None
    # if offer and bad price need zero offer
    if (offer_id > 0) and ((price > price_max) or (price < price_min)):
        logger.info(f'need cancel {selling_asset.code} for {buying_asset.code} price {price} amount {amount}')
        stellar_transaction = TransactionBuilder(source_account=account,
                                                 network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                                 base_fee=base_fee)
        stellar_transaction.append_manage_sell_offer_op(selling=selling_asset, buying=buying_asset, amount='0',
                                                        price=Price.from_raw_price('1'), offer_id=offer_id)
    elif (amount > 0) and (price > 0) and (
            (price > current_price * check_persent) or (price * check_persent < current_price) or
            (current_amount != amount)):
        logger.info(f'need sale {selling_asset.code} for {buying_asset.code} price {price} amount {amount}')
        stellar_transaction = TransactionBuilder(source_account=account,
                                                 network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                                 base_fee=base_fee)
        stellar_transaction.append_manage_sell_offer_op(selling=selling_asset, buying=buying_asset, amount=str(amount),
                                                        price=Price.from_raw_price(str(price)), offer_id=offer_id)
    if stellar_transaction:
        stellar_transaction.set_timeout(50)
        stellar_transaction = stellar_transaction.build()
        stellar_transaction.sign(private_sign)
        xdr = stellar_transaction.to_xdr()
        logger.info(f"xdr: {xdr}")

        server.submit_transaction(stellar_transaction)


def fire_mtl(account, amount):
    stellar_transaction = TransactionBuilder(source_account=account,
                                             network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                             base_fee=base_fee)
    stellar_transaction.append_payment_op(destination=asset_mtl.issuer, asset=asset_mtl, amount=str(amount))
    stellar_transaction = stellar_transaction.build()
    stellar_transaction.sign(private_sign)
    xdr = stellar_transaction.to_xdr()
    logger.info(f"xdr: {xdr}")

    server.submit_transaction(stellar_transaction)


def check_exchange():
    # get balance
    balances = {}
    rq = requests.get(f'https://horizon.stellar.org/accounts/{public_exchange}').json()
    # print(json.dumps(rq, indent=4))
    for balance in rq["balances"]:
        name = 'XLM' if balance["asset_type"] == 'native' else balance["asset_code"]
        balances[name] = balance["balance"]

    sum_eurmtl = float(balances['EURMTL'])
    sum_mtl = float(balances['MTL'])
    sum_xlm = float(balances['XLM'])
    sum_btcmtl = float(balances['BTCMTL'])
    logger.info(['sum_eurmtl', sum_eurmtl, 'sum_mtl', sum_mtl, 'sum_xlm', sum_xlm, 'sum_btcmtl', sum_btcmtl])

    # get offers
    rq = requests.get(f'https://horizon.stellar.org/accounts/{public_exchange}/offers').json()
    # print(json.dumps(rq["_embedded"]["records"], indent=4))
    records = {}
    if len(rq["_embedded"]["records"]) > 0:
        for record in rq["_embedded"]["records"]:
            selling_name = 'XLM' if record["selling"]["asset_type"] == 'native' else record["selling"]["asset_code"]
            buying_name = 'XLM' if record["buying"]["asset_type"] == 'native' else record["buying"]["asset_code"]
            records[f'{selling_name}-{buying_name}'] = record

    # EUR cost
    rq = requests.get('https://api.binance.com/api/v3/ticker/price?symbol=EURUSDT').json()
    # print(rq)
    eur_cost = 1 / float(rq['price'])

    rq = requests.get('https://api.binance.com/api/v3/ticker/price?symbol=XLMUSDT').json()
    stl = 1 / float(rq['price'])
    # print(stl)
    cost_eurmtl = stl / eur_cost

    rq = requests.get('https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT').json()
    cost_btc = float(rq['price']) * eur_cost
    # print(float(rq['price']), eur_cost, float(rq['price']) / eur_cost, float(rq['price']) * eur_cost)
    logger.info(['eur_cost', eur_cost, 'xlm_cost', cost_eurmtl, cost_eurmtl * persent_eurmtl, 'btc_cost', cost_btc])

    sum_eurmtl_xlm = sum_eurmtl if sum_eurmtl < max_eurmtl else max_eurmtl
    sum_eurmtl = sum_eurmtl - sum_eurmtl_xlm
    sum_eurmtl_btc = sum_eurmtl if sum_eurmtl < max_eurmtl else max_eurmtl
    sum_btcmtl = sum_btcmtl if sum_btcmtl < max_btcmtl else max_btcmtl
    max_xlm = round(max_eurmtl * cost_eurmtl / 1000) * 1000 + 5
    sum_xlm = sum_xlm if sum_xlm < max_xlm else max_xlm
    sum_xlm -= min_xlm

    update_offer(account=account_exchange, price_min=5, price_max=15, price=cost_eurmtl * persent_eurmtl,
                 selling_asset=asset_eurmtl, buying_asset=asset_xlm, amount=sum_eurmtl_xlm, check_persent=persent_cost,
                 record=records.get('EURMTL-XLM'))

    update_offer(account=account_exchange, price_min=0.01, price_max=1, price=round((1 / cost_eurmtl) * persent_xlm, 5),
                 selling_asset=asset_xlm, buying_asset=asset_eurmtl, amount=sum_xlm, check_persent=persent_cost,
                 record=records.get('XLM-EURMTL'))

    update_offer(account=account_exchange, price_min=15000, price_max=30000, price=round(cost_btc * persent_btc),
                 selling_asset=asset_btcmtl, buying_asset=asset_eurmtl, amount=sum_btcmtl, check_persent=persent_btc_cost,
                 record=records.get('BTCMTL-EURMTL'))

    update_offer(account=account_exchange, price_min=1 / 30000, price_max=1 / 15000,
                 price=round((1 / cost_btc) * persent_btc, 7),
                 selling_asset=asset_eurmtl, buying_asset=asset_btcmtl, amount=sum_eurmtl_btc, check_persent=persent_btc_cost,
                 record=records.get('EURMTL-BTCMTL'))

    # update_offer(account=account_exchange, price_min=15000 * cost_eurmtl, price_max=1 * cost_eurmtl,
    #             price=round(cost_btc * cost_eurmtl * persent_btc),
    #             selling_asset=asset_btcmtl, buying_asset=asset_xlm, amount=sum_btcmtl, check_persent=persent_cost,
    #             record=records.get('BTCMTL-XLM'))


def check_fire(cost_fire):
    # get balance
    balances = {}
    rq = requests.get(f'https://horizon.stellar.org/accounts/{public_fire}').json()
    # print(json.dumps(rq, indent=4))
    for balance in rq["balances"]:
        name = 'XLM' if balance["asset_type"] == 'native' else balance["asset_code"]
        balances[name] = balance["balance"]

    sum_eurmtl = float(balances['EURMTL'])
    sum_mtl = float(balances['MTL'])
    logger.info(['fire', 'sum_eurmtl', sum_eurmtl, 'sum_mtl', sum_mtl])

    # get offers
    rq = requests.get(f'https://horizon.stellar.org/accounts/{public_fire}/offers').json()
    # print(json.dumps(rq["_embedded"]["records"], indent=4))
    records = {}
    if len(rq["_embedded"]["records"]) > 0:
        for record in rq["_embedded"]["records"]:
            selling_name = 'XLM' if record["selling"]["asset_type"] == 'native' else record["selling"]["asset_code"]
            buying_name = 'XLM' if record["buying"]["asset_type"] == 'native' else record["buying"]["asset_code"]
            records[f'{selling_name}-{buying_name}'] = record

    update_offer(account=account_fire, price_min=0.5, price_max=1, price=round(1 / cost_fire, 5),
                 selling_asset=asset_eurmtl, buying_asset=asset_mtl, amount=sum_eurmtl, check_persent=1.01,
                 record=records.get('EURMTL-MTL'))

    if sum_mtl > 0:
        fire_mtl(account_fire, sum_mtl)


def update_multi_sign(account):
    from mystellar2 import cmd_get_new_vote_mtl
    from stellar_sdk import TransactionEnvelope

    threshold = 0
    xdr = cmd_get_new_vote_mtl(account)
    transaction = TransactionEnvelope.from_xdr(xdr[0], network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)

    for operation in transaction.transaction.operations:
        if operation.high_threshold:
            threshold = operation.high_threshold
        if operation.signer and operation.signer.signer_key.encoded_signer_key in (public_itolstov, public_sign):
            transaction.transaction.operations.remove(operation)
    for operation in transaction.transaction.operations:
        if operation.high_threshold:
            threshold = operation.high_threshold
        if operation.signer and operation.signer.signer_key.encoded_signer_key in (public_itolstov, public_sign):
            transaction.transaction.operations.remove(operation)

    if threshold > 0 and len(transaction.transaction.operations) > 2:
        transaction2 = TransactionBuilder(source_account=account_exchange,
                                          network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                          base_fee=base_fee)
        transaction2.append_ed25519_public_key_signer(account_id=public_sign, weight=threshold * 2)

        transaction.transaction.operations.insert(0, transaction2.operations[0])

        transaction.sign(private_sign)

        xdr = transaction.to_xdr()
        logger.info(f"xdr: {xdr}")

        server.submit_transaction(transaction)


def update_multi_sign_all():
    update_multi_sign(public_exchange)
    update_multi_sign(public_fire)


if __name__ == "__main__":
    check_exchange()
    # check_fire(1.5)
    # update_multi_sign_all()
    # update_multi_sign()
