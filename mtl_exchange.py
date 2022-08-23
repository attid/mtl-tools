from stellar_sdk import Keypair, Network, Server, Signer, TransactionBuilder, Asset, Account, SignerKey, Price
import json, requests, math
from settings import private_exchange, openexchangerates_id
import app_logger

# https://stellar-sdk.readthedocs.io/en/latest/

if 'logger' not in globals():
    logger = app_logger.get_logger("mtl_exchange")

min_price = 3.0  # min max price in xlm
max_price = 15.2

max_eurmtl = 10000.0  # max offer
max_btcmtl = 0.1  # max offer
max_mtl = 1500.0  # max offer
max_xlm_eurmtl = 20005.0
max_xlm_mtl = 1000.0
max_xlm_btcmtl = 1000.0

min_xlm = 5.0
persent_eurmtl = 1.05  # 5% наценки
persent_btcmtl = 1.05  # 5% наценки
persent_mtl = 1.05  # 5% наценки
persent_xlm = 1.005  # 0,5% наценки
persent_cost = 1.01  # 1% изменения цены для обновления

public_mtl = "GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V"

public_exchange = "GCVF74HQRLPAGTPFSYUAKGHSDSMBQTMVSLKWKUU65ULEN7TL4N56IPZ7"

server = Server(horizon_url="https://horizon.stellar.org")
account_exchange = server.load_account(public_exchange)

asset_xlm = Asset("XLM")
asset_eurmtl = Asset("EURMTL", public_mtl)
asset_mtl = Asset("MTL", public_mtl)
asset_btcmtl = Asset("BTCMTL", public_mtl)

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
offer_eurmtl_id = 0
offer_btcmtl_id = 0
offer_mtl_id = 0
offer_xlm_id = 0


print(json.dumps(rq["_embedded"]["records"], indent=4))
records = {}
if len(rq["_embedded"]["records"]) > 0:
    for record in rq["_embedded"]["records"]:
        selling_name = 'XLM' if record["selling"]["asset_type"] == 'native' else record["selling"]["asset_code"]
        buying_name = 'XLM' if record["buying"]["asset_type"] == 'native' else record["buying"]["asset_code"]
        records[f"{selling_name}-{buying_name}"] = record

    if 'EURMTL-XLM' in records:
        offer_eurmtl_id = int(records['EURMTL']["id"])
        eurmtl_sale_sum = float(records['EURMTL']["amount"])
        eurmtl_sale_price = float(records['EURMTL']["price"])
        logger.info(['offer_eurmtl_id', offer_eurmtl_id, 'eurmtl_sale_sum', eurmtl_sale_sum, 'eurmtl_sale_price',
                     eurmtl_sale_price])
    else:
        logger.info(['offer_eurmtl_id', offer_eurmtl_id])

    if 'BTCMTL-XLM' in records:
        offer_btcmtl_id = int(records['BTCMTL']["id"])
        btcmtl_sale_sum = float(records['BTCMTL']["amount"])
        btcmtl_sale_price = float(records['BTCMTL']["price"])
        logger.info(['offer_btcmtl_id', offer_btcmtl_id, 'btcmtl_sale_sum', btcmtl_sale_sum, 'btcmtl_sale_price',
                     btcmtl_sale_price])
    else:
        logger.info(['offer_btcmtl_id', offer_btcmtl_id])

    if 'MTL-XLM' in records:
        offer_mtl_id = int(records['MTL']["id"])
        mtl_sale_sum = float(records['MTL']["amount"])
        mtl_sale_price = float(records['MTL']["price"])
        logger.info(['offer_mtl_id', offer_eurmtl_id, 'mtl_sale_sum', mtl_sale_sum, 'mtl_sale_price',
                     mtl_sale_price])
    else:
        logger.info(['offer_mtl_id', offer_mtl_id])

    if 'XLM-EURMTL' in records:
        offer_xlm_id = int(records['XLM']["id"])
        xlm_sale_sum = float(records['XLM']["amount"])
        xlm_sale_price = float(records['XLM']["price"])
        logger.info(['offer_xlm_id', offer_xlm_id, 'xlm_sale_sum', xlm_sale_sum, 'xlm_sale_price', xlm_sale_price])
    else:
        logger.info(['offer_xlm_id', offer_xlm_id])

rq = requests.get(
    f'https://openexchangerates.org/api/latest.json?app_id={openexchangerates_id}&symbols=EUR,BTC,STR&show_alternative=true').json()
