import asyncio
import datetime
from stellar_sdk.sep.federation import resolve_stellar_address_async
from utils.stellar_utils import *
from scripts.mtl_exchange import check_fire

# https://docs.gspread.org/en/latest/

CITY_ASSETS = ['MTLDVL', 'MTLBRO', 'MTLGoldriver', 'MonteSol', 'MCITY136920', 'MonteAqua', 'MTLCAMP', ]
MABIZ_ASSETS = ['Agora', 'BIOM', 'FCM', 'GPA', 'iTrade', 'MTLBR', ]
DEFI_ASSETS = ['AUMTL', 'BTCMTL', 'EURMTL', 'MTLDefi', 'SATSMTL', ]
ISSUER_ASSETS = ['XLM', ]

COST_DATA = ['FCM_COST', 'MTLBR_COST', 'MTL_COST_N', 'LAND_AMOUNT', 'LAND_COST', 'MTLDVL_COST', ]


@logger.catch
async def update_main_report():
    agc = await agcm.authorize()

    # Open a sheet from a spreadsheet in one go
    ss = await agc.open("MTL Report")
    wks = await ss.worksheet("RawData")

    # Update a range of cells using the top left corner address
    now = datetime.now()
    # print(now.strftime('%d.%m.%Y %H:%M:%S'))

    # usd
    rq = requests.get(f'http://api.currencylayer.com/live?access_key={config.currencylayer_id}&format=1&currencies=EUR')
    await wks.update('B4', float(rq.json()['quotes']['USDEUR']))

    # BTC,XLM
    rq = requests.get(f'http://api.coinlayer.com/api/live?access_key={config.coinlayer_id}&symbols=BTC,XLM')
    await wks.update('B5', float(rq.json()['rates']['BTC']))
    await wks.update('B6', float(rq.json()['rates']['XLM']))

    # MTL
    rq = requests.get(
        'https://horizon.stellar.org/assets?asset_code=MTL&asset_issuer=GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V')
    await wks.update('B9', float(rq.json()['_embedded']['records'][0]['amount']))
    # MTLRECT
    rq = requests.get(
        'https://horizon.stellar.org/assets?asset_code=MTLRECT&asset_issuer=GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V')
    await wks.update('B10', float(rq.json()['_embedded']['records'][0]['amount']))
    # MTLCITY
    # rq = requests.get(
    #    'https://horizon.stellar.org/assets?asset_code=MTLCITY&asset_issuer=GDUI7JVKWZV4KJVY4EJYBXMGXC2J3ZC67Z6O5QFP4ZMVQM2U5JXK2OK3')
    # await wks.update('J9', float(rq.json()['_embedded']['records'][0]['amount']))

    # cost data
    cost_data = {}

    # defi
    assets, data = await get_balances(MTLAddresses.public_fund_defi, return_data=True)
    cost_data.update(data)

    good_assets = []
    for ms in DEFI_ASSETS:
        good_assets.append([ms, float(assets.get(ms))])
    await wks.update('A16', good_assets)

    # CITY
    assets, data = await get_balances(MTLAddresses.public_fund_city, return_data=True)
    cost_data.update(data)

    good_assets = []
    for ms in CITY_ASSETS:
        good_assets.append([ms, float(assets.get(ms))])
    await wks.update('C16', good_assets)

    # mabiz
    assets, data = await get_balances(MTLAddresses.public_fund_mabiz, return_data=True)
    cost_data.update(data)

    good_assets = []
    for ms in MABIZ_ASSETS:
        good_assets.append([ms, float(assets.get(ms))])
    await wks.update('E16', good_assets)

    # mabiz
    assets, data = await get_balances(MTLAddresses.public_issuer, return_data=True)
    cost_data.update(data)

    good_assets = []
    for ms in ISSUER_ASSETS:
        good_assets.append([ms, float(assets.get(ms))])
    await wks.update('I16', good_assets)

    # FOND safe desk
    # safe_desk_assets = {}
    # debt_holders = await stellar_get_mtl_holders(eurdebt_asset)
    # for record in debt_holders:
    #    if record['id'] != public_fund:
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
    await wks.update('B7', float(s))

    # divs
    div_sum = await cmd_show_data(MTLAddresses.public_div, 'LAST_DIVS', True)
    await wks.update('B11', int(float(div_sum[0])))

    # defi
    defi_balance = 0
    debank = requests.get("https://api.debank.com/token/balance_list"
                          "?user_addr=0x0358d265874b5cf002d1801949f1cee3b08fa2e9&chain=bsc")
    if debank:
        debank = debank.json()
        for row in debank['data']:
            defi_balance += row['amount'] * row['price']
    await asyncio.sleep(2)
    debank = requests.get("https://api.debank.com/portfolio/project_list"
                          "?user_addr=0x0358d265874b5cf002d1801949f1cee3b08fa2e9")
    if debank:
        debank = debank.json()
        for row in debank['data']:
            for row2 in row['portfolio_item_list']:
                for row3 in row2['asset_token_list']:
                    defi_balance += row3['amount'] * row3['price']
        await wks.update('E4', int(defi_balance))
    else:
        logger.warning(f'debank error - {debank}')
        #send_admin_message(session, 'debank error')

    # amount
    rq = requests.get(
        'https://horizon.stellar.org/assets?asset_code=MTLDefi&asset_issuer=GBTOF6RLHRPG5NRIU6MQ7JGMCV7YHL5V33YYC76YYG4JUKCJTUP5DEFI')
    await wks.update('E5', float(rq.json()['_embedded']['records'][0]['amount']))
    # buyback balance
    bot_balances = await get_balances(MTLAddresses.public_defi)
    defi_btc = float(bot_balances.get('BTCMTL', 0)) + float(bot_balances.get('SATSMTL', 0)) / 100000000
    await wks.update('E6', defi_btc)

    # cost data
    update_data = []
    print(cost_data)
    for ms in COST_DATA:
        # update_data.append([ms, float(assets[ms])])
        if ms in cost_data:
            update_data.append([ms, float(decode_data_value(cost_data[ms]))])
        else:
            update_data.append([ms, 0])
    await wks.update('G16', update_data)

    await wks.update('B2', now.strftime('%d.%m.%Y %H:%M:%S'))

    logger.info(f'all done {now}')


