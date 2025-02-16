import asyncio
import json
import math
import os
from datetime import datetime
from itertools import zip_longest

import gspread_asyncio
# from google-auth package
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

from db.requests import add_to_watchlist
from other.config_reader import start_path
from other.global_data import float2str, global_data


# https://gspread-asyncio.readthedocs.io/en/latest/index.html#

# First, set up a callback function that fetches our credentials off the disk.
# gspread_asyncio needs this to re-authenticate when credentials expire.

def get_creds():
    # To obtain a service account JSON file, follow these steps:
    # https://gspread.readthedocs.io/en/latest/oauth2.html#for-bots-using-service-account

    key_path = os.path.join(start_path, 'data', 'mtl-google-doc.json')
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


async def gs_check_bim(user_id=None, user_name=None):
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
        # print(data)
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
    ss = await agc.open("MTL_Airdrop_register")
    ws = await ss.worksheet("EUR_GNRL")
    data = await ws.find(str(user_id), in_column=7)
    if data:
        result.append(f'Найден в Airdrop строка {data.row}')
    else:
        result.append('ID пользователя не найдено в Airdrop')

    return result


# async def gs_update_watchlist(session_pool):
#     # Open the MTL_assets worksheet
#     agc = await agcm.authorize()
#     ss = await agc.open("MTL_assets")
#
#     # Check and process the ACCOUNTS worksheet
#     ws_accounts = await ss.worksheet("ACCOUNTS")
#     if (await ws_accounts.acell('G1')).value == 'pub_key':
#         keys_accounts = [cell for cell in (await ws_accounts.col_values(7)) if len(cell) == 56]
#     else:
#         raise ValueError("Expected 'pub_key' in cell G1 of the ACCOUNTS worksheet")
#
#     # Check and process the ASSETS worksheet
#     ws_assets = await ss.worksheet("ASSETS")
#     if (await ws_assets.acell('F1')).value == 'issuer':
#         keys_assets = [cell for cell in (await ws_assets.col_values(6)) if len(cell) == 56]
#     else:
#         raise ValueError("Expected 'issuer' in cell F1 of the ASSETS worksheet")
#
#     # Combine the keys and add to watchlist
#     combined_keys = keys_accounts + keys_assets
#
#     # Remove duplicates from the combined keys list
#     combined_keys = list(set(combined_keys))
#
#     with session_pool() as session:
#         add_to_watchlist(session, combined_keys)


# async def gs_update_namelist():
#     # Open the MTL_assets worksheet
#     agc = await agcm.authorize()
#     ss = await agc.open("MTL_assets")
#
#     # Select the ACCOUNTS worksheet
#     ws_accounts = await ss.worksheet("ACCOUNTS")
#     if (await ws_accounts.acell('G1')).value == 'pub_key' and (await ws_accounts.acell('C1')).value == 'descr':
#         keys = await ws_accounts.col_values(7)
#         descs = await ws_accounts.col_values(3)
#         key_to_desc = {}
#         for key, desc in zip_longest(keys, descs, fillvalue=''):
#             if len(key) == 56:
#                 if desc:
#                     key_to_desc[key] = desc
#                 else:
#                     key_to_desc[key] = key[:4] + '__' + key[-4:]
#
#     else:
#         raise ValueError("Expected 'pub_key' in cell G1 and 'descr' in cell C1 of the ACCOUNTS worksheet")
#
#     # Open the MTL_ID_register worksheet
#     ss_id_register = await agc.open("MTL_ID_register")
#
#     # Select the List worksheet
#     ws_list = await ss_id_register.worksheet("List")
#     if (await ws_list.acell('F2')).value == 'stellar_key' and (await ws_list.acell('D2')).value == 'tg_username':
#         keys = await ws_list.col_values(6)
#         usernames = await ws_list.col_values(4)
#         for key, username in zip_longest(keys, usernames, fillvalue=''):
#             if len(key) == 56:
#                 if username:
#                     key_to_desc[key] = username
#                 else:
#                     key_to_desc[key] = key[:4] + '__' + key[-4:]
#         # global_data.name_list = key_to_desc
#     else:
#         raise ValueError("Expected 'stellar_key' in cell F2 and 'tg_username' in cell D2 of the List worksheet")
#     # print(key_to_desc)
#     ss_mtlap = await agc.open_by_key("1_HaNfIsPXBs65vwfytAGXUXwH57gb50WtVkh0qBySCo")
#     ws_mtlap = await ss_mtlap.worksheet("MTLAP")
#
#     # Проверяем заголовки в первой строке
#     headers = await ws_mtlap.row_values(1)
#     if headers[0].lower() == 'telegram' and headers[2].lower() == 'stellar':
#         # Считываем данные из столбцов Telegram и Stellar
#         tgs = await ws_mtlap.col_values(1)
#         stellar_keys = await ws_mtlap.col_values(3)
#
#         # Добавляем данные в словарь key_to_desc
#         for tg, stellar_key in zip_longest(tgs, stellar_keys, fillvalue=''):
#             if len(stellar_key) == 56:
#                 if tg:
#                     key_to_desc[stellar_key] = tg[1:]
#                 else:
#                     key_to_desc[stellar_key] = stellar_key[:4] + '__' + stellar_key[-4:]
#     else:
#         raise ValueError("Expected 'Telegram' in column 1 and 'Stellar' in column 3 of the MTLAP worksheet")
#     # print(key_to_desc)
#     global_data.name_list = key_to_desc


