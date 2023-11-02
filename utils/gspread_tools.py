import asyncio
import json
import os
from datetime import datetime

import gspread_asyncio

# from google-auth package
from google.oauth2.service_account import Credentials
from sqlalchemy.orm import Session

from db.requests import add_to_watchlist
from utils.global_data import float2str, global_data
from itertools import zip_longest


# https://gspread-asyncio.readthedocs.io/en/latest/index.html#

# First, set up a callback function that fetches our credentials off the disk.
# gspread_asyncio needs this to re-authenticate when credentials expire.

def get_creds():
    # To obtain a service account JSON file, follow these steps:
    # https://gspread.readthedocs.io/en/latest/oauth2.html#for-bots-using-service-account
    start_path = os.path.dirname(__file__)
    key_path = os.path.join(os.path.dirname(__file__), 'mtl-google-doc.json')
    # print(start_path, key_path)

    creds = Credentials.from_service_account_file(key_path)
    scoped = creds.with_scopes([
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ])
    return scoped


# Create an AsyncioGspreadClientManager object which
# will give us access to the Spreadsheet API.

agcm = gspread_asyncio.AsyncioGspreadClientManager(get_creds)


# Here's an example of how you use the API:

async def example(agcm1):
    # Always authorize first.
    # If you have a long-running program call authorize() repeatedly.
    agc = await agcm.authorize()

    ss = await agc.open("MTL_BIM_register")
    print("Spreadsheet URL: https://docs.google.com/spreadsheets/d/{0}".format(ss.id))
    print("Open the URL in your browser to see gspread_asyncio in action!")

    # Create a new spreadsheet but also grab a reference to the default one.
    ws = await ss.worksheet("List")
    data = await ws.find('katerinafutur', in_column=3)
    print(data)
    print("All done!")


async def check_bim(user_id=None, user_name=None):
    agc = await agcm.authorize()
    ss = await agc.open("MTL_BIM_register")
    ws = await ss.worksheet("List")

    if user_name:
        data = await ws.find(str(user_name), in_column=3)
        if data:
            record = await ws.row_values(data.row)
            user_id = record[3]
    else:
        user_name = 'Your'

    if user_id:
        data = await ws.find(str(user_id), in_column=4)

    if data is None:
        return f'{user_name} account not found =('

    record = await ws.row_values(data.row)
    user_name = record[2]

    if len(record[4]) != 56:
        return f'{user_name} public key is bad =('

    if record[10] != 'TRUE':
        return f'{user_name} not resident =('

    if float(float2str(record[17])) < 1:
        return f'{user_name} MTL balance =('

    if len(record[20]) < 10:
        return f'{user_name} does not use MW  =('

    return f'{user_name} in BIM!'


# получить ID
async def gs_get_last_task_id():
    agc = await agcm.authorize()
    ss = await agc.open("MTL_TASKS_register")
    ws = await ss.worksheet("Term")

    record = await ws.col_values(1)
    return int(record[-1]), len(record)


async def gs_save_new_task(task_name, customer, manager, executor, contract_url):
    last_task_number, last_col = await gs_get_last_task_id()
    agc = await agcm.authorize()
    ss = await agc.open("MTL_TASKS_register")
    ws = await ss.worksheet("Term")
    # N	task	date_in	plan	fact	customer	manager	executor	program	contract
    await ws.update(f'A{last_col + 1}', [[last_task_number + 1, task_name, datetime.now().strftime('%d.%m'), None, None,
                                          customer, manager, executor, None, contract_url]])
    return json.dumps({'task_number': last_task_number + 1,
                       'task_name': task_name
                       })


async def gs_get_last_support_id():
    agc = await agcm.authorize()
    ss = await agc.open("MTL_support_register")
    ws = await ss.worksheet("ALL")

    record = await ws.col_values(1)
    return int(record[-1]), len(record)


async def gs_save_new_support(user_id, username, agent_username, url):
    last_number, last_col = await gs_get_last_support_id()
    agc = await agcm.authorize()
    ss = await agc.open("MTL_support_register")
    ws = await ss.worksheet("ALL")
    # n	date_in	username	ID	ticket	request	status	1	2	3	4	5	6	notes	agent
    await ws.update(f'A{last_col + 1}', [[last_number + 1, datetime.now().strftime('%d.%m'), username, user_id, url,
                                          None, None, None, None, None, None, None, None, None, agent_username]],
                    value_input_option='USER_ENTERED')
    # await wks.update('G1', now.strftime('%d.%m.%Y %H:%M:%S'))
    # await wks.update('U3', use_date_list, value_input_option='USER_ENTERED')


async def gs_close_support(url):
    agc = await agcm.authorize()
    ss = await agc.open("MTL_support_register")
    ws = await ss.worksheet("ALL")

    data = await ws.find(url, in_column=5)
    if data:
        print(data)
        record = await ws.row_values(data.row)
        user_id = record[3]