# print(rq)
# rq = {'disclaimer': 'Usage subject to terms: https://openexchangerates.org/terms', 'license': 'https://openexchangerates.org/license', 'timestamp': 1639054800, 'base': 'USD', 'rates': {'BTC': 2.0214929e-05, 'EUR': 0.884216, 'STR': 3.4054617845}}
eur = float(rq["rates"]["EUR"])
stl = float(rq["rates"]["STR"])
btc = float(rq["rates"]["BTC"])
eur_in_xlm_cost = stl / eur
btc_in_eur_cost = eur / eur
logger.info(['eurmtl_cost', eur_in_xlm_cost, 'btc_in_eur_cost', btc_in_eur_cost])

sum_eurmtl = sum_eurmtl if sum_eurmtl < max_eurmtl else max_eurmtl
sum_btcmtl = sum_btcmtl if sum_btcmtl < max_btcmtl else max_btcmtl
sum_mtl = sum_mtl if sum_mtl < max_mtl else max_mtl
# get xlm to eurmtl
sum_xlm -= min_xlm
sum_xlm_to_eurmtl = sum_xlm if sum_xlm < max_xlm_eurmtl else max_xlm_eurmtl
# get xlm to mtl
sum_xlm -= sum_xlm_to_eurmtl
sum_xlm_to_mtl = sum_xlm if sum_xlm < max_xlm_mtl else max_xlm_mtl
# get xlm to btc
sum_xlm -= sum_xlm_to_mtl
sum_xlm_to_btcmtl = sum_xlm if sum_xlm < max_xlm_btcmtl else max_xlm_btcmtl

if (eur_in_xlm_cost < min_price) or (eur_in_xlm_cost > max_price):
    sum_eurmtl = 0
    sum_btcmtl = 0
    sum_mtl = 0
    sum_xlm_to_eurmtl = 0

if (((offer_eurmtl_id == 0) and (sum_eurmtl > 0)) or (
        eur_in_xlm_cost * persent_eurmtl > eurmtl_sale_price * persent_cost) or (
        eur_in_xlm_cost * persent_eurmtl * persent_cost < eurmtl_sale_price) or (sum_eurmtl != eurmtl_sale_sum)):
    logger.info('need sale eurmtl')

    transaction = TransactionBuilder(source_account=account_exchange,
                                     network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE, base_fee=100)
    transaction.append_manage_sell_offer_op(selling=asset_eurmtl, buying=asset_xlm, amount=str(sum_eurmtl),
                                            price=Price.from_raw_price(str(round(eur_in_xlm_cost * persent_eurmtl, 7))),
                                            offer_id=offer_eurmtl_id)
    transaction = transaction.build()
    xdr = transaction.to_xdr()
    logger.info(f"xdr: {xdr}")

    transaction.sign(private_exchange)
    transaction_resp = server.submit_transaction(transaction)
    # logger.info(transaction_resp)

if (((offer_mtl_id == 0) and (sum_mtl > 0)) or (
        eur_in_xlm_cost * persent_mtl > mtl_sale_price * persent_cost) or (
        eur_in_xlm_cost * persent_mtl * persent_cost < mtl_sale_price) or (sum_mtl != mtl_sale_sum)):
    logger.info('need sale mtl')

    transaction = TransactionBuilder(source_account=account_exchange,
                                     network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE, base_fee=100)
    transaction.append_manage_sell_offer_op(selling=asset_mtl, buying=asset_xlm, amount=str(sum_mtl),
                                            price=Price.from_raw_price(
                                                str(round(eur_in_xlm_cost * 2.01 * persent_mtl, 7))),
                                            offer_id=offer_mtl_id)
    transaction = transaction.build()
    xdr = transaction.to_xdr()
    logger.info(f"xdr: {xdr}")

    transaction.sign(private_exchange)
    transaction_resp = server.submit_transaction(transaction)

if (((offer_xlm_id == 0) and (sum_xlm_to_eurmtl > 0)) or (
        1 / eur_in_xlm_cost * persent_xlm > xlm_sale_price * persent_cost) or (
        1 / eur_in_xlm_cost * persent_xlm * persent_cost < xlm_sale_price) or (sum_xlm_to_eurmtl != xlm_sale_sum)):
    logger.info(f'need sale {sum_xlm_to_eurmtl} xlm')

    transaction = TransactionBuilder(source_account=account_exchange,
                                     network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE, base_fee=100)
    transaction.append_manage_sell_offer_op(selling=asset_xlm, buying=asset_eurmtl, amount=str(sum_xlm_to_eurmtl),
                                            price=Price.from_raw_price(
                                                str(round((1 / eur_in_xlm_cost) * persent_xlm, 7))),
                                            offer_id=offer_xlm_id)
    transaction = transaction.build()
    transaction.sign(private_exchange)
    xdr = transaction.to_xdr()
    logger.info(f"xdr: {xdr}")

    transaction_resp = server.submit_transaction(transaction)