# async def gs_get_assets_dict():
#     agc = await agcm.authorize()
#
#     # Откройте таблицу и получите лист
#     ss = await agc.open("MTL_assets")
#     wks = await ss.worksheet("ASSETS")
#
#     # Получите данные из листа
#     data = await wks.get_all_values()
#
#     # Проверьте заголовки
#     if data[0][0] != 'code' or data[0][5] != 'issuer' or data[0][13] != 'eurmtl.me':
#         return {}
#
#     # Создайте словарь
#     assets_dict = {}
#     for row in data[1:]:
#         code = row[0]
#         issuer = row[5]
#         eurmtl = row[13]
#
#         # Проверьте условия
#         if eurmtl != 'TRUE' or len(issuer) < 56 or len(code) < 3:
#             continue
#
#         # Добавьте в словарь
#         assets_dict[code] = issuer
#
#     return assets_dict


# async def gs_get_accounts_dict():
#     agc = await agcm.authorize()
#
#     # Откройте таблицу и получите лист
#     ss = await agc.open("MTL_assets")
#     wks = await ss.worksheet("ACCOUNTS")
#
#     # Получите данные из листа
#     data = await wks.get_all_values()
#
#     # Проверьте заголовки
#     if data[0][2] != 'descr' or data[0][6] != 'pub_key' or data[0][7] != 'eurmtl.me':
#         return None
#
#     # Создайте словарь
#     accounts_dict = {}
#     for row in data[1:]:
#         descr = row[2]
#         pub_key = row[6]
#         eurmtl = row[7]
#
#         # Проверьте условия
#         if eurmtl != 'TRUE' or len(pub_key) != 56 or len(descr) < 3:
#             continue
#
#         # Добавьте в словарь
#         accounts_dict[descr] = pub_key
#
#     return accounts_dict


# async def gs_get_accounts_multi_list() -> list:
#     agc = await agcm.authorize()
#
#     ss = await agc.open("MTL_assets")
#     wks = await ss.worksheet("ACCOUNTS")
#
#     data = await wks.get_all_values()
#
#     if data[0][2] != 'descr' or data[0][6] != 'pub_key' or data[0][5] != 'signers':
#         return None
#
#     accounts_list = []
#     for row in data[1:]:
#         descr = row[2]
#         pub_key = row[6]
#         flag = row[5]
#
#         # Проверьте условия
#         if flag.lower().find('multisp') == -1 or len(pub_key) != 56 or len(descr) < 3:
#             continue
#
#         # Добавьте в словарь
#         accounts_list.append(pub_key)
#
#     return accounts_list


async def gs_get_chicago_premium():
    # Авторизация для доступа к Google Sheets
    agc = await agcm.authorize()

    # Откройте таблицу и получите лист
    ss = await agc.open("Chicago_cashback_table")
    wks = await ss.worksheet("data")

    # Получите данные из листа
    data = await wks.get_all_values()

    # Фильтруйте список, оставляя только строки с длиной 56 символов в первом столбце
    premium_list = [row[0] for row in data if len(row[0]) == 56]

    return premium_list


