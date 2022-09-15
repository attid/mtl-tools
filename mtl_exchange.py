from stellar_sdk import Keypair, Network, Server, Signer, TransactionBuilder, Asset, Account, SignerKey, Price
import json, requests, math
from settings import private_exchange, openexchangerates_id
import app_logger

# https://stellar-sdk.readthedocs.io/en/latest/

if 'logger' not in globals():
    logger = app_logger.get_logger("mtl_exchange")

min_price = 6.0  # min max price in xlm
max_price = 12.2

max_eurmtl = 10000.0  # max offer
max_mtl = 1500.0  # max offer
max_xlm = 20005.0

min_xlm = 5.0
persent_eurmtl = 1.05  # 5% наценки
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
logger.info(['sum_eurmtl', sum_eurmtl, 'sum_mtl', sum_mtl, 'sum_xlm', sum_xlm])

# get offers
rq = requests.get(f'https://horizon.stellar.org/accounts/{public_exchange}/offers').json()
offer_eurmtl_id = 0
offer_mtl_id = 0
offer_xlm_id = 0
eurmtl_sale_price = 0
xlm_sale_price = 0

# print(json.dumps(rq["_embedded"]["records"], indent=4))
records = {}
if len(rq["_embedded"]["records"]) > 0:
    for record in rq["_embedded"]["records"]:
        name = 'XLM' if record["selling"]["asset_type"] == 'native' else record["selling"]["asset_code"]
        records[name] = record

    if 'EURMTL' in records:
        offer_eurmtl_id = int(records['EURMTL']["id"])
        eurmtl_sale_sum = float(records['EURMTL']["amount"])
        eurmtl_sale_price = float(records['EURMTL']["price"])
        logger.info(['offer_eurmtl_id', offer_eurmtl_id, 'eurmtl_sale_sum', eurmtl_sale_sum, 'eurmtl_sale_price',
                     eurmtl_sale_price])
    else:
        logger.info(['offer_eurmtl_id', offer_eurmtl_id])

    if 'MTL' in records:
        offer_mtl_id = int(records['MTL']["id"])
        mtl_sale_sum = float(records['MTL']["amount"])
        mtl_sale_price = float(records['MTL']["price"])
        logger.info(['offer_mtl_id', offer_eurmtl_id, 'mtl_sale_sum', mtl_sale_sum, 'mtl_sale_price',
                     mtl_sale_price])
    else:
        logger.info(['offer_mtl_id', offer_mtl_id])

    if 'XLM' in records:
        offer_xlm_id = int(records['XLM']["id"])
        xlm_sale_sum = float(records['XLM']["amount"])
        xlm_sale_price = float(records['XLM']["price"])
        logger.info(['offer_xlm_id', offer_xlm_id, 'xlm_sale_sum', xlm_sale_sum, 'xlm_sale_price', xlm_sale_price])
    else:
        logger.info(['offer_xlm_id', offer_xlm_id])

rq = requests.get(
    f'https://openexchangerates.org/api/latest.json?app_id={openexchangerates_id}&symbols=EUR,BTC,STR&show_alternative=true').json()
#print(rq)
# rq = {'disclaimer': 'Usage subject to terms: https://openexchangerates.org/terms', 'license': 'https://openexchangerates.org/license', 'timestamp': 1639054800, 'base': 'USD', 'rates': {'BTC': 2.0214929e-05, 'EUR': 0.884216, 'STR': 3.4054617845}}
eur = float(rq["rates"]["EUR"])
#stl = float(rq["rates"]["STR"])
#print(stl)

rq = requests.get('https://api.binance.com/api/v3/ticker/price?symbol=XLMUSDT').json()
stl = 1/float(rq['price'])
#print(stl)

cost = stl / eur
logger.info(['cost', cost])

sum_eurmtl = sum_eurmtl if sum_eurmtl < max_eurmtl else max_eurmtl
sum_mtl = sum_mtl if sum_mtl < max_mtl else max_mtl
sum_xlm = sum_xlm if sum_xlm < max_xlm else max_xlm
sum_xlm -= min_xlm

if (cost < min_price) or (cost > max_price):
    sum_eurmtl = 0
    sum_mtl = 0
    sum_xlm = 0

if (((offer_eurmtl_id == 0) and (sum_eurmtl > 0)) or (cost * persent_eurmtl > eurmtl_sale_price * persent_cost) or (
        cost * persent_eurmtl * persent_cost < eurmtl_sale_price) or (sum_eurmtl != eurmtl_sale_sum)):
    logger.info('need sale eurmtl')

    transaction = TransactionBuilder(source_account=account_exchange,
                                     network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE, base_fee=100)
    transaction.append_manage_sell_offer_op(selling=asset_eurmtl, buying=asset_xlm, amount=str(sum_eurmtl),
                                            price=Price.from_raw_price(str(round(cost * persent_eurmtl, 7))),
                                            offer_id=offer_eurmtl_id)
    if sum_mtl > 1:
        transaction.append_manage_sell_offer_op(selling=asset_mtl, buying=asset_xlm, amount=str(sum_mtl),
                                                price=Price.from_raw_price(str(round(cost * 2.01 * persent_mtl, 7))),
                                                offer_id=offer_mtl_id)
    transaction = transaction.build()
    xdr = transaction.to_xdr()
    logger.info(f"xdr: {xdr}")

    transaction.sign(private_exchange)
    transaction_resp = server.submit_transaction(transaction)
    # logger.info(transaction_resp)

if (((offer_xlm_id == 0) and (sum_xlm > 0)) or (1 / cost * persent_xlm > xlm_sale_price * persent_cost) or (
        1 / cost * persent_xlm * persent_cost < xlm_sale_price) or (sum_xlm != xlm_sale_sum)):
    logger.info(f'need sale {sum_xlm} xlm')

    transaction = TransactionBuilder(source_account=account_exchange,
                                     network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE, base_fee=100)
    transaction.append_manage_sell_offer_op(selling=asset_xlm, buying=asset_eurmtl, amount=str(sum_xlm),
                                            price=Price.from_raw_price(str(round((1 / cost) * persent_xlm, 7))),
                                            offer_id=offer_xlm_id)
    transaction = transaction.build()
    transaction.sign(private_exchange)
    xdr = transaction.to_xdr()
    logger.info(f"xdr: {xdr}")

    transaction_resp = server.submit_transaction(transaction)
    # logger.info(transaction_resp)