async def gs_find_user(user_id):
    result = []
    agc = await agcm.authorize()
    ss = await agc.open("MTL_ID_register")
    ws = await ss.worksheet("List")
    data = await ws.find(str(user_id), in_column=5)
    if data:
        result.append('Найден в ID')
    else:
        result.append('Не найден в ID')

    agc = await agcm.authorize()
    ss = await agc.open("MTL_BIM_register")
    ws = await ss.worksheet("List")
    data = await ws.find(str(user_id), in_column=4)
    if data:
        result.append('Найден в BIM')
    else:
        result.append('Не найден в BIM')

    return result


async def gs_update_watchlist(session_pool):
    # Open the MTL_assets worksheet
    agc = await agcm.authorize()
    ss = await agc.open("MTL_assets")

    # Check and process the ACCOUNTS worksheet
    ws_accounts = await ss.worksheet("ACCOUNTS")
    if (await ws_accounts.acell('G1')).value == 'pub_key':
        keys_accounts = [cell for cell in (await ws_accounts.col_values(7)) if len(cell) == 56]
    else:
        raise ValueError("Expected 'pub_key' in cell G1 of the ACCOUNTS worksheet")

    # Check and process the ASSETS worksheet
    ws_assets = await ss.worksheet("ASSETS")
    if (await ws_assets.acell('F1')).value == 'issuer':
        keys_assets = [cell for cell in (await ws_assets.col_values(6)) if len(cell) == 56]
    else:
        raise ValueError("Expected 'issuer' in cell F1 of the ASSETS worksheet")

    # Combine the keys and add to watchlist
    combined_keys = keys_accounts + keys_assets

    # Remove duplicates from the combined keys list
    combined_keys = list(set(combined_keys))

    with session_pool() as session:
        add_to_watchlist(session, combined_keys)


async def gs_update_namelist():
    # Open the MTL_assets worksheet
    agc = await agcm.authorize()
    ss = await agc.open("MTL_assets")

    # Select the ACCOUNTS worksheet
    ws_accounts = await ss.worksheet("ACCOUNTS")
    if (await ws_accounts.acell('G1')).value == 'pub_key' and (await ws_accounts.acell('C1')).value == 'descr':
        keys = await ws_accounts.col_values(7)
        descs = await ws_accounts.col_values(3)
        key_to_desc = {}
        for key, desc in zip_longest(keys, descs, fillvalue=''):
            if len(key) == 56:
                if desc:
                    key_to_desc[key] = desc
                else:
                    key_to_desc[key] = key[:4] + '__' + key[-4:]

    else:
        raise ValueError("Expected 'pub_key' in cell G1 and 'descr' in cell C1 of the ACCOUNTS worksheet")

    # Open the MTL_ID_register worksheet
    ss_id_register = await agc.open("MTL_ID_register")

    # Select the List worksheet
    ws_list = await ss_id_register.worksheet("List")
    if (await ws_list.acell('F2')).value == 'stellar_key' and (await ws_list.acell('D2')).value == 'tg_username':
        keys = await ws_list.col_values(6)
        usernames = await ws_list.col_values(4)
        for key, username in zip_longest(keys, usernames, fillvalue=''):
            if len(key) == 56:
                if username:
                    key_to_desc[key] = username
                else:
                    key_to_desc[key] = key[:4] + '__' + key[-4:]
        global_data.name_list = key_to_desc
    else:
        raise ValueError("Expected 'stellar_key' in cell F2 and 'tg_username' in cell D2 of the List worksheet")


async def get_assets_dict():
    agc = await agcm.authorize()

    # Откройте таблицу и получите лист
    ss = await agc.open("MTL_assets")
    wks = await ss.worksheet("ASSETS")

    # Получите данные из листа
    data = await wks.get_all_values()

    # Проверьте заголовки
    if data[0][0] != 'code' or data[0][5] != 'issuer' or data[0][13] != 'eurmtl.me':
        return {}

    # Создайте словарь
    assets_dict = {}
    for row in data[1:]:
        code = row[0]
        issuer = row[5]
        eurmtl = row[13]

        # Проверьте условия
        if eurmtl != 'TRUE' or len(issuer) < 56 or len(code) < 3:
            continue

        # Добавьте в словарь
        assets_dict[code] = issuer

    return assets_dict


async def get_accounts_dict():
    agc = await agcm.authorize()

    # Откройте таблицу и получите лист
    ss = await agc.open("MTL_assets")
    wks = await ss.worksheet("ACCOUNTS")

    # Получите данные из листа
    data = await wks.get_all_values()

    # Проверьте заголовки
    if data[0][2] != 'descr' or data[0][6] != 'pub_key' or data[0][7] != 'eurmtl.me':
        return None

    # Создайте словарь
    accounts_dict = {}
    for row in data[1:]:
        descr = row[2]
        pub_key = row[6]
        eurmtl = row[7]

        # Проверьте условия
        if eurmtl != 'TRUE' or len(pub_key) != 56 or len(descr) < 3:
            continue

        # Добавьте в словарь
        accounts_dict[descr] = pub_key

    return accounts_dict


if __name__ == "__main__":
    # a = asyncio.run(check_bim(user_name='itolstov'))
    # a = asyncio.run(gs_find_user('710700915'))
    # from db.quik_pool import quik_pool
    a = asyncio.run(gs_update_namelist())
    print(a)