async def gs_set_column_width(spreadsheet, worksheet_id, column_index, width):
    # Формируем запрос для изменения ширины столбца
    request = {
        "requests": [
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": worksheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": column_index - 1,
                        "endIndex": column_index
                    },
                    "properties": {
                        "pixelSize": width
                    },
                    "fields": "pixelSize"
                }
            }
        ]
    }

    # Отправляем запрос

    await spreadsheet.batch_update(request)


async def gs_copy_a_table(new_name):
    agc = await agcm.authorize()

    # Получаем доступ к таблице, которую надо скопировать
    ss = await agc.open("default_a_vote")

    # Копируем таблицу
    new_ss = await agc.create(new_name)
    await agc.insert_permission(new_ss.id, None, perm_type="anyone", role="reader")

    # Получаем список листов в существующем документе
    worksheets = await ss.worksheets()

    # Копируем каждый лист
    for sheet in worksheets:
        new_sheet = await new_ss.add_worksheet(title=sheet.title, rows=sheet.row_count, cols=sheet.col_count)

    # Данные после чтоб ссылки работали
    for sheet in worksheets:
        new_sheet = await new_ss.worksheet(title=sheet.title)
        # Получаем данные из исходного листа
        # cells = await sheet.get_all_values()
        cells = (await sheet.batch_get(['A1:D20'], value_render_option='FORMULA'))[0]

        # Заполняем лист данными
        await new_sheet.update('A1', cells, value_input_option='USER_ENTERED')

    await new_ss.del_worksheet((await new_ss.worksheets())[0])

    # Возвращаем ссылку на новую таблицу
    new_ss_url = new_ss.url
    return new_ss_url, new_ss.id


async def gs_update_a_table_first(table_uuid, question, options, votes):
    agc = await agcm.authorize()

    ss = await agc.open_by_key(table_uuid)
    wks = await ss.worksheet("Result")
    await gs_set_column_width(ss, wks.id, 1, 200)
    await gs_set_column_width(ss, wks.id, 2, 400)

    update_data = [[question],
                   [datetime.now().strftime('%d.%m.%Y %H:%M:%S')],
                   [],
                   [len(votes)],
                   [math.ceil(len(votes) / 2)]
                   ]
    await wks.update('B1', update_data)
    update_data = []
    for option in options:
        update_data.append([option])
    await wks.update('A7', update_data)
    update_data = [['']] * 10
    await wks.update(f'B{7 + len(options)}', update_data)
    # 2
    wks = await ss.worksheet("Log")
    await wks.delete_row(2)
    await wks.update('C1', [options])
    # 3
    # {'GA5Q2PZWIHSCOHNIGJN4BX5P42B4EMGTYAS3XCMAHEHCFFKCQQ3ZX34A': {'delegate': 'GCPOWDQQDVSAQGJXZW3EWPPJ5JCF4KTTHBYNB4U54AKQVDLZXLLYMXY7', 'vote': 1, 'was_delegate': 'GCPOWDQQDVSAQGJXZW3EWPPJ5JCF4KTTHBYNB4U54AKQVDLZXLLYMXY7'}
    update_data = []
    for vote in votes:
        update_data.append([vote, votes[vote].get('was_delegate')])

    wks = await ss.worksheet("Members")
    await wks.update('A2', update_data)


# async def gs_find_user_a(username):
#     agc = await agcm.authorize()
#     ss = await agc.open_by_key("1_HaNfIsPXBs65vwfytAGXUXwH57gb50WtVkh0qBySCo")
#     ws = await ss.worksheet("MTLAP")
#     data = await ws.find(str(username), in_column=1, case_sensitive=False)
#     if data:
#         result = await ws.row_values(data.row)
#         return result[2]


