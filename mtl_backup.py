import mystellar
from mystellar import *

MASTERASSETS = ['BTCDEBT', 'BTCMTL', 'EURDEBT', 'EURMTL', 'GRAFDRON',
                'MonteAqua', 'MonteCrafto', 'MTL', 'MTLBR', 'MTLBRO', 'MTLCAMP', 'MTLCITY',
                'MTLand', 'AUMTL', 'MTLMiner']


def save_account(account: str):
    rq = requests.get(f'https://horizon.stellar.org/accounts/{account}')
    with open(f"backup/{account}.json", "w") as fp:
        json.dump(rq.json(), fp, indent=2)


def save_asset(asset: str):
    accounts = mystellar.stellar_get_mtl_holders()
    with open(f"backup/{asset}.json", "w") as fp:
        json.dump(accounts, fp, indent=2)


save_account(public_issuer)
save_account(public_pawnshop)
save_account(public_distributor)
save_account(public_fond)

for asset in MASTERASSETS:
    save_asset(asset)
