import asyncio
from utils.aiogram_utils import get_web_request
from utils.config_reader import config

grist_notify = "https://montelibero.getgrist.com/api/docs/oNYTdHkEstf9X7dkh7yH11"
grist_main_chat_info = "https://montelibero.getgrist.com/api/docs/gnXfashifjtdExQoeQeij6"

async def fetch_grist_data(grist, table_name):
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {config.grist_token}'
    }
    url = f'{grist}/tables/{table_name}/records'
    status, response = await get_web_request('GET', url, headers=headers)
    if status == 200 and response and "records" in response:
        return [record['fields'] for record in response["records"]]
    else:
        raise Exception(f'Ошибка запроса: Статус {status}')

async def put_grist_data(grist, table_name, json_data):
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {config.grist_token}'
    }
    url = f'{grist}/tables/{table_name}/records'
    status, response = await get_web_request('PUT', url, headers=headers, json=json_data)
    print(response)
    if status == 200:
        return True
    else:
        raise Exception(f'Ошибка запроса: Статус {status}')

async def load_notify_info_accounts():
    try:
        records = await fetch_grist_data(grist_notify, 'Accounts')
        print(records)
    except Exception as e:
        print(f"Ошибка при загрузке данных accounts: {e}")

async def load_notify_info_assets():
    try:
        records = await fetch_grist_data(grist_notify, 'Assets')
        print(records)
    except Exception as e:
        print(f"Ошибка при загрузке данных assets: {e}")


if __name__ == '__main__':
    asyncio.run(load_notify_info_assets())