async def gs_update_a_table_vote(table_uuid, address, options, delegated=None, wks=None):
    if wks is None:
        agc = await agcm.authorize()
        ss = await agc.open_by_key(table_uuid)
        wks = await ss.worksheet("Log")

    # Проверка наличия адреса на странице Members
    members_addresses = await (await ss.worksheet("Members")).col_values(1)
    if address not in members_addresses:
        return

    # Удаляем голос если был
    data = await wks.find(str(address), in_column=1, case_sensitive=False)
    if data and delegated:
        return

    # if data:
    while data:
        await wks.delete_row(data.row)
        data = await wks.find(f'{address[:4]}..{address[-4:]}', case_sensitive=False)

    # Если опции не пусты, то добавляем запись
    if options:
        record = await wks.col_values(1)
        update_data = [address, datetime.now().strftime('%d.%m.%Y %H:%M:%S')]

        # Создаем список для голосов
        votes_list = [None] * (max(options) + 1)  # Предполагаем, что максимальное значение в options это конец списка
        x = delegated if delegated else 'X'
        for option in options:
            votes_list[option] = x
        update_data.extend(votes_list)  # Начинаем добавление данных с третьей колонки, пропускаем первые два элемента

        # Записываем данные в таблицу, начиная с новой строки
        await wks.update(f'A{len(record) + 1}', [update_data])

        if delegated:
            return
        # теперь с делегаций
        delegate_data = await (await ss.worksheet("Members")).get_all_values()
        for record in delegate_data[1:]:
            if record[1] == address:
                await gs_update_a_table_vote(table_uuid, record[0], options,
                                             delegated=f'{address[:4]}..{address[-4:]}', wks=wks)

        #
        wks = await ss.worksheet("Result")
        data = await wks.get_all_values()

        return data[3:]


async def gs_check_vote_table(table_uuid):
    # Авторизация и получение данных из первой таблицы
    agc = await agcm.authorize()
    ss = await agc.open_by_key("1_HaNfIsPXBs65vwfytAGXUXwH57gb50WtVkh0qBySCo")  # MTLA Members
    ws = await ss.worksheet("MTLAP")
    data = await ws.get_all_values()

    # Создание словаря для хранения адресов и соответствующих @username
    address_dict = {row[2]: row[0] for row in data if len(row) >= 2}

    # Открытие второй таблицы и получение списка участников
    ss = await agc.open_by_key(table_uuid)
    wks = await ss.worksheet("Members")
    who_in = await wks.col_values(1)
    delegate_to = await wks.col_values(2)

    # Создание словарей для хранения адресов
    matched_addresses = {}
    matched_addresses_delegated = {}

    for i, address in enumerate(who_in[1:], start=1):
        if address in address_dict:
            if i < len(delegate_to) and delegate_to[i].strip():
                matched_addresses_delegated[address] = address_dict[address]
            else:
                matched_addresses[address] = address_dict[address]
        else:
            if i < len(delegate_to) and delegate_to[i].strip():
                matched_addresses_delegated[address] = f"{address[:4]}..{address[-4:]}"
            else:
                matched_addresses[address] = f"{address[:4]}..{address[-4:]}"

    # проголосовали
    wks = await ss.worksheet("Log")
    who_vote = await wks.col_values(1)

    for address in who_vote[1:]:
        if address in matched_addresses:
            matched_addresses.pop(address)
        elif address in matched_addresses_delegated:
            matched_addresses_delegated.pop(address)

    return list(matched_addresses.values()), list(matched_addresses_delegated.values())


