import asyncio
import datetime
import gspread
from loguru import logger
import fb
from mystellar import get_balances


# https://docs.gspread.org/en/latest/


@logger.catch
async def update_wallet_report():
    gc = gspread.service_account('mtl-google-doc.json')

    # Open a sheet from a spreadsheet in one go
    wks = gc.open("Табличка с кошелька").worksheet("RawData")

    # Update a range of cells using the top left corner address
    now = datetime.datetime.now()

    list_wallet = fb.execsql("select m.public_key, m.free_wallet, m.default_wallet, m.last_use_day "
                             "from mymtlwalletbot m where m.user_id > 100")

    update_list = []

    for wallet in list_wallet:
        balances = await get_balances(wallet[0])
        if balances:
            update_list.append([wallet[0], wallet[1], wallet[2], wallet[3].strftime('%d.%m.%Y %H:%M:%S'),
                                float(balances.get('EURMTL', 0)),
                                float(balances.get('MTL', 0))])

    # print(update_list)
    # print(update_list)
    wks.update('A4', update_list)
    wks.update('H1', now.strftime('%d.%m.%Y %H:%M:%S'))

    logger.info(f'all done {now}')


if __name__ == "__main__":
    logger.add("update_report.log", rotation="1 MB")
    logger.info(datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S'))

    asyncio.run(update_wallet_report())