@logger.catch
async def update_fire(session: Session):
    agc = await agcm.authorize()
    ss = await agc.open("MTL Report")
    wks = await ss.worksheet("AutoData")
    if 'book value of 1 token' != (await wks.cell(35, 2)).value:
        send_admin_message(session, 'bad fire value')
        raise Exception('bad fire value')
    cost_fire = (await wks.cell(35, 4)).value
    logger.info(f'cost_fire {cost_fire}')
    cost_fire = float(cost_fire.replace(',', '.')) * 0.8
    await check_fire(cost_fire)


async def update_guarantors_report():
    agc = await agcm.authorize()

    # Open a sheet from a spreadsheet in one go
    ss = await agc.open("EURMTL Guarantors")
    wks = await ss.worksheet("Guarantors")

    # Update a range of cells using the top left corner address
    now = datetime.now()
    # print(now.strftime('%d.%m.%Y %H:%M:%S'))

    # user_entered_format = gspread_formatting.get_user_entered_format(wks,'D2')
    # print(user_entered_format)
    # gspread_formatting.format_cell_range(wks,'D4',
    #   gspread_formatting.CellFormat(numberFormat={"type":"DATE","pattern":"dd.mm.yyyy"}))
    # user_entered_format = gspread_formatting.get_user_entered_format(wks,'D4')
    # print(user_entered_format)
    # gspread_formatting.batch_updater(gc)
    address_list = await wks.col_values(2)
    address_list.pop(0)
    address_list.pop(0)
    len_address_list = len(address_list)

    all_accounts = await stellar_get_mtl_holders(MTLAssets.eurdebt_asset)
    for account in all_accounts:
        if account["id"] in address_list:
            pass
        else:
            balances = account['balances']
            found = list(filter(lambda x: x.get('asset_code') and x.get('asset_code') == 'EURDEBT', balances))
            if float(found[0]['balance']) > 1:
                address_list.append(account["id"])

    if len(address_list) > len_address_list:
        update_list = []
        for account in address_list:
            update_list.append([account])
        await wks.update('B3', update_list)

    date_list = await wks.col_values(4)
    date_list.pop(0)
    #    date_list.pop(0)

    update_list = []

    for idx, address in enumerate(address_list):
        eur_sum = ''
        debt_sum = ''
        if idx == len(date_list):
            date_list.append('')
        if address and (len(address) == 56):
            # print(val)
            # get balance
            balances = await get_balances(address)
            eur_sum = round(float(balances.get('EURMTL', 0)))
            debt_sum = float(balances.get('EURDEBT', 0))
            if eur_sum >= debt_sum:
                dt = ''
            else:
                dt = date_list[idx] if len(date_list[idx]) > 3 else now.strftime('%d.%m.%Y')

        dt_google = ''  # if dt == '' else (
        # datetime.strptime(dt, '%d.%m.%Y') - datetime(1899, 12, 30)).days
        update_list.append([dt_google, eur_sum, debt_sum])

    await wks.update('E3', update_list)
    # wks.format("E3:E40", {"numberFormat": {"type": "DATE", "pattern": "dd.mm.yyyy"}})

    # rects
    address_list = await wks.col_values(3)
    address_list.pop(0)
    address_list.pop(0)
    update_list = []
    for address in address_list:
        if len(address) == 56:
            balances = await get_balances(address)
            update_list.append([balances.get('MTLRECT', 0)])
        else:
            update_list.append(['=['])

    await wks.update('H3', update_list)

    # dt1 = datetime.strptime(record["created_at"], '%Y-%m-%dT%H:%M:%SZ')
    # print(update_list)
    await wks.update('B2', now.strftime('%d.%m.%Y %H:%M:%S'))

    logger.info(f'report Guarantors all done {now}')


