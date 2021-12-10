import gspread
import datetime
import requests
import app_logger
from settings import currencylayer_id, coinlayer_id

logger = app_logger.get_logger("update_report")

MASTERASSETS = ['BTCDEBT','BTCMTL','EUR','EURDEBT','EURMTL','GPA','GRAFDRON','iTrade',
                'MonteAqua','MonteCrafto','MTL','MTLBR','MTLBRO','MTLCAMP','MTLCITY','OSW','XLM','MTLand']

gc = gspread.service_account('mtl-google-doc.json')

# Open a sheet from a spreadsheet in one go
wks = gc.open("MTL Report").worksheet("RawData")

# Update a range of cells using the top left corner address
now = datetime.datetime.now()
#print(now.strftime('%d.%m.%Y %H:%M:%S'))
wks.update('B2',now.strftime('%d.%m.%Y %H:%M:%S'))

#usd
rq = requests.get(f'http://api.currencylayer.com/live?access_key={currencylayer_id}&format=1&currencies=EUR')
wks.update('B4',float(rq.json()['quotes']['USDEUR']))

#BTC,XLM
rq = requests.get(f'http://api.coinlayer.com/api/live?access_key={coinlayer_id}&symbols=BTC,XLM')
wks.update('B5',float(rq.json()['rates']['BTC']))
wks.update('B6',float(rq.json()['rates']['XLM']))

#MTL
rq = requests.get('https://horizon.stellar.org/assets?asset_code=MTL&asset_issuer=GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V')
wks.update('B9',float(rq.json()['_embedded']['records'][0]['amount']))

#FOND
rq = requests.get('https://horizon.stellar.org/accounts/GDX23CPGMQ4LN55VGEDVFZPAJMAUEHSHAMJ2GMCU2ZSHN5QF4TMZYPIS')
assets = []

for balance in rq.json()['balances']:
    if balance['asset_type'] == "native" :
        assets.append(['XLM',float(balance['balance'])])
    else:
        assets.append([balance['asset_code'],float(balance['balance'])])

goodassets = []

for ms in MASTERASSETS:
    asset = list(filter(lambda x: x[0] == ms, assets))[0]
    goodassets.append(asset)

wks.update('A12',goodassets)

#MTLand
json_land = requests.get('https://api.stellar.expert/explorer/public/asset/MTLand-GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V/holders?limit=200').json()

#print(json_land['_embedded']['records'])
land_count = 0.0
for landlord in json_land['_embedded']['records']:
    if landlord['account']!='GDX23CPGMQ4LN55VGEDVFZPAJMAUEHSHAMJ2GMCU2ZSHN5QF4TMZYPIS':
        land_count += float(landlord['balance']) / 10000000
#print(land_count)
wks.update('C29',land_count)

#exchange
public_exchange = "GCVF74HQRLPAGTPFSYUAKGHSDSMBQTMVSLKWKUU65ULEN7TL4N56IPZ7"
balances = {}
rq = requests.get(f'https://horizon.stellar.org/accounts/{public_exchange}').json()
#print(json.dumps(rq, indent=4))
for balance in rq["balances"]:
    name = 'XLM' if balance["asset_type"] == 'native' else balance["asset_code"]
    balances[name] = balance["balance"]
wks.update('F10',float(balances['XLM']))
wks.update('F11',float(balances['EURMTL']))
wks.update('F12',float(balances['EURDEBT']))

logger.info(f'all done {now}')
