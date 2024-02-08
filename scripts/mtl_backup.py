from config_reader import start_path
from utils.stellar_utils import *

MASTERASSETS = ['BTCDEBT', 'BTCMTL', 'EURDEBT', 'EURMTL', 'GRAFDRON',
                'MonteAqua', 'MonteCrafto', 'MTL', 'MTLBR', 'MTLBRO', 'MTLCAMP', 'MTLCITY',
                'MTLand', 'AUMTL', 'MTLMiner']


def save_account(account: str):
    rq = requests.get(f'https://horizon.stellar.org/accounts/{account}')
    with open(f"backup/{account}.json", "w") as fp:
        json.dump(rq.json(), fp, indent=2)


async def save_asset(asset: str):
    accounts = await stellar_get_mtl_holders()
    d = datetime.now().day % 5
    with open(f"backup/{asset}.{d}.json", "w") as fp:
        json.dump(accounts, fp, indent=2)


async def save_assets(assets: list):
    accounts = []
    for asset in assets:
        asset_accounts = await stellar_get_mtl_holders(asset)
        # Добавляем аккаунты, избегая дублирования
        for account in asset_accounts:
            if account not in accounts:
                accounts.append(account)

    # Сохраняем данные в файл с уникальным идентификатором
    d = datetime.now().day % 5
    with open(f"{start_path}/backup/all.{d}.json", "w") as fp:
        json.dump(accounts, fp, indent=2)
    with open(f"{start_path}/backup/all.last.json", "w") as fp:
        json.dump(accounts, fp, indent=2)


asyncio.run(save_assets([MTLAssets.mtl_asset, MTLAssets.mtlap_asset, MTLAssets.mtlrect_asset, MTLAssets.eurmtl_asset]))