@logger.catch
async def update_top_holders_report(session: Session):
    agc = await agcm.authorize()

    now = datetime.now()

    ss = await agc.open("MTL_TopHolders")
    wks = await ss.worksheet("TopHolders")

    vote_list = await cmd_gen_mtl_vote_list()
    vote_list = await stellar_add_mtl_holders_info(vote_list)

    for vote in vote_list:
        vote[0] = await resolve_account(vote[0]) if vote[1] > 400 else vote[0][:4] + '..' + vote[0][-4:]
        vote.pop(4)

    vote_list.sort(key=lambda k: k[2], reverse=True)

    await wks.update('B2', vote_list)
    await wks.update('G1', now.strftime('%d.%m.%Y %H:%M:%S'))

    records = await wks.get_values('F2:F21')
    gd_link = 'https://docs.google.com/spreadsheets/d/1HSgK_QvK4YmVGwFXuW5CmqgszDxe99FAS2btN3FlQsI/edit#gid=171831156'
    for record in records:
        if record[0] != '0':
            text = f'You need update votes <a href="{gd_link}">more info</a>'
            cmd_add_message(session, MTLChats.SignGroup, text, True)
            break

    logger.info(f'report topholders all done {now}')


@logger.catch
async def update_bdm_report():
    agc = await agcm.authorize()

    now = datetime.now()

    ss = await agc.open("MTL_TopHolders")
    wks = await ss.worksheet("BDM")

    bdm_list = await cmd_show_guards_list()

    for bdm in bdm_list:
        if len(bdm[0]) == 56:
            bdm.append(await resolve_account(bdm[0]))
        if len(bdm[2]) == 56:
            bdm.append(await resolve_account(bdm[2]))

    await wks.update('A2', bdm_list)
    await wks.update('G1', now.strftime('%d.%m.%Y %H:%M:%S'))

    logger.info(f'update bdm_report all done {now}')


@logger.catch
async def update_bim_data(session: Session):
    agc = await agcm.authorize()

    now = datetime.now()

    ss = await agc.open("MTL_BIM_register")
    wks = await ss.worksheet("List")

    use_date_list = []
    mtl_amount_list = []
    data = await wks.get_all_values()
    for record in data[2:]:
        mtl_amount = 0
        mmwb_date = None
        if len(record[4]) == 56 and record[10] == 'TRUE':
            use_date = get_mmwb_use_date(session, record[4])
            if use_date:
                mmwb_date = use_date.strftime('%d.%m.%Y %H:%M:%S')
            # get balance
            balances = await get_balances(record[4])
            mtl_amount = float(balances.get('MTL', 0) + balances.get('MTLRECT', 0))
        mtl_amount_list.append([mtl_amount])
        use_date_list.append([mmwb_date])

    await wks.update('R3', mtl_amount_list)
    await wks.update('U3', use_date_list, value_input_option='USER_ENTERED')
    await wks.update('AG1', now.strftime('%d.%m.%Y %H:%M:%S'))
    logger.info(f'update bdm_report all done {now}')


