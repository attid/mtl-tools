import asyncio
import json
import os
from datetime import datetime

import gspread_asyncio

# from google-auth package
from google.oauth2.service_account import Credentials

from utils.global_data import float2str


# https://gspread-asyncio.readthedocs.io/en/latest/index.html#

# First, set up a callback function that fetches our credentials off the disk.
# gspread_asyncio needs this to re-authenticate when credentials expire.

def get_creds():
    # To obtain a service account JSON file, follow these steps:
    # https://gspread.readthedocs.io/en/latest/oauth2.html#for-bots-using-service-account
    start_path = os.path.dirname(__file__)
    key_path = os.path.join(os.path.dirname(__file__), 'mtl-google-doc.json')
    #print(start_path, key_path)

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
async def cmd_get_last_task_id():
    agc = await agcm.authorize()
    ss = await agc.open("MTL_TASKS_register")
    ws = await ss.worksheet("Term")

    record = await ws.col_values(1)
    return int(record[-1]), len(record)


async def cmd_save_new_task(task_name, customer, manager, executor, contract_url):
    last_task_number, last_col = await cmd_get_last_task_id()
    agc = await agcm.authorize()
    ss = await agc.open("MTL_TASKS_register")
    ws = await ss.worksheet("Term")
    # N	task	date_in	plan	fact	customer	manager	executor	program	contract
    await ws.update(f'A{last_col + 1}', [[last_task_number + 1, task_name, datetime.now().strftime('%d.%m'), None, None,
                                          customer, manager, executor, None, contract_url]])
    return json.dumps({'task_number': last_task_number + 1,
                       'task_name': task_name
                       })


if __name__ == "__main__":
    # a = asyncio.run(check_bim(user_name='itolstov'))
    a = asyncio.run(cmd_save_new_task())
    print(a)
