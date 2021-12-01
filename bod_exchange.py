from stellar_sdk import Keypair, Network, Server, Signer, TransactionBuilder, Asset, Account, SignerKey, Price
import json,requests,math
from settings import private_bod_exchange, openexchangerates_id
import app_logger
#https://stellar-sdk.readthedocs.io/en/latest/

#logging.basicConfig(filename="bod_exchange.log", level=logging.INFO)
logger = app_logger.get_logger("bod_exchange")

public_mtl = "GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V"
public_fond = "GDX23CPGMQ4LN55VGEDVFZPAJMAUEHSHAMJ2GMCU2ZSHN5QF4TMZYPIS"

public_bod_exchange = "GDEK5KGFA3WCG3F2MLSXFGLR4T4M6W6BMGWY6FBDSDQM6HXFMRSTEWBW"
public_bod = "GARUNHJH3U5LCO573JSZU4IOBEVQL6OJAAPISN4JKBG2IYUGLLVPX5OH"

server = Server(horizon_url="https://horizon.stellar.org")
bod_account_exchange = server.load_account(public_bod_exchange)

xlm_asset = Asset("XLM")  
eurmtl_asset = Asset("EURMTL", public_mtl)

# get balance
rq = requests.get(f'https://horizon.stellar.org/accounts/{public_bod_exchange}').json()
eurmtl_sum = float(rq["balances"][0]['balance'])
xlm_sum = float(rq["balances"][1]['balance'])
logger.info(['eurmtl_sum',eurmtl_sum,'xlm_sum',xlm_sum])

#get offers
rq = requests.get(f'https://horizon.stellar.org/accounts/{public_bod_exchange}/offers').json()
if len(rq["_embedded"]["records"]) > 0:
    offer_id = int(rq["_embedded"]["records"][0]["id"])
    eurmtl_sale_sum = float(rq["_embedded"]["records"][0]["amount"])
    eurmtl_sale_price = float(rq["_embedded"]["records"][0]["price"])
    logger.info(['offer_id',offer_id,'eurmtl_sale_sum',eurmtl_sale_sum,'eurmtl_sale_price',eurmtl_sale_price]) 
else:
    offer_id = 0
    logger.info(['offer_id',offer_id]) 

# if we need update offer    
if ((eurmtl_sum > 0) and (offer_id == 0)) or ((offer_id > 0) and (eurmtl_sum > eurmtl_sale_sum)):
    logger.info('need sale')
    rq = requests.get(f'https://openexchangerates.org/api/latest.json?app_id={openexchangerates_id}&symbols=EUR,BTC,STR&show_alternative=true').json()
    #rq = {'disclaimer': 'Usage subject to terms: https://openexchangerates.org/terms', 'license': 'https://openexchangerates.org/license', 'timestamp': 1638374400, 'base': 'USD', 'rates': {'BTC': 1.7052583e-05, 'EUR': 0.882253, 'STR': 3.0092620811}}
    
    eur = float(rq["rates"]["EUR"])
    stl = float(rq["rates"]["STR"])
    cost = stl / eur
    logger.info(['cost',cost])
    
    transaction = TransactionBuilder(source_account=bod_account_exchange,network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,base_fee=100)
    transaction.append_manage_sell_offer_op(selling_code=eurmtl_asset.code, selling_issuer=eurmtl_asset.issuer,
                                            buying_code=xlm_asset.code, buying_issuer=xlm_asset.issuer, amount=str(eurmtl_sum), 
                                            price=Price.from_raw_price(cost),offer_id=offer_id)
#   operation(ManageSellOffer(eurmtl_asset,xlm_asset,str(eurmtl_sum),Price.from_raw_price(cost),offer_id))
    transaction = transaction.build()
    xdr = transaction.to_xdr()
    logger.info(f"xdr: {xdr}")
    

    transaction.sign(private_bod_exchange)
    transaction_resp = server.submit_transaction(transaction)    
    logger.info(transaction_resp)
    
#if need send    
if xlm_sum > 3.1:
    logger.info('need pay')
    transaction = TransactionBuilder(source_account=bod_account_exchange,network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,base_fee=100)
    transaction.append_payment_op(destination=public_bod, amount=str(round(xlm_sum - 3,7)), asset_code=xlm_asset.code)
    transaction = transaction.build()
    xdr = transaction.to_xdr()
    logger.info(f"xdr: {xdr}")
    
    transaction.sign(private_bod_exchange)
    transaction_resp = server.submit_transaction(transaction)    
    logger.info(transaction_resp)

    