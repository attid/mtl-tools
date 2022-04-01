import gspread
import datetime
import requests
import app_logger

# import gspread_formatting
# import json
# from settings import currencylayer_id, coinlayer_id
# https://docs.gspread.org/en/latest/
import mystellar
import mystellar2

if 'logger' not in globals():
    logger = app_logger.get_logger("update_report")


def update_guarant_report():
    gc = gspread.service_account('mtl-google-doc.json')

    # Open a sheet from a spreadsheet in one go
    wks = gc.open("EURMTL Guarantors").worksheet("Guarantors")

    # Update a range of cells using the top left corner address
    now = datetime.datetime.now()
    # print(now.strftime('%d.%m.%Y %H:%M:%S'))

    # user_entered_format = gspread_formatting.get_user_entered_format(wks,'D2')
    # print(user_entered_format)
    # gspread_formatting.format_cell_range(wks,'D4',
    #   gspread_formatting.CellFormat(numberFormat={"type":"DATE","pattern":"dd.mm.yyyy"}))
    # user_entered_format = gspread_formatting.get_user_entered_format(wks,'D4')
    # print(user_entered_format)
    # gspread_formatting.batch_updater(gc)
    address_list = wks.col_values(2)
    address_list.pop(0)
    len_address_list = len(address_list)

    all_accounts = mystellar.stellar_get_mtl_holders(mystellar.eurdebt_asset)
    for account in all_accounts:
        if account["id"] in address_list:
            pass
        else:
            address_list.append(account["id"])

    if len(address_list) > len_address_list:
        update_list = []
        for account in address_list:
            update_list.append([account])
        wks.update('B2', update_list)

    date_list = wks.col_values(4)
    date_list.pop(0)

    update_list = []

    for idx, adress in enumerate(address_list):
        eur_sum = ''
        debt_sum = ''
        if idx == len(date_list):
            date_list.append('')
        if adress and (len(adress) == 56):
            # print(val)
            # get balance
            balances = {}
            rq = requests.get(f'https://horizon.stellar.org/accounts/{adress}').json()
            # print(json.dumps(rq, indent=4))
            for balance in rq["balances"]:
                if balance["asset_type"] == 'credit_alphanum12':
                    balances[balance["asset_code"]] = balance["balance"]
            eur_sum = round(float(balances.get('EURMTL', 0)))
            debt_sum = float(balances.get('EURDEBT', 0))
            if eur_sum >= debt_sum:
                dt = ''
            else:
                dt = date_list[idx] if len(date_list[idx]) > 3 else now.strftime('%d.%m.%Y')

        dt_google = '' if dt == '' else (
                datetime.datetime.strptime(dt, '%d.%m.%Y') - datetime.datetime(1899, 12, 30)).days
        update_list.append([dt_google, eur_sum, debt_sum])

    wks.update('D2', update_list)
    wks.format("D2:D40", {"numberFormat": {"type": "DATE", "pattern": "dd.mm.yyyy"}})

    # dt1 = datetime.datetime.strptime(record["created_at"], '%Y-%m-%dT%H:%M:%SZ')
    # print(update_list)

    # vote
    wks = gc.open("MTL Report").worksheet("TopHolders")

    vote_list = mystellar2.cmd_gen_vote_list()

    wks.update('A1', vote_list)

    logger.info(f'report 2 all done {now}')


if __name__ == "__main__":
    update_guarant_report()
