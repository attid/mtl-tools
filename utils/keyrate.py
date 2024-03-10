# import requests
# from loguru import logger
#
# import fb
# from mystellar import stellar_get_holders, eurmtl_asset, eurdebt_asset, get_balances, public_key_rate
#
# key_rate = 1.6
#
#
# @logger.catch
# def get_pair(holders, eurmtl_dic, eurdebt_dic):
#     for account in holders:
#         # print(json.dumps(account,indent=4))
#         # print('***')
#         # print(account["balances"])
#         balances = account["balances"]
#         balance_eurmtl = 0
#         balance_eurdebt = 0
#         eur = 0
#         # check all balanse
#         for balance in balances:
#             if balance["asset_type"][0:15] == "credit_alphanum":
#                 if balance["asset_code"] == "EURDEBT":
#                     balance_eurdebt = round(float(balance["balance"]), 7)
#                 if balance["asset_code"] == "EURMTL":
#                     balance_eurmtl = round(float(balance["balance"]), 7)
#         if balance_eurmtl > 0:
#             eurmtl_dic[account["account_id"]] = balance_eurmtl
#         if balance_eurdebt > 0:
#             eurdebt_dic[account["account_id"]] = balance_eurdebt
#         # print(f'{div_sum=},{mtl_sum},{balance_mtl},{balance_rect}')
#         # print(eurmtl_dic)
#         # print(eurdebt_dic)
#
#
# @logger.catch
# async def update_eurmtl_log():
#     eurmtl_dic = {}
#     eurdebt_dic = {}
#     insert_list = []
#
#     holders = await stellar_get_holders(eurdebt_asset)
#     get_pair(holders, eurmtl_dic, eurdebt_dic)
#     holders = await stellar_get_holders(eurmtl_asset)
#     get_pair(holders, eurmtl_dic, eurdebt_dic)
#
#     for key in eurmtl_dic:
#         persent = eurmtl_dic[key] * (key_rate / 100) / 365
#         insert_list.append([key, 'EURMTL', persent])
#     for key in eurdebt_dic:
#         persent = eurdebt_dic[key] * (key_rate / 100) / 365
#         insert_list.append([key, 'EURDEBT', persent])
#
#     fb.many_insert("insert into t_keyrate (user_key, asset, amount) values (?,?,?)", insert_list)
#
#
# @logger.catch
# def show_key_rate(key='all', check_can_run=False):
#     remains = 0
#     if len(key) < 10:
#         eurmtl = fb.execsql('select sum(a), count(c) from (select sum(ec.amount) a, count(*) c from t_keyrate ec '
#                             'where ec.was_packed = 0 and ec.asset = ? group by ec.user_key)', ('EURMTL',))[0]
#         eurdebt = fb.execsql('select sum(a), count(c) from (select sum(ec.amount) a, count(*) c from t_keyrate ec '
#                              'where ec.was_packed = 0 and ec.asset = ? group by ec.user_key)', ('EURDEBT',))[0]
#
#         result = 'К выплате:'
#
#         if eurmtl[0]:
#             result += f'\n> {round(eurmtl[0], 7)} EURMTL на {eurmtl[1]} адресов'
#             remains -= round(eurmtl[0], 7)
#         if eurdebt[0]:
#             result += f'\n> {round(eurdebt[0], 7)} EURDEBT на {eurdebt[1]} адресов'
#             remains -= round(eurdebt[0], 7)
#
#         balances = get_balances(public_key_rate)
#         remains += float(balances['EURMTL'])
#         remains += float(balances['EURDEBT'])
#
#         result += f"\n\nТекущий баланс бота:\n> {balances['EURMTL']} EURMTL \n> {balances['EURDEBT']} EURDEBT"
#     else:
#         eurmtl = fb.execsql('select sum(ec.amount) from t_keyrate ec where ec.was_packed = 0 '
#                             'and ec.asset = ? and ec.user_key = ?', ('EURMTL', key))[0][0]
#         eurdebt = fb.execsql('select sum(ec.amount) from t_keyrate ec where ec.was_packed = 0 '
#                              'and ec.asset = ? and ec.user_key = ?', ('EURDEBT', key))[0][0]
#         result = f'Для адреса {key[:4]}..{key[-4:]} на текущий момент начислено'
#         if eurmtl:
#             result += '\n> {: .7f} EURMTL '.format(round(eurmtl, 7))
#         if eurdebt:
#             result += '\n> {: .7f} EURDEBT '.format(round(eurdebt, 7))
#
#     if check_can_run:
#         can_run = remains > 0
#         return can_run
#     else:
#         return result
#
#
# if __name__ == "__main__":
#     update_eurmtl_log()
#     # print(show_key_rate('GAHSPXXXAEIGIHQR3Z3KNINXANPUAYGNQTYB5WAHWJXBAKUQ7VKTZVXT'))
