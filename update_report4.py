import datetime
import gspread
import requests
import app_logger
import fb
from stellar_sdk.sep.federation import resolve_account_id

# https://docs.gspread.org/en/latest/
from mystellar import resolve_account

if 'logger' not in globals():
    logger = app_logger.get_logger("update_report")


def update_donate_report():
    gc = gspread.service_account('mtl-google-doc.json')

    # Open a sheet from a spreadsheet in one go
    wks = gc.open("MTL_reestr").worksheet("Donates")

    # Update a range of cells using the top left corner address
    now = datetime.datetime.now()

    # donates
    donates = requests.get("https://raw.githubusercontent.com/montelibero-org/mtl/main/json/donation.json").json()
    donate_list = {}
    for k in donates:
        donate_list[k] = ''
        for v in donates[k]["recipients"]:
            donate_list[v['recipient']] = ''

    last_pay_id = \
        fb.execsql("select first 1 d.id from t_div_list d where d.memo like '%donate%' order by d.id desc")[0][0]
    last_div_id = \
        fb.execsql("select first 1 d.id from t_div_list d where d.memo like '%div%' order by d.id desc")[0][0]
    update_list = []

    for key in donate_list:
        # print(key, last_div_id)
        last_donate_sum = \
            fb.execsql(f"select sum(p.user_calc - p.user_div) from t_payments p where p.id_div_list = {last_div_id} " +
                       f"and p.user_key = '{key}'")[0][0]
        total_donate_sum = fb.execsql(f"select sum(p.user_calc - p.user_div) from t_payments p " +
                                      f"join t_div_list d on d.id = p.id_div_list " +
                                      f"where p.user_key = '{key}' and d.memo like '%div%'")[0][0]
        last_receive_sum = \
            fb.execsql(f"select sum(p.user_div) from t_payments p where p.id_div_list = {last_pay_id} " +
                       f"and p.user_key = '{key}'")[0][0]
        total_receive_sum = fb.execsql(f"select sum(p.user_div) from t_payments p " +
                                       f"join t_div_list d on d.id = p.id_div_list " +
                                       f"where p.user_key = '{key}' and d.memo like '%donate%'")[0][0]
        account_name = resolve_account(key)
        update_list.append([account_name, last_donate_sum, last_receive_sum, total_donate_sum, total_receive_sum])

    update_list.append(['', '', '', '', ''])
    update_list.append(['', '', '', '', ''])
    update_list.append(['', '', '', '', ''])

    # print(update_list)
    wks.update('A2', update_list)

    logger.info(f'all done {now}')


if __name__ == "__main__":
    update_donate_report()