async def update_mmwb_report(session: Session):
    agc = await agcm.authorize()

    now = datetime.now()

    ss = await agc.open("MMWB MM TABLE")
    wks = await ss.worksheet("DATA")

    # check structure
    records = await wks.get_values('D1:E1')
    if records != [['EURMTL', 'валюта2']]:
        print(records)
        raise Exception('wrong structure')
    records = await wks.get_values('B2:B6')
    if records[0][0] != 'GDEMWIXGF3QQE7CJIOKWWMJAXAWGINJRR6DOOOSNO3C4UQGPDOA3OBOT':
        print(records)
        raise Exception('wrong structure')

    # update data
    update_data = []
    balances = await get_balances(MTLAddresses.public_exchange_eurmtl_xlm)
    update_data.append([balances.get('EURMTL', 0), balances.get('XLM', 0)])
    balances = await get_balances(MTLAddresses.public_exchange_eurmtl_usdc)
    update_data.append([balances.get('EURMTL', 0), balances.get('USDC', 0)])
    balances = await get_balances(MTLAddresses.public_exchange_eurmtl_sats)
    update_data.append([balances.get('EURMTL', 0), balances.get('SATSMTL', 0)])
    balances = await get_balances(MTLAddresses.public_exchange_eurmtl_btc)
    update_data.append([balances.get('EURMTL', 0), balances.get('BTCMTL', 0)])
    balances = await get_balances(MTLAddresses.public_fire)
    update_data.append([balances.get('EURMTL', 0), balances.get('MTL', 0)])

    await wks.update('D2', update_data)

    records = await wks.get_values('H2:H5')
    for record in records:
        value = float(record[0].replace(',', '.'))
        if value < 0.2 or value > 0.8:
            send_admin_message(session, f'update_mmwb_report balance error {value}')

    await wks.update('J1', now.strftime('%d.%m.%Y %H:%M:%S'))
    logger.info(f'update mmwb_report all done {now}')


def my_float(s):
    result = round(float(s), 2) if len(str(s)) > 1 else s
    return result


async def update_airdrop():
    agc = await agcm.authorize()
    client = AiohttpClient()

    # Open a sheet from a spreadsheet in one go
    ss = await agc.open("MTL_reestr")
    wks = await ss.worksheet("EUR_GNRL")

    # Update a range of cells using the top left corner address
    now = datetime.now()
    # print(now.strftime('%d.%m.%Y %H:%M:%S'))

    address_list = await wks.col_values(4)
    fed_address_list = await wks.col_values(5)
    start_pos = int((await wks.cell(1, 1)).value)

    start_pos = start_pos if start_pos > 2 else 2

    max_length = len(address_list) if len(address_list) > len(fed_address_list) else len(fed_address_list)

    # fill addresses

    # print(address_list)
    # print(fed_address_list)

    for idx in range(start_pos, max_length):
        if len(address_list) > idx:  # if address more that federal
            if (len(address_list[idx]) < 10) and (len(fed_address_list) >= idx) and (
                    len(fed_address_list[idx]) > 5) and (fed_address_list[idx].count('*') > 0):
                try:
                    # print(address_list[idx], fed_address_list[idx])
                    address = await resolve_stellar_address_async(fed_address_list[idx], client=client)
                    # print(address.account_id)
                    await wks.update(f'D{idx + 1}', address.account_id)
                except:
                    print('Resolving error', address_list[idx], fed_address_list[idx])
        else:  # if federal more that address
            if (len(fed_address_list[idx]) > 5) and (fed_address_list[idx].count('*') > 0):
                # print(fed_address_list[idx], '***')
                address = await resolve_stellar_address_async(fed_address_list[idx], client=client)
                # print(address.account_id)
                await wks.update(f'D{idx + 1}', address.account_id)

    address_list = await wks.col_values(4)
    address_list.pop(0)
    address_list.pop(0)
    update_list = []
    start_pos = start_pos if start_pos > 3 else 3

    for idx, address in enumerate(address_list[start_pos:]):
        mtl_sum = ''
        eurmtl_sum = ''
        xlm_sum = ''
        sats_sum = ''
        if address and (len(address) == 56):
            # print(val)
            # get balance
            balance_dic: dict = await get_balances(address)
            mtl_sum = my_float(balance_dic.get('MTL', ''))
            eurmtl_sum = my_float(balance_dic.get('EURMTL', ''))
            xlm_sum = my_float(balance_dic.get('XLM', ''))
            sats_sum = my_float(balance_dic.get('SATSMTL', ''))

        update_list.append([xlm_sum, eurmtl_sum, mtl_sum, sats_sum])

    # print(update_list)
    await wks.update(f'K{start_pos + 3}', update_list)
    await wks.update('O2', now.strftime('%d.%m.%Y %H:%M:%S'))
    await client.close()

    logger.info(f'report 3 all done {now}')


