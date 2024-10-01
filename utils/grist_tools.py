import asyncio
from utils.aiogram_utils import get_web_request
from utils.config_reader import config


async def load_notify_info():
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {config.grist_token}'
    }
    url = 'https://montelibero.getgrist.com/api/docs/nHQDDNd3HQywQvxwhcbg5t/tables/Notify_info/records'
    status, response = await get_web_request('GET', url, headers=headers)
    if status == 200 and response and "records" in response:
        # {'usd_value': 253279.1102783137}
        # return float(response.get('usd_value'))
        print(response["records"])
    else:
        raise Exception(f'Ошибка запроса: Статус {status}')



if __name__ == '__main__':
    asyncio.run(load_notify_info())