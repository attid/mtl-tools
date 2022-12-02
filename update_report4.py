import datetime
from builtins import print

import gspread
import requests
import app_logger
import fb
from stellar_sdk.sep.federation import resolve_account_id

# https://docs.gspread.org/en/latest/
from mystellar import resolve_account, cmd_show_donates, key_name

if 'logger' not in globals():
    logger = app_logger.get_logger("update_report")


def update_donate_report():
    gc = gspread.service_account('mtl-google-doc.json')

    # Open a sheet from a spreadsheet in one go
    wks = gc.open("MTL_TopHolders").worksheet("Donates")

    # Update a range of cells using the top left corner address
    now = datetime.datetime.now()

    # donates

    updates = fb.execsql("""select user_key, iif(total_pay > 0, sl.total_pay, 0) total_pay, 
    coalesce(total_receive, 0) total_receive, 
    (select coalesce(sum(p.user_calc - p.user_div), 0)
          from t_payments p
         where p.id_div_list = sl.max_div_num
           and p.user_key = sl.user_key) last_pay,
       (select coalesce(sum(p.user_div), 0)
          from t_payments p
         where p.id_div_list = sl.max_donate_num
           and p.user_key = sl.user_key) last_receive
  from (select pp.user_key,
               (select sum(p.user_calc - p.user_div)
                  from t_payments p
                  join t_div_list d on d.id = p.id_div_list
                 where p.user_key = pp.user_key
                   and d.memo like '%div%'
                   and p.was_packed = 1) total_pay,
               (select sum(p.user_div)
                  from t_payments p
                  join t_div_list d on d.id = p.id_div_list
                 where p.user_key = pp.user_key
                   and d.memo like '%donate%'
                   and p.was_packed = 1) total_receive,
               (select first 1 d.id
                  from t_div_list d
                 where d.memo like '%div%'
                 order by d.id desc) max_div_num,
               (select first 1 d.id
                  from t_div_list d
                 where d.memo like '%donate%'
                 order by d.id desc) max_donate_num
          from t_payments pp
          join t_div_list dd on dd.id = pp.id_div_list and
                dd.pay_type = 0
         group by pp.user_key) sl
 where (sl.total_pay > 0) or (total_receive > 0)
    """)
    update_list = []

    for key in updates:
        account_name = key_name(key[0])
        update_list.append([account_name, key[3], key[4], key[1], key[2]])

    update_list.append(['', '', '', '', ''])
    update_list.append(['', '', '', '', ''])
    update_list.append(['', '', '', '', ''])

    # print(update_list)
    wks.update('A2', update_list)
    wks.update('G1', now.strftime('%d.%m.%Y %H:%M:%S'))

    # Open a sheet from a spreadsheet in one go
    wks = gc.open("MTL_TopHolders").worksheet("DonatesNew")
    update_list = cmd_show_donates(return_table=True)

    wks.update('A2', update_list)
    wks.update('E1', now.strftime('%d.%m.%Y %H:%M:%S'))
    update_list.append(['', '', ''])
    update_list.append(['', '', ''])
    update_list.append(['', '', ''])

    logger.info(f'all done {now}')


if __name__ == "__main__":
    update_donate_report()
