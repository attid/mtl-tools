import asyncio
import gspread
import datetime

from stellar_sdk import AiohttpClient
from stellar_sdk.sep.federation import resolve_stellar_address_async
from mystellar import get_balances
from loguru import logger

# import gspread_formatting
# import json
# from settings import currencylayer_id, coinlayer_id
# https://docs.gspread.org/en/latest/


@logger.catch
def my_float(s):
    result = round(float(s), 2) if len(str(s)) > 1 else s
    return result


@logger.catch
async def update_airdrop():
    gc = gspread.service_account('mtl-google-doc.json')
    client = AiohttpClient()

    # Open a sheet from a spreadsheet in one go
    wks = gc.open("MTL_reestr").worksheet("EUR_GNRL")

    # Update a range of cells using the top left corner address
    now = datetime.datetime.now()
    # print(now.strftime('%d.%m.%Y %H:%M:%S'))

    address_list = wks.col_values(4)
    fed_address_list = wks.col_values(5)
    start_pos = int(wks.cell(1,1).value)

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
                    wks.update(f'D{idx + 1}', address.account_id)
                except:
                    print('Resolving error', address_list[idx], fed_address_list[idx])
        else:  # if federal more that address
            if (len(fed_address_list[idx]) > 5) and (fed_address_list[idx].count('*') > 0):
                # print(fed_address_list[idx], '***')
                address = await resolve_stellar_address_async(fed_address_list[idx], client=client)
                # print(address.account_id)
                wks.update(f'D{idx + 1}', address.account_id)

    address_list = wks.col_values(4)
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
            balance_dic:dict = await get_balances(address)
            mtl_sum = my_float(balance_dic.get('MTL', ''))
            eurmtl_sum = my_float(balance_dic.get('EURMTL', ''))
            xlm_sum = my_float(balance_dic.get('XLM', ''))
            sats_sum = my_float(balance_dic.get('SATSMTL', ''))

        update_list.append([xlm_sum, eurmtl_sum, mtl_sum, sats_sum])

    #print(update_list)
    wks.update(f'K{start_pos+3}', update_list)
    wks.update('O2', now.strftime('%d.%m.%Y %H:%M:%S'))
    await client.close()

    logger.info(f'report 3 all done {now}')


if __name__ == "__main__":
    logger.add("update_report.log", rotation="1 MB")
    logger.info(datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S'))

    asyncio.run(update_airdrop())