def gs_copy_sheets_with_style(copy_from, copy_to, sheet_name_from, sheet_name_to=None):
    if sheet_name_to is None:
        sheet_name_to = sheet_name_from
    # sheet_data_result = await asyncio.to_thread(get_sheet_data_and_styles_sync, service, copy_from, sheet_name)
    # Настройка аутентификации для Google Sheets API
    key_path = os.path.join(start_path, 'data', 'mtl-google-doc.json')

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    credentials = ServiceAccountCredentials.from_json_keyfile_name(key_path, scopes)
    service = build('sheets', 'v4', credentials=credentials)

    # Запрос метаданных всего документа
    source_sheet_data = service.spreadsheets().get(spreadsheetId=copy_from, includeGridData=True).execute()

    # Находим нужный лист по имени
    sheet_data = None
    for sheet in source_sheet_data['sheets']:
        if sheet['properties']['title'] == sheet_name_from:
            sheet_data = sheet
            break

    if not sheet_data:
        raise Exception(f"Sheet {sheet_name_from} not found in spreadsheet.")

    # Получение данных и стилей с исходного листа
    row_data = sheet_data.get('data', [])[0].get('rowData', [])
    merges = sheet_data.get('merges', [])

    # Получение целевого документа и листа
    # Запрос метаданных всего документа
    target_sheet_data = service.spreadsheets().get(spreadsheetId=copy_to).execute()

    # Находим нужный лист в целевом документе по имени и получаем его ID
    target_sheet_id = None
    for sheet in target_sheet_data['sheets']:
        if sheet['properties']['title'] == sheet_name_to:
            target_sheet_id = sheet['properties']['sheetId']
            break

    if target_sheet_id is None:
        raise Exception(f"Target sheet {sheet_name_to} not found in spreadsheet.")

    # Вставляем вызов функции unmerge_all_cells здесь
    unmerge_all_cells(service, copy_to, target_sheet_id)

    # Применение данных и стилей к целевому листу
    requests = []
    for row_index, row in enumerate(row_data):
        for col_index, cell in enumerate(row.get('values', [])):
            cell_data = cell.get('effectiveValue', {})
            cell_style = cell.get('effectiveFormat', {})

            # Формирование значения для ячейки
            user_entered_value = {}
            if 'stringValue' in cell_data:
                user_entered_value = {"stringValue": cell_data['stringValue']}
            elif 'numberValue' in cell_data:
                user_entered_value = {"numberValue": cell_data['numberValue']}
            elif 'boolValue' in cell_data:
                user_entered_value = {"boolValue": cell_data['boolValue']}

            # Формирование запроса для обновления ячейки
            cell_update = {
                "userEnteredFormat": cell_style
            }
            if user_entered_value:
                cell_update["userEnteredValue"] = user_entered_value

            requests.append({
                "updateCells": {
                    "rows": [{"values": [cell_update]}],
                    "fields": "userEnteredValue,userEnteredFormat",
                    "start": {
                        "sheetId": target_sheet_id,
                        "rowIndex": row_index,
                        "columnIndex": col_index
                    }
                }
            })

    for merge in merges:
        start_row = merge.get('startRowIndex', 0)
        end_row = merge.get('endRowIndex', 0)
        start_col = merge.get('startColumnIndex', 0)
        end_col = merge.get('endColumnIndex', 0)

        requests.append({
            "mergeCells": {
                "range": {
                    "sheetId": target_sheet_id,
                    "startRowIndex": start_row,
                    "endRowIndex": end_row,
                    "startColumnIndex": start_col,
                    "endColumnIndex": end_col
                },
                "mergeType": "MERGE_ALL"  # или "MERGE_COLUMNS", "MERGE_ROWS" в зависимости от ваших потребностей
            }
        })

    # Отправка запросов к API
    if requests:
        service.spreadsheets().batchUpdate(spreadsheetId=copy_to, body={"requests": requests}).execute()


def unmerge_all_cells(service, spreadsheet_id, sheet_id):
    # Получаем информацию о листе, чтобы найти все объединенные ячейки
    sheet_info = service.spreadsheets().get(spreadsheetId=spreadsheet_id, includeGridData=False).execute()
    requests = []

    # Поиск объединенных ячеек в нужном листе
    for sheet in sheet_info['sheets']:
        if sheet['properties']['sheetId'] == sheet_id:
            merges = sheet.get('merges', [])
            for merge in merges:
                # Для каждой найденной объединенной группы создаем запрос на разъединение
                requests.append({
                    "unmergeCells": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": merge['startRowIndex'],
                            "endRowIndex": merge['endRowIndex'],
                            "startColumnIndex": merge['startColumnIndex'],
                            "endColumnIndex": merge['endColumnIndex']
                        }
                    }
                })
            break

    # Если есть запросы на разъединение, отправляем их
    if requests:
        service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests}).execute()


