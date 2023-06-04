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

# MASTERASSETS = ['BTCDEBT',  'EUR', 'EURDEBT',  'GRAFDRON',  'MonteAqua',
#                'MonteCrafto', 'MTL',  'MTLBRO', 'MTLCAMP', 'MTLCITY', 'XLM', 'MTLand',
#                'MTLMiner', 'MTLDVL', 'GPACAR', 'SwapCoin',  'MrxpInvest',   'BIOMinvest',
#                 'USDC', 'MonteSol', 'MTLGoldriver']

CITY_ASSETS = ['MTLDVL', 'MTLBRO', 'MTLGoldriver', 'MonteSol', 'MCITY136920', 'MonteAqua', 'MTLCAMP', ]
MABIZ_ASSETS = ['Agora', 'BIOM', 'FCM', 'GPA', 'iTrade', 'MTLBR', ]
DEFI_ASSETS = ['AUMTL', 'BTCMTL', 'EURMTL', 'MTLDefi', 'SATSMTL', ]
ISSUER_ASSETS = ['XLM', ]

COST_DATA = ['FCM_COST', 'MTLBR_COST', 'MTL_COST_N', 'LAND_AMOUNT', 'LAND_COST', 'MTLDVL_COST', ]


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
    wks.update('B10', float(rq.json()['_embedded']['records'][0]['amount']))
    # MTLCITY
    # rq = requests.get(
    #    'https://horizon.stellar.org/assets?asset_code=MTLCITY&asset_issuer=GDUI7JVKWZV4KJVY4EJYBXMGXC2J3ZC67Z6O5QFP4ZMVQM2U5JXK2OK3')
    # wks.update('J9', float(rq.json()['_embedded']['records'][0]['amount']))

    # cost data
    cost_data = {}

    # defi
    assets, data = await mystellar.get_balances(mystellar.public_fund_defi, return_data=True)
    cost_data.update(data)

    good_assets = []
    for ms in DEFI_ASSETS:
        good_assets.append([ms, float(assets.get(ms))])
    wks.update('A16', good_assets)

    # CITY
    assets, data = await mystellar.get_balances(mystellar.public_fund_city, return_data=True)
    cost_data.update(data)

    good_assets = []
    for ms in CITY_ASSETS:
        good_assets.append([ms, float(assets.get(ms))])
    wks.update('C16', good_assets)

    # mabiz
    assets, data = await mystellar.get_balances(mystellar.public_fund_mabiz, return_data=True)
    cost_data.update(data)

    good_assets = []
    for ms in MABIZ_ASSETS:
        good_assets.append([ms, float(assets.get(ms))])
    wks.update('E16', good_assets)

    # mabiz
    assets, data = await mystellar.get_balances(mystellar.public_issuer, return_data=True)
    cost_data.update(data)

    good_assets = []
    for ms in ISSUER_ASSETS:
        good_assets.append([ms, float(assets.get(ms))])
    wks.update('I16', good_assets)

    # FOND safe desk
    # safe_desk_assets = {}
    # debt_holders = await mystellar.stellar_get_mtl_holders(mystellar.eurdebt_asset)
    # for record in debt_holders:
    #    if record['id'] != mystellar.public_fund:
    #        found = list(filter(lambda x: x.get('asset_code') == 'EURDEBT', record['balances']))
    #        if float(found[0]['balance']) > 0:
    #            for balance in record['balances']:
    #                if balance['asset_type'] == "native":
    #                    safe_desk_assets['XLM'] = float(balance['balance'])
    #                else:
    #                    safe_desk_assets[balance['asset_code']] = float(balance['balance']) + \
    #                                                              safe_desk_assets.get(balance['asset_code'], 0)

    # aum
    s = requests.get(
        f'https://www.suissegold.eu/en/product/argor-heraeus-10-gram-gold-bullion-bar-999-9-fine?change-currency=EUR').text
    s = s[s.find('"offers":'):]
    # print(s)
    s = s[s.find('"price": "') + 10:]
    s = s[:s.find('"')]
    wks.update('B7', float(s))

    # divs
    div_sum = await mystellar.cmd_show_data(mystellar.public_div, 'LAST_DIVS', True)
    wks.update('B11', int(float(div_sum[0])))

    # defi
    defi_balance = 0
    debank = requests.get("https://api.debank.com/token/balance_list"
                          "?user_addr=0x0358d265874b5cf002d1801949f1cee3b08fa2e9&chain=bsc").json()
    for row in debank['data']:
        defi_balance += row['amount'] * row['price']
    debank = requests.get("https://api.debank.com/portfolio/project_list"
                          "?user_addr=0x0358d265874b5cf002d1801949f1cee3b08fa2e9").json()
    for row in debank['data']:
        for row2 in row['portfolio_item_list']:
            for row3 in row2['asset_token_list']:
                defi_balance += row3['amount'] * row3['price']
    wks.update('E4', int(defi_balance))

    # amount
    rq = requests.get(
        'https://horizon.stellar.org/assets?asset_code=MTLDefi&asset_issuer=GBTOF6RLHRPG5NRIU6MQ7JGMCV7YHL5V33YYC76YYG4JUKCJTUP5DEFI')
    wks.update('E5', float(rq.json()['_embedded']['records'][0]['amount']))
    # buyback balance
    bot_balances = await mystellar.get_balances(mystellar.public_defi)
    defi_btc = float(bot_balances.get('BTCMTL', 0)) + float(bot_balances.get('SATSMTL', 0)) / 100000000
    wks.update('E6', defi_btc)

    # cost data
    update_data = []
    print(cost_data)
    for ms in COST_DATA:
        # update_data.append([ms, float(assets[ms])])
        if ms in cost_data:
            update_data.append([ms, float(mystellar.decode_data_value(cost_data[ms]))])
        else:
            update_data.append([ms, 0])
    wks.update('G16', update_data)

    wks.update('B2', now.strftime('%d.%m.%Y %H:%M:%S'))

    logger.info(f'all done {now}')


@logger.catch
async def update_fire():
    gc = gspread.service_account('mtl-google-doc.json')
    wks = gc.open("MTL Report").worksheet("AutoData")
    if 'book value of 1 token' != wks.cell(35, 2).value:
        fb.send_admin_message('bad fire value')
        raise Exception('bad fire value')
    cost_fire = wks.cell(35, 4).value
    logger.info(f'cost_fire {cost_fire}')
    cost_fire = float(cost_fire.replace(',', '.')) * 0.8
    await check_fire(cost_fire)


if __name__ == "__main__":
    logger.add("update_report.log", rotation="1 MB")
    asyncio.run(update_main_report())
    asyncio.run(update_fire())
