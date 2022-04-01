from stellar_sdk import Keypair, Network, Server, Signer, TransactionBuilder, Asset, Account, SignerKey, Price
import json,requests,math
from settings import private_exchange2, openexchangerates_id
import app_logger
#https://stellar-sdk.readthedocs.io/en/latest/

if 'logger' not in globals():
    logger = app_logger.get_logger("mtl_exchange")

min_price = 2.0  # min max price in xlm
max_price = 10.4

max_eurmtl = 202.0 #max offer
max_xlm = 104.0

min_xlm = 3.0   
persent_eurmtl = 1.0  #0% наценки 
persent_xlm = 1.0  #2% наценки 
persent_cost = 1.01  #1% изменения цены для обновления

public_mtl = "GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V"

public_exchange2 = "GAEFTFGQYWSF5T3RVMBSW2HFZMFZUQFBYU5FUF3JT3ETJ42NXPDWOO2F"

server = Server(horizon_url="https://horizon.stellar.org")
account_exchange = server.load_account(public_exchange2)

asset_xlm = Asset("XLM")
asset_eurmtl = Asset("EURMTL", public_mtl)

# get balance
balances = {}
rq = requests.get(f'https://horizon.stellar.org/accounts/{public_exchange2}').json()
#print(json.dumps(rq, indent=4))
for balance in rq["balances"]:
    name = 'XLM' if balance["asset_type"] == 'native' else balance["asset_code"]
    balances[name] = balance["balance"]

sum_eurmtl = float(balances['EURMTL'])
sum_xlm = float(balances['XLM'])
logger.info(['sum_eurmtl',sum_eurmtl,'sum_xlm',sum_xlm])

#get offers
rq = requests.get(f'https://horizon.stellar.org/accounts/{public_exchange2}/offers').json()
#print(json.dumps(rq["_embedded"]["records"], indent=4))
records = {}
#if len(rq["_embedded"]["records"]) > 0:
for record in rq["_embedded"]["records"]:
    name = 'XLM' if record["selling"]["asset_type"] == 'native' else record["selling"]["asset_code"]
    records[name] = record

if 'EURMTL' in records:
    offer_eurmtl_id = int(records['EURMTL']["id"])
    eurmtl_sale_sum = float(records['EURMTL']["amount"])
    eurmtl_sale_price = float(records['EURMTL']["price"])
    logger.info(['offer_eurmtl_id',offer_eurmtl_id,'eurmtl_sale_sum',eurmtl_sale_sum,'eurmtl_sale_price',eurmtl_sale_price]) 
else:
    offer_eurmtl_id = 0
    logger.info(['offer_eurmtl_id',offer_eurmtl_id]) 

if 'XLM' in records:
    offer_xlm_id = int(records['XLM']["id"])
    xlm_sale_sum = float(records['XLM']["amount"])
    xlm_sale_price = float(records['XLM']["price"])
    logger.info(['offer_xlm_id',offer_xlm_id,'xlm_sale_sum',xlm_sale_sum,'xlm_sale_price',xlm_sale_price]) 
else:
    offer_xlm_id = 0
    logger.info(['offer_xlm_id',offer_xlm_id]) 
        

rq = requests.get('https://horizon.stellar.org/offers?selling_asset_type=credit_alphanum4&selling_asset_issuer=GAP5LETOV6YIE62YAM56STDANPRDO7ZFDBGSNHJQIYGGKSMOZAHOOS2S&selling_asset_code=EURT&limit=2&buying_asset_type=native&order=desc').json()
#print(json.dumps(rq["_embedded"]["records"], indent=4))
cost_eur = float(rq["_embedded"]["records"][0]["price"])
rq = requests.get('https://horizon.stellar.org/offers?buying_asset_type=credit_alphanum4&buying_asset_issuer=GAP5LETOV6YIE62YAM56STDANPRDO7ZFDBGSNHJQIYGGKSMOZAHOOS2S&buying_asset_code=EURT&limit=2&selling_asset_type=native&order=desc').json()
cost_xlm = float(rq["_embedded"]["records"][0]["price"])
logger.info(['cost_eur',cost_eur,'cost_xlm',cost_xlm])

sum_eurmtl = sum_eurmtl if sum_eurmtl < max_eurmtl else max_eurmtl
sum_xlm = sum_xlm if sum_xlm < max_xlm else max_xlm
sum_xlm -= min_xlm

if (cost_eur < min_price) or (cost_eur > max_price):
    sum_eurmtl = 0
    sum_xlm = 0


if (((offer_eurmtl_id == 0) and (sum_eurmtl > 0)) or (cost_eur*persent_eurmtl > eurmtl_sale_price*persent_cost) or (cost_eur*persent_eurmtl*persent_cost < eurmtl_sale_price) or (sum_eurmtl != eurmtl_sale_sum)):
    logger.info('need sale eurmtl')

    transaction = TransactionBuilder(source_account=account_exchange,network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,base_fee=100)
    transaction.append_manage_sell_offer_op(selling=asset_eurmtl, buying=asset_xlm, amount=str(sum_eurmtl),
                                            price=Price.from_raw_price(str(round(cost_eur*persent_eurmtl,7))),offer_id=offer_eurmtl_id)
    transaction = transaction.build()
    transaction.sign(private_exchange2)
    xdr = transaction.to_xdr()
    logger.info(f"xdr: {xdr}")

    transaction_resp = server.submit_transaction(transaction)
    #logger.info(transaction_resp)

if (((offer_xlm_id == 0) and (sum_xlm > 0)) or (cost_xlm*persent_xlm > xlm_sale_price*persent_cost) or (cost_xlm*persent_xlm*persent_cost < xlm_sale_price) or (sum_xlm != xlm_sale_sum)):
#    if (cost_xlm > 1/min_price) or (cost_xlm < 1/max_price) or (sum_xlm < 1):
#        print(sum_xlm,cost_xlm,1/min_price,1/max_price)
    logger.info('need sale xlm')

    transaction = TransactionBuilder(source_account=account_exchange,network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,base_fee=100)
    transaction.append_manage_sell_offer_op(selling=asset_xlm, buying=asset_eurmtl, amount=str(sum_xlm),
                                            price=Price.from_raw_price(str(round(cost_xlm*persent_xlm,7))),offer_id=offer_xlm_id)
    transaction = transaction.build()
    transaction.sign(private_exchange2)
    xdr = transaction.to_xdr()
    logger.info(f"xdr: {xdr}")

    transaction_resp = server.submit_transaction(transaction)
    #logger.info(transaction_resp)