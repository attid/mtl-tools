import asyncio
import datetime
import gspread
import json
import requests
from loguru import logger
import fb
import mystellar
from mtl_exchange import check_fire
from settings import currencylayer_id, coinlayer_id

# https://docs.gspread.org/en/latest/

MASTERASSETS = ['BTCDEBT', 'BTCMTL', 'EUR', 'EURDEBT', 'EURMTL', 'GPA', 'GRAFDRON', 'iTrade', 'MonteAqua',
                'MonteCrafto', 'MTL', 'MTLBR', 'MTLBRO', 'MTLCAMP', 'MTLCITY', 'Agora', 'XLM', 'MTLand', 'AUMTL',
                'MTLMiner', 'MTLDVL', 'GPACAR', 'SwapCoin', 'BIOM', 'MrxpInvest', 'MTLDefi', 'FCM', 'BIOMinvest',
                'SATSMTL', 'USDC', 'MonteSol', 'MTLGoldriver']

CITYASSETS = ['MTLDVL', 'MTLBRO', 'MTLGoldriver', 'MonteSol', 'MCITY136920', 'MonteAqua', 'MTLCAMP']


@logger.catch
async def update_main_report():
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
    # MTLRECT
    rq = requests.get(
        'https://horizon.stellar.org/assets?asset_code=MTLRECT&asset_issuer=GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V')
    wks.update('C9', float(rq.json()['_embedded']['records'][0]['amount']))
    # MTLCITY
    rq = requests.get(
        'https://horizon.stellar.org/assets?asset_code=MTLCITY&asset_issuer=GDUI7JVKWZV4KJVY4EJYBXMGXC2J3ZC67Z6O5QFP4ZMVQM2U5JXK2OK3')
    wks.update('J9', float(rq.json()['_embedded']['records'][0]['amount']))

    #cost data
    cost_data = {}

    # FOND
    rq = requests.get('https://horizon.stellar.org/accounts/GDX23CPGMQ4LN55VGEDVFZPAJMAUEHSHAMJ2GMCU2ZSHN5QF4TMZYPIS')
    cost_data.update(rq.json()['data'])
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

    # CITY
    rq = requests.get('https://horizon.stellar.org/accounts/GDUI7JVKWZV4KJVY4EJYBXMGXC2J3ZC67Z6O5QFP4ZMVQM2U5JXK2OK3')
    assets = []
    cost_data.update(rq.json()['data'])

    for balance in rq.json()['balances']:
        if balance['asset_type'] == "native":
            assets.append(['XLM', float(balance['balance'])])
        else:
            assets.append([balance['asset_code'], float(balance['balance'])])
    goodassets = []
    for ms in CITYASSETS:
        asset = list(filter(lambda x: x[0] == ms, assets))
        if asset:
            asset = list(filter(lambda x: x[0] == ms, assets))[0]
        else:
            asset = [ms, 0]
        goodassets.append(asset)
    wks.update('I14', goodassets)


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
    debt_holders = await mystellar.stellar_get_mtl_holders(mystellar.eurdebt_asset)
    for record in debt_holders:
        if record['id'] != mystellar.public_fund:
            found = list(filter(lambda x: x.get('asset_code') == 'EURDEBT', record['balances']))
            if float(found[0]['balance']) > 0:
                for balance in record['balances']:
                    if balance['asset_type'] == "native":
                        safe_desk_assets['XLM'] = float(balance['balance'])
                    else:
                        safe_desk_assets[balance['asset_code']] = float(balance['balance']) + \
                                                                  safe_desk_assets.get(balance['asset_code'], 0)

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
    exchange_balances = {}
    for bot in mystellar.exchange_bots:
        bot_balances = await mystellar.get_balances(bot)
        for balance in bot_balances:
            exchange_balances[balance] = bot_balances[balance] + exchange_balances.get(balance, 0)
    # {'EURMTL': 66008.3838227, 'XLM': 68700.34405200001, 'BTCMTL': 1.0014920999999999, 'SATSMTL': 9601261.275270201, 'USDC': 5338.6724997, 'MTL': 0.0}
    wks.update('E18', exchange_balances['EURMTL'])
    wks.update('E30', exchange_balances['XLM'])
    wks.update('E15', exchange_balances['BTCMTL'])
    wks.update('E42', exchange_balances['SATSMTL'])
    wks.update('E43', exchange_balances['USDC'])

    # divs
    div_sum = await mystellar.cmd_show_data(mystellar.public_div, 'LAST_DIVS', True)
    wks.update('B10', int(float(div_sum[0])))

    # defi
    defi_balance = 0
    debank = requests.get("https://api.debank.com/token/balance_list?user_addr=0x0358d265874b5cf002d1801949f1cee3b08fa2e9&chain=bsc").json()
    for row in debank['data']:
        defi_balance += row['amount'] * row['price']
    debank = requests.get("https://api.debank.com/portfolio/project_list?user_addr=0x0358d265874b5cf002d1801949f1cee3b08fa2e9").json()
    for row in debank['data']:
        for row2 in row['portfolio_item_list']:
            for row3 in row2['asset_token_list']:
                defi_balance += row3['amount'] * row3['price']
    wks.update('E4', int(defi_balance))
    #amount
    rq = requests.get(
        'https://horizon.stellar.org/assets?asset_code=MTLDefi&asset_issuer=GBTOF6RLHRPG5NRIU6MQ7JGMCV7YHL5V33YYC76YYG4JUKCJTUP5DEFI')
    wks.update('E5', float(rq.json()['_embedded']['records'][0]['amount']))
    # buyback balance
    bot_balances = await mystellar.get_balances(mystellar.public_defi)
    wks.update('E6', float(bot_balances.get('BTCMTL',0)))


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

    # cost data
    update_data = []
    for data_name in cost_data:
        if data_name.find('_COST') != -1 or data_name.find('_AMOUNT') != -1:
            update_data.append([data_name, float(mystellar.decode_data_value(cost_data[data_name]))])
    wks.update('L10', update_data)

    wks.update('B2', now.strftime('%d.%m.%Y %H:%M:%S'))

    logger.info(f'all done {now}')


@logger.catch
async def update_fire():
    gc = gspread.service_account('mtl-google-doc.json')
    wks = gc.open("MTL Report").worksheet("AutoData")
    cost_fire = wks.cell(32, 4).value
    logger.info(f'cost_fire {cost_fire}')
    cost_fire = float(cost_fire.replace(',', '.')) * 0.8
    await check_fire(cost_fire)


if __name__ == "__main__":
    logger.add("update_report.log", rotation="1 MB")
    asyncio.run(update_main_report())
    asyncio.run(update_fire())
