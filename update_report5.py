import datetime
import gspread
import requests
from loguru import logger
import fb
from stellar_sdk.sep.federation import resolve_account_id

# https://docs.gspread.org/en/latest/
from mystellar import resolve_account, cmd_show_donates


@logger.catch
def update_wallet_report():
    gc = gspread.service_account('mtl-google-doc.json')

    # Open a sheet from a spreadsheet in one go
    wks = gc.open("Табличка с кошелька").worksheet("RawData")

    # Update a range of cells using the top left corner address
    now = datetime.datetime.now()

    list_wallet = fb.execsql("select m.public_key, m.free_wallet, m.default_wallet, m.last_use_day "
                             "from mymtlwalletbot m where m.user_id > 100")

    update_list = []

    for wallet in list_wallet:
        balances = {}
        # print(wallet[0])
        rq = requests.get(f'https://horizon.stellar.org/accounts/{wallet[0]}')
        if rq.status_code != 200:
            continue
        # print(rq)
        rq = rq.json()
        # print(json.dumps(rq, indent=4))
        for balance in rq["balances"]:
            if balance["asset_type"] == 'native':
                name = 'XLM'
                balances[name] = balance["balance"]
            elif balance['asset_type'][:15] == "credit_alphanum":
                name = balance["asset_code"]
                balances[name] = balance["balance"]

        update_list.append(
            [wallet[0], wallet[1], wallet[2], wallet[3].strftime('%d.%m.%Y %H:%M:%S'), float(balances.get('EURMTL', 0)),
             float(balances.get('MTL', 0))])

    # print(update_list)
    # print(update_list)
    wks.update('A4', update_list)
    wks.update('H1', now.strftime('%d.%m.%Y %H:%M:%S'))

    logger.info(f'all done {now}')


if __name__ == "__main__":
    logger.add("update_report.log", rotation="1 MB")
    update_wallet_report()
