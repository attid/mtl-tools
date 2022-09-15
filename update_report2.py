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
        wks.update('B3', update_list)

    date_list = wks.col_values(4)
    date_list.pop(0)
    #    date_list.pop(0)

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

        dt_google = ''  # if dt == '' else (
        # datetime.datetime.strptime(dt, '%d.%m.%Y') - datetime.datetime(1899, 12, 30)).days
        update_list.append([dt_google, eur_sum, debt_sum])

    wks.update('D3', update_list)
    wks.format("D3:D40", {"numberFormat": {"type": "DATE", "pattern": "dd.mm.yyyy"}})

    # dt1 = datetime.datetime.strptime(record["created_at"], '%Y-%m-%dT%H:%M:%SZ')
    # print(update_list)

    logger.info(f'report Guarantors all done {now}')


def update_top_holders_report():
    gc = gspread.service_account('mtl-google-doc.json')

    now = datetime.datetime.now()

    wks = gc.open("MTL_TopHolders").worksheet("TopHolders")

    vote_list = mystellar.cmd_gen_vote_list()
    vote_list = mystellar.stellar_add_mtl_holders_info(vote_list)

    for vote in vote_list:
        vote[0] = mystellar.resolve_account(vote[0])
        vote.pop(4)

    vote_list.sort(key=lambda k: k[2], reverse=True)

    # print(vote_list)
    wks.update('B2', vote_list)
    wks.update('G1', now.strftime('%d.%m.%Y %H:%M:%S'))

    logger.info(f'report topholders all done {now}')


def update_bdm_report():
    gc = gspread.service_account('mtl-google-doc.json')

    now = datetime.datetime.now()

    wks = gc.open("MTL_TopHolders").worksheet("BDM")

    bdm_list = mystellar.cmd_show_guards_list()

    for bdm in bdm_list:
        if len(bdm[0]) == 56:
            bdm.append(mystellar.resolve_account(bdm[0]))
        if len(bdm[2]) == 56:
            bdm.append(mystellar.resolve_account(bdm[2]))

    wks.update('A2', bdm_list)
    wks.update('G1', now.strftime('%d.%m.%Y %H:%M:%S'))

    logger.info(f'update bdm_report all done {now}')


if __name__ == "__main__":
    update_guarant_report()
    update_top_holders_report()
    update_bdm_report()