async def update_donate_report(session: Session):
    agc = await agcm.authorize()


#    # Open a sheet from a spreadsheet in one go
#    wks = gc.open("MTL_TopHolders").worksheet("Donates")
#
#    # Update a range of cells using the top left corner address
#    now = datetime.now()
#
#    # donates
#
#    updates = fb.execsql("""select user_key, iif(total_pay > 0, sl.total_pay, 0) total_pay,
#    coalesce(total_receive, 0) total_receive,
#    (select coalesce(sum(p.user_calc - p.user_div), 0)
#          from t_payments p
#         where p.id_div_list = sl.max_div_num
#           and p.user_key = sl.user_key) last_pay,
#       (select coalesce(sum(p.user_div), 0)
#          from t_payments p
#         where p.id_div_list = sl.max_donate_num
#           and p.user_key = sl.user_key) last_receive
#  from (select pp.user_key,
#               (select sum(p.user_calc - p.user_div)
#                  from t_payments p
#                  join t_div_list d on d.id = p.id_div_list
#                 where p.user_key = pp.user_key
#                   and d.memo like '%div%'
#                   and p.was_packed = 1) total_pay,
#               (select sum(p.user_div)
#                  from t_payments p
#                  join t_div_list d on d.id = p.id_div_list
#                 where p.user_key = pp.user_key
#                   and d.memo like '%donate%'
#                   and p.was_packed = 1) total_receive,
#               (select first 1 d.id
#                  from t_div_list d
#                 where d.memo like '%div%'
#                 order by d.id desc) max_div_num,
#               (select first 1 d.id
#                  from t_div_list d
#                 where d.memo like '%donate%'
#                 order by d.id desc) max_donate_num
#          from t_payments pp
#          join t_div_list dd on dd.id = pp.id_div_list and
#                dd.pay_type = 0
#         group by pp.user_key) sl
# where (sl.total_pay > 0) or (total_receive > 0)
#    """)
#    update_list = []
#
#    for key in updates:
#        account_name = address_id_to_username(key[0])
#        update_list.append([account_name, key[3], key[4], key[1], key[2]])
#
#    update_list.append(['', '', '', '', ''])
#    update_list.append(['', '', '', '', ''])
#    update_list.append(['', '', '', '', ''])
#
#    # print(update_list)
#    await wks.update('A2', update_list)
#    await wks.update('G1', now.strftime('%d.%m.%Y %H:%M:%S'))
#    logger.info(f'donate report done {now}')


async def update_donates_new():
    agc = await agcm.authorize()

    # Update a range of cells using the top left corner address
    now = datetime.now()
    # Open a sheet from a spreadsheet in one go
    ss = await agc.open("MTL_TopHolders")
    wks = await ss.worksheet("DonatesNew")

    update_list = await cmd_show_donates(return_table=True)

    await wks.update('A2', update_list)
    await wks.update('E1', now.strftime('%d.%m.%Y %H:%M:%S'))
    update_list.append(['', '', ''])
    update_list.append(['', '', ''])
    update_list.append(['', '', ''])

    logger.info(f'new done {now}')


