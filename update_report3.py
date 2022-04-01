import json

import gspread
import datetime
import requests
from stellar_sdk.sep.federation import resolve_stellar_address

import app_logger

# import gspread_formatting
# import json
# from settings import currencylayer_id, coinlayer_id
# https://docs.gspread.org/en/latest/
import mystellar2

if 'logger' not in globals():
    logger = app_logger.get_logger("update_report")


def my_float(s):
    result = round(float(s), 2) if len(s) > 1 else s
    return result


def update_airdrop():
    gc = gspread.service_account('mtl-google-doc.json')

    # Open a sheet from a spreadsheet in one go
    wks = gc.open("MTL_reestr").worksheet("EUR_EXTR")

    # Update a range of cells using the top left corner address
    now = datetime.datetime.now()
    # print(now.strftime('%d.%m.%Y %H:%M:%S'))

    address_list = wks.col_values(4)
    fed_address_list = wks.col_values(5)

    max_length = len(address_list) if len(address_list) > len(fed_address_list) else len(fed_address_list)

    # fill addresses

    # print(address_list)
    # print(fed_address_list)

    for idx in range(2, max_length):
        if len(address_list) > idx:  # if address more that federal
            if (len(address_list[idx]) < 10) and (len(fed_address_list[idx]) > 5) and (
                    fed_address_list[idx].count('*') > 0):
                # print(address_list[idx], fed_address_list[idx])
                address = resolve_stellar_address(fed_address_list[idx])
                # print(address.account_id)
                wks.update(f'D{idx + 1}', address.account_id)
        else:  # if federal more that address
            if (len(fed_address_list[idx]) > 5) and (fed_address_list[idx].count('*') > 0):
                # print(fed_address_list[idx], '***')
                address = resolve_stellar_address(fed_address_list[idx])
                # print(address.account_id)
                wks.update(f'D{idx + 1}', address.account_id)

    address_list = wks.col_values(4)
    address_list.pop(0)
    address_list.pop(0)
    update_list = []

    for idx, address in enumerate(address_list):
        mtl_sum = ''
        eurmtl_sum = ''
        xlm_sum = ''
        if address and (len(address) == 56):
            # print(val)
            # get balance
            balance_dic = {}
            rq = requests.get(f'https://horizon.stellar.org/accounts/{address}')
            rq_json = rq.json()
            balances = rq_json.get("balances")
            # print(json.dumps(rq, indent=4))
            if balances:
                for balance in balances:
                    if balance["asset_type"][:7] == 'credit_':
                        balance_dic[balance["asset_code"]] = balance["balance"]
                    if balance["asset_type"] == 'native':
                        balance_dic['XLM'] = balance["balance"]
                mtl_sum = my_float(balance_dic.get('MTL', ''))
                eurmtl_sum = my_float(balance_dic.get('EURMTL', ''))
                xlm_sum = my_float(balance_dic.get('XLM', ''))

        update_list.append([xlm_sum, eurmtl_sum, mtl_sum])

    print(update_list)
    wks.update('K3', update_list)

    logger.info(f'report 3 all done {now}')


if __name__ == "__main__":
    update_airdrop()
