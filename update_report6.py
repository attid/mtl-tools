import asyncio
import datetime
from builtins import print

import gspread
from loguru import logger
import fb

# https://docs.gspread.org/en/latest/


@logger.catch
async def update_export():
    gc = gspread.service_account('mtl-google-doc.json')

    # Open a sheet from a spreadsheet in one go
    wks = gc.open("test export 4").worksheet("2023")

    # Update a range of cells using the top left corner address
    now = datetime.datetime.now()

    update_list = []

    # print(update_list)
    last_row = wks.find('LAST', in_column=1).row
    last_id = wks.get_values(f'A{last_row - 1}')[0][0]

    list_operation = fb.execsql("select first 3000 o.id, o.dt, o.operation, o.amount1, o.code1, o.amount2, o.code2, "
                                "o.from_account, o.for_account, o.ledger from t_operations o "
                                "where o.id > ? order by o.id", (last_id,))
    for record in list_operation:
        update_list.append(
            [record[0], record[1].strftime('%d.%m.%Y %H:%M:%S'), record[2], float(record[3]), record[4],
             None if record[5] is None else float(record[5]), record[6], record[7], record[8], None, None, record[9]])

    update_list.append(['LAST', ])
    wks.update(f'A{last_row}', update_list, value_input_option='USER_ENTERED')
    # wks.update('H1', now.strftime('%d.%m.%Y %H:%M:%S'))

    logger.info(f'all done {now}')


if __name__ == "__main__":
    logger.add("update_report.log", rotation="1 MB")
    logger.info(datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S'))
    asyncio.run(update_export())