async def update_wallet_report(session: Session):
    agc = await agcm.authorize()

    # Open a sheet from a spreadsheet in one go
    ss = await agc.open("Табличка с кошелька")
    wks = await ss.worksheet("RawData")

    # Update a range of cells using the top left corner address
    now = datetime.now()

    list_wallet = get_wallet_info(session)

    update_list = []

    for wallet in list_wallet:
        balances = await get_balances(wallet[0])
        if balances:
            update_list.append([wallet[0], wallet[1], wallet[2], wallet[3].strftime('%d.%m.%Y %H:%M:%S'),
                                float(balances.get('EURMTL', 0)),
                                float(balances.get('MTL', 0))])

    # print(update_list)
    # print(update_list)
    await wks.update('A4', update_list)
    await wks.update('H1', now.strftime('%d.%m.%Y %H:%M:%S'))

    logger.info(f'all done {now}')


async def update_wallet_report2(session: Session):
    agc = await agcm.authorize()

    # Open a sheet from a spreadsheet in one go
    ss = await agc.open("Табличка с кошелька")
    wks = await ss.worksheet("DayByDay")

    # Update a range of cells using the top left corner address
    now = datetime.now()

    update_data = [(now - timedelta(days=1)).strftime('%d.%m.%Y')]

    for record in get_wallet_stats(session):
        update_data.append(record)
        # update_data.append(record[1])
        # update_data.append(record[2])
        # update_data.append(record[3])

    update_data.append(get_log_count(session, 'callback'))
    update_data.append(get_log_count(session, 'sign'))

    update_data = [update_data, ['LAST']]

    last_row = (await wks.find('LAST', in_column=1)).row

    # print(update_list)
    await wks.update(f'A{last_row}', update_data)
    await wks.update('K1', now.strftime('%d.%m.%Y %H:%M:%S'))

    logger.info(f'all done {now}')


async def update_export(session: Session):
    agc = await agcm.authorize()

    # Open a sheet from a spreadsheet in one go
    ss = await agc.open("test export 4")
    wks = await ss.worksheet("2023")

    # Update a range of cells using the top left corner address
    now = datetime.now()

    update_list = []

    # print(update_list)
    last_row = (await wks.find('LAST', in_column=1)).row
    last_id = (await wks.get_values(f'A{last_row - 1}'))[0][0]

    list_operation = get_operations(session, last_id)
    ##fb.execsql("select first 3000 o.id, o.dt, o.operation, o.amount1, o.code1, o.amount2, o.code2, "
    #                        "o.from_account, o.for_account, o.ledger from t_operations o "
    #                        "where o.id > ? order by o.id", (last_id,))
    for record in list_operation:
        update_list.append(
            [record.id, record.dt.strftime('%d.%m.%Y %H:%M:%S'), record.operation, float(record.amount1), record.code1,
             None if record.amount2 is None else float(cast(float, record.amount2)), record.code2, record.from_account,
             record.for_account, None, None, record.ledger])

    update_list.append(['LAST', ])
    await wks.update(f'A{last_row}', update_list, value_input_option='USER_ENTERED')
    # await wks.update('H1', now.strftime('%d.%m.%Y %H:%M:%S'))

    logger.info(f'all done {now}')


async def main():
    from db.quik_pool import quik_pool

    logger.add("update_report.log", rotation="1 MB")

    await asyncio.gather(
        update_main_report(),
        update_guarantors_report(),
        update_bim_data(quik_pool()),
        update_top_holders_report(quik_pool()),
        update_mmwb_report(quik_pool()),
        update_donates_new(),
        update_wallet_report(quik_pool()),
        update_wallet_report2(quik_pool()),
        update_export(quik_pool())
    )

    await update_fire(quik_pool())


if __name__ == "__main__":
    # asyncio.run(update_airdrop())  # only from skynet
    #from db.quik_pool import quik_pool
    #asyncio.run(update_mmwb_report(quik_pool()))  # only from skynet
    #exit()
    #from db.quik_pool import quik_pool
    #asyncio.run(update_mmwb_report(quik_pool()))
    asyncio.run(main())