async def get_all_data_from_mmwb_config():
    agc = await agcm.authorize()
    # Открытие таблицы по ключу
    ss = await agc.open_by_key("1ImFxY_WaDzBDBXkpokUj186CdxBhZH7-_COxXnMkoVc")
    # Выбор вкладки "CONFIG"
    ws = await ss.worksheet("CONFIG")
    # Получение всех данных с вкладки
    data = await ws.get_all_values()
    return data


async def get_one_data_mm_from_report():
    agc = await agcm.authorize()
    ss = await agc.open_by_key("1ZaopK2DRbP5756RK2xiLVJxEEHhsfev5ULNW5Yz_EZc")
    ws = await ss.worksheet("autodata_config")

    data = await ws.get_values('D2:D15')
    mtl_market = data[11][0]
    mtlfarm_usd = data[8][0]
    usd_eur = data[1][0]
    xlm_usd = data[3][0]
    mtl_market_xlm = (float(float2str(mtl_market)) / float(float2str(usd_eur)) / float(float2str(xlm_usd)))
    mtlfarm_usd = float(float2str(mtlfarm_usd))
    return mtl_market_xlm, mtlfarm_usd


async def gs_get_all_mtlap():
    agc = await agcm.authorize()
    ss = await agc.open_by_key("1_HaNfIsPXBs65vwfytAGXUXwH57gb50WtVkh0qBySCo")
    ws = await ss.worksheet("MTLAP")
    data = await ws.get_all_values()
    return data


async def gs_get_update_mtlap_skynet_row(data):
    agc = await agcm.authorize()
    ss = await agc.open_by_key("1_HaNfIsPXBs65vwfytAGXUXwH57gb50WtVkh0qBySCo")
    ws = await ss.worksheet("MTLAP")

    # Обновляем значения в 14-м столбце (SkyNet) за один запрос
    cell_range = "O2"
    values = [[value] for value in data]
    await ws.update(cell_range, values)


async def gs_permission(table_id, email='attid0@gmail.com', remove_permissions=False):
    agc = await agcm.authorize()
    ss = await agc.open_by_key(table_id)

    # To remove permissions
    if remove_permissions:
        permissions = await ss.list_permissions()
        for permission in permissions:
            if permission.get('emailAddress') == email:
                await ss.remove_permissions(permission['id'])
    else:
        await agc.insert_permission(
            ss.id,
            email,
            perm_type='user',
            role='writer'
        )


if __name__ == "__main__":
    pass

    _ = asyncio.run(gs_permission(True))
    print(_)

    # a = asyncio.run(gs_check_bim(user_name='itolstov'))
    # a = asyncio.run(gs_find_user('710700915'))
    # from db.quik_pool import quik_pool

    # a = asyncio.run(gs_test())
    # ('https://docs.google.com/spreadsheets/d/1FxCMie193zD3EH8zrMgDh4jS-zsXmLhPFRKNISkASa4', '1FxCMie193zD3EH8zrMgDh4jS-zsXmLhPFRKNISkASa4')
    # a = asyncio.run(gs_update_a_table_first('1eosWKqeq3sMB9FCIShn0YcuzzDOR40fAgeTGCqMfhO8', 'question',
    #                                        ['dasd adsd asd', 'asdasdsadsad asdsad asd', 'sdasdasd dsf'], []))
    # a = asyncio.run(gs_update_namelist())
    # get_creds()
    # print(a)
    # gs_copy_sheets_with_style("1ZaopK2DRbP5756RK2xiLVJxEEHhsfev5ULNW5Yz_EZc",
    #                           "1v2s2kQfciWJbzENOy4lHNx-UYX61Uctdqf1rE-2NFWc", "report", None)
    # gs_copy_sheets_with_style("1ZaopK2DRbP5756RK2xiLVJxEEHhsfev5ULNW5Yz_EZc",
    #                           "1iQgWZ7vjkcN7tMJDUvTSXvLvzIxWD6ZnkmF8kx_Hu1c", "usdm_report", None)
    # gs_copy_sheets_with_style("1ZaopK2DRbP5756RK2xiLVJxEEHhsfev5ULNW5Yz_EZc",
    #                           "1hn_GnLoClx20WcAsh0Kax3WP4SC5PGnjs4QZeDnHWec", "report", "B_TBL")
