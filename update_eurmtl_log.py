import datetime
import gspread
import json
import requests
import app_logger
import fb
from mystellar import stellar_get_mtl_holders, eurmtl_asset, eurdebt_asset
from settings import currencylayer_id, coinlayer_id

key_rate = 1.6


def get_pair(holders, eurmtl_dic, eurdebt_dic):
    for account in holders:
        # print(json.dumps(account,indent=4))
        # print('***')
        # print(account["balances"])
        balances = account["balances"]
        balance_eurmtl = 0
        balance_eurdebt = 0
        eur = 0
        # check all balanse
        for balance in balances:
            if balance["asset_type"][0:15] == "credit_alphanum":
                if balance["asset_code"] == "EURDEBT":
                    balance_eurdebt = round(float(balance["balance"]), 7)
                if balance["asset_code"] == "EURMTL":
                    balance_eurmtl = round(float(balance["balance"]), 7)
        if balance_eurmtl > 0:
            eurmtl_dic[account["account_id"]] = balance_eurmtl
        if balance_eurdebt > 0:
            eurdebt_dic[account["account_id"]] = balance_eurdebt
        # print(f'{div_sum=},{mtl_sum},{balance_mtl},{balance_rect}')
        # print(eurmtl_dic)
        # print(eurdebt_dic)


def update_eurmtl_log():
    eurmtl_dic = {}
    eurdebt_dic = {}
    insert_list = []

    holders = stellar_get_mtl_holders(eurdebt_asset)
    get_pair(holders, eurmtl_dic, eurdebt_dic)
    holders = stellar_get_mtl_holders(eurmtl_asset)
    get_pair(holders, eurmtl_dic, eurdebt_dic)

    for key in eurmtl_dic:
        persent = eurmtl_dic[key] * (key_rate / 100) / 365
        insert_list.append([key, 'EURMTL', persent])
    for key in eurdebt_dic:
        persent = eurdebt_dic[key] * (key_rate / 100) / 365
        insert_list.append([key, 'EURDEBT', persent])

    fb.manyinsert("insert into t_eurmtl_calc (user_key, asset, amount) values (?,?,?)", insert_list)


def show_key_rate(key):
    if len(key) < 10:
        eurmtl = fb.execsql('select sum(a), count(c) from (select sum(ec.amount) a, count(*) c from t_eurmtl_calc ec '
                            'where ec.was_packed = 0 and ec.asset = ? group by ec.user_key)', ('EURMTL',))[0]
        eurdebt = fb.execsql('select sum(a), count(c) from (select sum(ec.amount) a, count(*) c from t_eurmtl_calc ec '
                             'where ec.was_packed = 0 and ec.asset = ? group by ec.user_key)', ('EURDEBT',))[0]
        result = f'на сейчас начислено и не выплачено {eurmtl[0]} EURMTL {eurdebt[0]} EURDEBT, ' \
                 f'кол-во адресов {eurmtl[1]} EURMTL {eurdebt[1]} EURDEBT'
    else:
        eurmtl = fb.execsql('select sum(ec.amount) from t_eurmtl_calc ec where ec.was_packed = 0 '
                            'and ec.asset = ? and ec.user_key = ?', ('EURMTL', key))[0][0]
        eurdebt = fb.execsql('select sum(ec.amount) from t_eurmtl_calc ec where ec.was_packed = 0 '
                             'and ec.asset = ? and ec.user_key = ?', ('EURDEBT', key))[0][0]
        result = f'для адреса {key} на сейчас начислено и не выплачено {eurmtl} EURMTL {eurdebt} EURDEBT'

    return result


if __name__ == "__main__":
    update_eurmtl_log()
    #print(show_key_rate(''))
