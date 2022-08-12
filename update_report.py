import datetime
import gspread
import json
import requests
import app_logger
import fb
from settings import currencylayer_id, coinlayer_id

# https://docs.gspread.org/en/latest/

if 'logger' not in globals():
    logger = app_logger.get_logger("update_report")

MASTERASSETS = ['BTCDEBT', 'BTCMTL', 'EUR', 'EURDEBT', 'EURMTL', 'GPA', 'GRAFDRON', 'iTrade',
                'MonteAqua', 'MonteCrafto', 'MTL', 'MTLBR', 'MTLBRO', 'MTLCAMP', 'MTLCITY',
                'OSW', 'XLM', 'MTLand', 'AUMTL', 'MTLMiner', 'MTLDVL', 'GPACAR']


def update_main_report():
    gc = gspread.service_account('mtl-google-doc.json')

    # Open a sheet from a spreadsheet in one go
    wks = gc.open("MTL Report").worksheet("RawData")

    # Update a range of cells using the top left corner address
    now = datetime.datetime.now()
    # print(now.strftime('%d.%m.%Y %H:%M:%S'))

    # usd
    rq = requests.get(f'http://api.currencylayer.com/live?access_key={currencylayer_id}&format=1&currencies=EUR')
    wks.update('B4', float(rq.json()['quotes']['USDEUR']))

    # BTC,XLM
    rq = requests.get(f'http://api.coinlayer.com/api/live?access_key={coinlayer_id}&symbols=BTC,XLM')
    wks.update('B5', float(rq.json()['rates']['BTC']))
    wks.update('B6', float(rq.json()['rates']['XLM']))

    # MTL
    rq = requests.get(
        'https://horizon.stellar.org/assets?asset_code=MTL&asset_issuer=GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V')
    wks.update('B9', float(rq.json()['_embedded']['records'][0]['amount']))

    # FOND
    rq = requests.get('https://horizon.stellar.org/accounts/GDX23CPGMQ4LN55VGEDVFZPAJMAUEHSHAMJ2GMCU2ZSHN5QF4TMZYPIS')
    assets = []

    for balance in rq.json()['balances']:
        if balance['asset_type'] == "native":
            assets.append(['XLM', float(balance['balance'])])
        else:
            assets.append([balance['asset_code'], float(balance['balance'])])

    goodassets = []

    for ms in MASTERASSETS:
        asset = list(filter(lambda x: x[0] == ms, assets))
        if asset:
            asset = list(filter(lambda x: x[0] == ms, assets))[0]
        else:
            asset = [ms, 0]
        goodassets.append(asset)

    wks.update('A14', goodassets)

    # MTLand
    json_land = requests.get(
        'https://api.stellar.expert/explorer/public/asset/MTLand-GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V/holders?limit=200').json()
    # MTLMiner
    json_miner = requests.get(
        'https://api.stellar.expert/explorer/public/asset/MTLMiner-GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V/holders?limit=200').json()

    # competition
    # FOND
    rq = requests.get('https://horizon.stellar.org/accounts/GAIKBJYL5DZFHBL3R4HPFIA2U3ZEBTJ72RZLP444ACV24YZ2C73P6COM')
    competition_assets = {}

    for balance in rq.json()['balances']:
        if balance['asset_type'] == "native":
            competition_assets['XLM'] = float(balance['balance'])
        else:
            competition_assets[balance['asset_code']] = float(balance['balance'])
    # FOND safe desk
    safe_desk_assets = {}
    rq = requests.get('https://horizon.stellar.org/accounts/GAJIOTDOP25ZMXB5B7COKU3FGY3QQNA5PPOKD5G7L2XLGYJ3EDKB2SSS')
    for balance in rq.json()['balances']:
        if balance['asset_type'] == "native":
            safe_desk_assets['XLM'] = float(balance['balance'])
        else:
            safe_desk_assets[balance['asset_code']] = float(balance['balance'])
    rq = requests.get('https://horizon.stellar.org/accounts/GBBCLIYOIBVZSMCPDAOP67RJZBDHEDQ5VOVYY2VDXS2B6BLUNFS5242O')
    for balance in rq.json()['balances']:
        if balance['asset_type'] == "native":
            safe_desk_assets['XLM'] = float(balance['balance'])
        else:
            safe_desk_assets[balance['asset_code']] += float(balance['balance'])
    rq = requests.get('https://horizon.stellar.org/accounts/GC624CN4PZJX3YPMGRAWN4B75DJNT3AWIOLYY5IW3TWLPUAG6ER6IFE6')
    for balance in rq.json()['balances']:
        if balance['asset_type'] == "native":
            safe_desk_assets['XLM'] = float(balance['balance'])
        else:
            safe_desk_assets[balance['asset_code']] += float(balance['balance'])

    # aum
    s = requests.get(
        f'https://www.suissegold.eu/en/product/argor-heraeus-10-gram-gold-bullion-bar-999-9-fine?change-currency=EUR').text
    s = s[s.find('"offers":'):]
    # print(s)
    s = s[s.find('"price": "') + 10:]
    s = s[:s.find('"')]
    wks.update('B7', float(s))

    # print(json_land['_embedded']['records'])
    land_count = 0.0
    for landlord in json_land['_embedded']['records']:
        if landlord['account'] != 'GDX23CPGMQ4LN55VGEDVFZPAJMAUEHSHAMJ2GMCU2ZSHN5QF4TMZYPIS':
            land_count += float(landlord['balance']) / 10000000
    # print(land_count)
    wks.update('C31', land_count)
    miner_count = 0.0
    for minerlord in json_miner['_embedded']['records']:
        if minerlord['account'] != 'GDX23CPGMQ4LN55VGEDVFZPAJMAUEHSHAMJ2GMCU2ZSHN5QF4TMZYPIS':
            miner_count += float(minerlord['balance']) / 10000000
    wks.update('C33', miner_count)

    # exchange
    public_exchange = "GCVF74HQRLPAGTPFSYUAKGHSDSMBQTMVSLKWKUU65ULEN7TL4N56IPZ7"
    balances = {}
    rq = requests.get(f'https://horizon.stellar.org/accounts/{public_exchange}').json()
    # print(json.dumps(rq, indent=4))
    for balance in rq["balances"]:
        name = 'XLM' if balance["asset_type"] == 'native' else balance["asset_code"]
        balances[name] = balance["balance"]
    wks.update('F10', float(balances['XLM']))
    wks.update('F11', float(balances['EURMTL']))
    wks.update('F12', float(balances['EURDEBT']))
    wks.update('F13', float(balances['BTCMTL']))

    # exchange
    public_exchange = "GAEFTFGQYWSF5T3RVMBSW2HFZMFZUQFBYU5FUF3JT3ETJ42NXPDWOO2F"
    balances = {}
    rq = requests.get(f'https://horizon.stellar.org/accounts/{public_exchange}').json()
    # print(json.dumps(rq, indent=4))
    for balance in rq["balances"]:
        name = 'XLM' if balance["asset_type"] == 'native' else balance["asset_code"]
        balances[name] = balance["balance"]
    wks.update('H10', float(balances['XLM']))
    wks.update('H11', float(balances['EURMTL']))
    wks.update('H12', float(balances['EURDEBT']))

    # divs
    j = requests.get(
        f'https://horizon.stellar.org/accounts/GDX23CPGMQ4LN55VGEDVFZPAJMAUEHSHAMJ2GMCU2ZSHN5QF4TMZYPIS/operations?order=desc&limit=50').text
    j = json.loads(j)
    div_sum = 0
    for record in j["_embedded"]["records"]:
        # print('*',record)
        if record['type'] == 'payment' and 'GDNHQWZRZDZZBARNOH6VFFXMN6LBUNZTZHOKBUT7GREOWBTZI4FGS7IQ' == record['to']:
            div_sum = float(record['amount'])
            break
    wks.update('B10', div_sum)

    # donates
    donates = requests.get("https://raw.githubusercontent.com/montelibero-org/mtl/main/json/donation.json").json()
    donates_count = len(donates)
    last_pay_id = \
        fb.execsql("select first 1 d.id from t_div_list d where d.memo like '%donate%' order by d.id desc")[0][0]
    recipients_count = fb.execsql(f"select count(*) from t_payments p where p.id_div_list = {last_pay_id} " +
                                  f"and p.user_key <> 'GDEK5KGFA3WCG3F2MLSXFGLR4T4M6W6BMGWY6FBDSDQM6HXFMRSTEWBW'")[0][0]
    donates_sum = fb.execsql(f"select sum(p.user_div) from t_payments p where p.id_div_list = {last_pay_id} " +
                             f"and p.user_key <> 'GDEK5KGFA3WCG3F2MLSXFGLR4T4M6W6BMGWY6FBDSDQM6HXFMRSTEWBW'")[0][0]

    wks.update('B11', donates_count)
    wks.update('C11', float(donates_sum))
    wks.update('D11', int(recipients_count))
    wks.update('C18', competition_assets.get('EURMTL'))
    wks.update('D18', safe_desk_assets.get('EURMTL'))
    wks.update('D17', safe_desk_assets.get('EURDEBT'))

    wks.update('B2', now.strftime('%d.%m.%Y %H:%M:%S'))

    logger.info(f'all done {now}')


if __name__ == "__main__":
    update_main_report()
