import asyncio

import gspread
import gspread_asyncio
import datetime
import requests
from loguru import logger

import fb
# import gspread_formatting
# import json
# from settings import currencylayer_id, coinlayer_id
# https://docs.gspread.org/en/latest/
import mystellar


@logger.catch
async def update_guarantors_report():
    gc = gspread.service_account('mtl-google-doc.json')

    # Open a sheet from a spreadsheet in one go
    wks = gc.open("EURMTL Guarantors").worksheet("Guarantors")

    # Update a range of cells using the top left corner address
    now = datetime.datetime.now()
    # print(now.strftime('%d.%m.%Y %H:%M:%S'))

    # user_entered_format = gspread_formatting.get_user_entered_format(wks,'D2')
    # print(user_entered_format)
    # gspread_formatting.format_cell_range(wks,'D4',
    #   gspread_formatting.CellFormat(numberFormat={"type":"DATE","pattern":"dd.mm.yyyy"}))
    # user_entered_format = gspread_formatting.get_user_entered_format(wks,'D4')
    # print(user_entered_format)
    # gspread_formatting.batch_updater(gc)
    address_list = wks.col_values(2)
    address_list.pop(0)
    address_list.pop(0)
    len_address_list = len(address_list)

    all_accounts = await mystellar.stellar_get_mtl_holders(mystellar.eurdebt_asset)
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
        wks.update('B3', update_list)

    date_list = wks.col_values(4)
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
            balances = await mystellar.get_balances(address)
            eur_sum = round(float(balances.get('EURMTL', 0)))
            debt_sum = float(balances.get('EURDEBT', 0))
            if eur_sum >= debt_sum:
                dt = ''
            else:
                dt = date_list[idx] if len(date_list[idx]) > 3 else now.strftime('%d.%m.%Y')

        dt_google = ''  # if dt == '' else (
        # datetime.datetime.strptime(dt, '%d.%m.%Y') - datetime.datetime(1899, 12, 30)).days
        update_list.append([dt_google, eur_sum, debt_sum])

    wks.update('E3', update_list)
    # wks.format("E3:E40", {"numberFormat": {"type": "DATE", "pattern": "dd.mm.yyyy"}})

    # rects
    address_list = wks.col_values(3)
    address_list.pop(0)
    address_list.pop(0)
    update_list = []
    for address in address_list:
        if len(address) == 56:
            balances = await mystellar.get_balances(address)
            update_list.append([balances.get('MTLRECT', 0)])
        else:
            update_list.append(['=['])

    wks.update('H3', update_list)

    # dt1 = datetime.datetime.strptime(record["created_at"], '%Y-%m-%dT%H:%M:%SZ')
    # print(update_list)
    wks.update('B2', now.strftime('%d.%m.%Y %H:%M:%S'))

    logger.info(f'report Guarantors all done {now}')


@logger.catch
async def update_top_holders_report():
    gc = gspread.service_account('mtl-google-doc.json')

    now = datetime.datetime.now()

    wks = gc.open("MTL_TopHolders").worksheet("TopHolders")

    vote_list = await mystellar.cmd_gen_mtl_vote_list()
    vote_list = await mystellar.stellar_add_mtl_holders_info(vote_list)

    for vote in vote_list:
        vote[0] = await mystellar.resolve_account(vote[0]) if vote[1] > 400 else vote[0][:4] + '..' + vote[0][-4:]
        vote.pop(4)

    vote_list.sort(key=lambda k: k[2], reverse=True)

    wks.update('B2', vote_list)
    wks.update('G1', now.strftime('%d.%m.%Y %H:%M:%S'))

    records = wks.get_values('F2:F21')
    gd_link = 'https://docs.google.com/spreadsheets/d/1HSgK_QvK4YmVGwFXuW5CmqgszDxe99FAS2btN3FlQsI/edit#gid=171831156'
    for record in records:
        if record != '0':
            text = f'You need update votes <a href="{gd_link}">more info</a>'
            fb.execsql('insert into t_message (user_id, text, use_alarm) values (?,?,?)', (-1001239694752, text, True))
            break

    logger.info(f'report topholders all done {now}')


@logger.catch
async def update_bdm_report():
    gc = gspread.service_account('mtl-google-doc.json')

    now = datetime.datetime.now()

    wks = gc.open("MTL_TopHolders").worksheet("BDM")

    bdm_list = await mystellar.cmd_show_guards_list()

    for bdm in bdm_list:
        if len(bdm[0]) == 56:
            bdm.append(await mystellar.resolve_account(bdm[0]))
        if len(bdm[2]) == 56:
            bdm.append(await mystellar.resolve_account(bdm[2]))

    wks.update('A2', bdm_list)
    wks.update('G1', now.strftime('%d.%m.%Y %H:%M:%S'))

    logger.info(f'update bdm_report all done {now}')


@logger.catch
async def update_bim_data():
    gc = gspread.service_account('mtl-google-doc.json')

    now = datetime.datetime.now()

    wks = gc.open("MTL_BIM_register").worksheet("List")
    use_date_list = []
    mtl_amount_list = []
    data = wks.get_all_values()
    for record in data[2:]:
        mtl_amount = 0
        mmwb_date = None
        if len(record[4]) == 56 and record[10] == 'TRUE':
            use_date = fb.get_mmwb_use_date(record[4])
            if use_date:
                mmwb_date = use_date.strftime('%d.%m.%Y %H:%M:%S')
            # get balance
            balances = await mystellar.get_balances(record[4])
            mtl_amount = float(balances.get('MTL', 0) + balances.get('MTLRECT', 0))
        mtl_amount_list.append([mtl_amount])
        use_date_list.append([mmwb_date])

    wks.update('R3', mtl_amount_list)
    wks.update('U3', use_date_list, value_input_option='USER_ENTERED')
    wks.update('AG1', now.strftime('%d.%m.%Y %H:%M:%S'))
    logger.info(f'update bdm_report all done {now}')


if __name__ == "__main__":
    logger.add("update_report.log", rotation="1 MB")
    asyncio.run(update_guarantors_report())
    asyncio.run(update_bim_data())
    asyncio.run(update_top_holders_report())
