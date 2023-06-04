import mystellar
from mystellar import *

MASTERASSETS = ['BTCDEBT', 'BTCMTL', 'EURDEBT', 'EURMTL', 'GRAFDRON',
                'MonteAqua', 'MonteCrafto', 'MTL', 'MTLBR', 'MTLBRO', 'MTLCAMP', 'MTLCITY',
                'MTLand', 'AUMTL', 'MTLMiner']


def save_account(account: str):
    rq = requests.get(f'https://horizon.stellar.org/accounts/{account}')
    with open(f"backup/{account}.json", "w") as fp:
        json.dump(rq.json(), fp, indent=2)


async def save_asset(asset: str):
    accounts = await mystellar.stellar_get_mtl_holders()
    d = datetime.now().day % 5
    with open(f"backup/{asset}.{d}.json", "w") as fp:
        json.dump(accounts, fp, indent=2)


save_account(public_issuer)
save_account(public_pawnshop)
save_account(public_fund_mabiz)
save_account(public_fund_city)
save_account(public_fund_defi)

#for asset in MASTERASSETS:
asyncio.run(save_asset('mtl'))

