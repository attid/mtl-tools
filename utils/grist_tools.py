import asyncio
from loguru import logger
from utils.aiogram_utils import get_web_request
from utils.config_reader import config

grist_notify = "https://montelibero.getgrist.com/api/docs/oNYTdHkEstf9X7dkh7yH11"
grist_main_chat_info = "https://montelibero.getgrist.com/api/docs/gnXfashifjtdExQoeQeij6"
grist_sp = "https://montelibero.getgrist.com/api/docs/3sFtdPU7Dcfw2XwTioLcJD"


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
    if status == 200:
        return True
    else:
        raise Exception(f'Ошибка запроса: Статус {status}')


async def load_notify_info_accounts():
    try:
        records = await fetch_grist_data(grist_notify, 'Accounts')
        return records
    except Exception as e:
        logger.warning(f"Ошибка при загрузке данных accounts: {e}")


async def load_notify_info_assets():
    try:
        records = await fetch_grist_data(grist_notify, 'Assets')
        return records
    except Exception as e:
        logger.warning(f"Ошибка при загрузке данных assets: {e}")


async def load_notify_sp_users():
    try:
        records = await fetch_grist_data(grist_sp, 'SP_USERS')
        return records
    except Exception as e:
        logger.warning(f"Ошибка при загрузке данных assets: {e}")


async def load_notify_sp_chats():
    try:
        records = await fetch_grist_data(grist_sp, 'SP_CHATS')
        return records
    except Exception as e:
        logger.warning(f"Ошибка при загрузке данных assets: {e}")


if __name__ == '__main__':
    _ = asyncio.run(load_notify_sp_users())
    print(_)
