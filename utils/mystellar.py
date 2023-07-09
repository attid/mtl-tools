# import asyncio
# import base64
# import math
# from builtins import print
# from contextlib import suppress
#
# import aiohttp
# import gspread
# from stellar_sdk import Network, Server, TransactionBuilder, Asset, TextMemo, Keypair, \
#     ServerAsync, AiohttpClient, Price
# from stellar_sdk import TransactionEnvelope, FeeBumpTransactionEnvelope  # , Operation, Payment, SetOptions
# import json, requests, datetime
#
# from stellar_sdk.exceptions import NotFoundError
# from stellar_sdk.sep.federation import resolve_account_id_async
#
# from loguru import logger
# from stellar_sdk.xdr import TransactionResult
#
# import fb, re, enum
# from settings import base_fee, private_sign
# from datetime import datetime
#
# # https://stellar-sdk.readthedocs.io/en/latest/
# # https://github.com/StellarCN/py-stellar-base/tree/main/examples
#
#
#
#
#
#
#
#
#
#
#
#
# def stellar_add_drone2(public_key):
#     return stellar_add_trustline(public_key, 'DRONE2DEBT', 'GACJQY4DGVRCVCPURAOH7PH2ERWCG5ATAUXKJFD4ON5ON6PWRJWCBQNN')
#
#
# def stellar_add_mtlcamp(public_key):
#     return stellar_add_trustline(public_key, 'MTLCAMP', 'GBK2NV2L6A6TLKJSEJX3YZH7DEEHOOLB56WIK64Y5T2SFGNCG5FABKUB')
#
#
#
#
# def stellar_check_xdr(xdr):
#     transaction = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
#     list_op = ''
#     i = 0
#     for operation in transaction.transaction.operations:
#         list_op += f'{i} * {operation} \n'
#         i += 1
#     return [transaction.to_xdr(), transaction.transaction.sequence, len(transaction.transaction.operations), list_op]
#
#
# def stellar_set_sequence(xdr, sequence):
#     transaction = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
#     transaction.signatures.clear()
#     transaction.transaction.sequence = sequence
#     return [transaction.to_xdr(), transaction.transaction.sequence, len(transaction.transaction.operations)]
#
#
# def stellar_set_fee(xdr, fee):
#     transaction = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
#     transaction.signatures.clear()
#     transaction.transaction.fee = fee
#     return [transaction.to_xdr(), transaction.transaction.sequence, len(transaction.transaction.operations)]
#
#
# def stellar_set_memo(xdr, memo):
#     transaction = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
#     transaction.signatures.clear()
#     transaction.transaction.memo = TextMemo(memo)
#     return [transaction.to_xdr(), transaction.transaction.sequence, len(transaction.transaction.operations)]
#
#
# def stellar_del_operation(xdr, num):
#     transaction = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
#     transaction.signatures.clear()
#     # transaction.transaction.fee -= 100
#     operation = transaction.transaction.operations.pop(num)
#     return [transaction.to_xdr(), transaction.transaction.sequence, len(transaction.transaction.operations), operation]
#
#
# def stellar_del_sign(xdr, num):
#     transaction = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
#     operation = transaction.signatures.pop(num)
#     return [transaction.to_xdr(), transaction.transaction.sequence, len(transaction.transaction.operations),
#             operation]
#
#
# def stellar_add_xdr(xdr, xdr2):
#     transaction = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
#     transaction2 = TransactionEnvelope.from_xdr(xdr2, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
#     for operation in transaction2.transaction.operations:
#         transaction.transaction.operations.append(operation)
#     transaction.transaction.fee += transaction.transaction.fee
#     return [transaction.to_xdr(), transaction.transaction.sequence, len(transaction.transaction.operations)]
#
#
# def username_to_address_id(username: str) -> list:
#     with open('members_key.json', 'r', encoding='UTF-8') as fp:
#         data: dict = json.load(fp)
#     result = []
#     if username in data.values():
#         for key in data:
#             if data[key] == username:
#                 result.append(data[key])
#     return result
#
#
#
# def load_xdr(xdr) -> TransactionEnvelope:
#     if FeeBumpTransactionEnvelope.is_fee_bump_transaction_envelope(xdr):
#         fee_transaction = FeeBumpTransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
#         transaction = fee_transaction.transaction.inner_transaction_envelope
#     else:
#         transaction = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
#     return transaction
#
#
#
#
#
#
#
#
#
#
# async def cmd_gen_key_rate_xdr(list_id):
#     memo = fb.execsql(f'select dl.memo from t_div_list dl where dl.id = {list_id}')[0][0]
#     pay_type = fb.execsql(f'select dl.pay_type from t_div_list dl where dl.id = {list_id}')[0][0]
#     records = fb.execsql(f"select first {pack_count} e.asset, e.user_key, sum(e.amount) amount from t_keyrate e "
#                          f"where e.was_packed = 0 group by e.user_key, e.asset order by e.asset")
#
#     accounts_list = []
#     accounts = await stellar_get_mtl_holders(eurmtl_asset)
#     for account in accounts:
#         accounts_list.append(f"{account['account_id']}-EURMTL")
#     accounts = await stellar_get_mtl_holders(eurdebt_asset)
#     for account in accounts:
#         accounts_list.append(f"{account['account_id']}-EURDEBT")
#
#     server = Server(horizon_url="https://horizon.stellar.org")
#     # if pay_type != 3: exit
#     div_account = server.load_account(public_key_rate)
#
#     transaction = TransactionBuilder(source_account=div_account, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
#                                      base_fee=base_fee)
#     transaction.set_timeout(60 * 60)
#
#     for record in records:
#         if f"{record[1]}-{record[0]}" in accounts_list:
#             if round(record[2], 7) > 0:
#                 transaction.append_payment_op(destination=record[1], amount=str(round(record[2], 7)),
#                                               asset=Asset(record[0], public_issuer))
#                 fb.execsql('update t_keyrate set was_packed = ? where asset = ? and user_key = ? and was_packed = 0',
#                            [list_id, record[0], record[1]])
#         else:
#             fb.execsql('update t_keyrate set was_packed = ? where asset = ? and user_key = ? and was_packed = 0',
#                        [-1, record[0], record[1]])
#
#     transaction.add_text_memo(memo)
#     transaction = transaction.build()
#     xdr = transaction.to_xdr()
#     # print(f"xdr: {xdr}")
#
#     fb.execsql("insert into T_TRANSACTION (ID_DIV_LIST, XDR_ID, XDR) values (?,?,?)", [list_id, 0, xdr])
#     need = fb.execsql('select count(*) from t_keyrate where was_packed = 0 and amount > 0.0001', [list_id])[0][0]
#     # print(f'need {need} more')
#     return need
#
#
#
# def cmd_alarm_pin_url(chat_id):
#     url = cmd_load_bot_value(BotValueTypes.PinnedUrl, chat_id)
#     return cmd_alarm_url_(url)
#
#
# def cmd_get_info(my_id):
#     s = requests.get(f'http://rzhunemogu.ru/RandJSON.aspx?CType={my_id}').text
#     return s[12:-2]
#     # 1 - Анекдот; 4 - Афоризмы; 6 - Тосты; 8 - Статусы;
#     # 11 - Анекдот (+18);#12 - Рассказы (+18); 13 - Стишки (+18);  14 - Афоризмы (+18); 15 - Цитаты (+18);  16 - Тосты (+18); 18 - Статусы (+18);
#
#
#
# def cmd_check_new_asset_transaction_old(asset_name: str, save_id: BotValueTypes, filter_sum: int = -1,
#                                         filter_operation=None, issuer=public_issuer, filter_asset=None):
#     if filter_operation is None:
#         filter_operation = []
#     result = []
#     transactions = {}
#     last_id = int(cmd_load_bot_value(save_id, 0, '0'))
#     max_id = last_id
#     rq = requests.get(
#         f"https://api.stellar.expert/explorer/public/asset/{asset_name}-{issuer}/history/all?limit=10&order=desc&sort=id").json()
#     # print(json.dumps(rq, indent=4))
#     for operation in rq["_embedded"]["records"]:
#         current_id = int(operation["id"])
#         if current_id == last_id:
#             break
#         my_operation = Server(horizon_url="https://horizon.stellar.org").operations().operation(operation["id"]).call()
#         # print(my_operation["_links"]["transaction"]["href"])
#         transaction = requests.get(my_operation["_links"]["transaction"]["href"]).json()
#         transactions[transaction["paging_token"]] = {
#             'link': f'https://stellar.expert/explorer/public/tx/{transaction["paging_token"]}',
#             'envelope_xdr': transaction["envelope_xdr"]}
#         if current_id > max_id:
#             max_id = current_id
#
#     for paging_token in transactions:
#         xdr_result = decode_xdr(transactions[paging_token]["envelope_xdr"], filter_sum=filter_sum,
#                                 filter_operation=filter_operation,
#                                 filter_asset=filter_asset)
#         if len(xdr_result) > 0:
#             link = transactions[paging_token]["link"]
#             xdr_result.insert(0, f'(<a href="{link}">expert link</a>)')
#             result.append(xdr_result)
#         # print(decode_xdr(transaction["envelope_xdr"]))
#
#     cmd_save_bot_value(save_id, 0, max_id)
#     return result
#
#
# def cmd_gen_div_xdr(div_sum):
#     server = Server(horizon_url="https://horizon.stellar.org")
#
#     div_account = server.load_account(public_issuer)
#
#     transaction = TransactionBuilder(source_account=div_account, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
#                                      base_fee=base_fee)
#     transaction.set_timeout(60 * 60)
#
#     transaction.append_payment_op(destination=public_div, amount=str(round(div_sum, 7)), asset=eurmtl_asset)
#
#     transaction.add_text_memo(datetime.datetime.now().strftime('mtl div %d/%m/%Y'))
#     transaction = transaction.build()
#     xdr = transaction.to_xdr()
#     # print(f"xdr: {xdr}")
#     return xdr
#
#
#
#
#
# def cmd_show_guards():
#     account_json = requests.get(
#         f'https://horizon.stellar.org/accounts/GDEK5KGFA3WCG3F2MLSXFGLR4T4M6W6BMGWY6FBDSDQM6HXFMRSTEWBW').json()
#     result_data = []
#     if "data" in account_json:
#         data = account_json["data"]
#         for data_name in list(data):
#             data_value = data[data_name]
#             if data_name[:13] == 'bod_guarantor':
#                 result_data.append(f'{data_name} => {decode_data_value(data_value)}')
#                 x = cmd_show_data(decode_data_value(data_value), 'bod')
#                 result_data.extend(x)
#             result_data.append('***')
#             # print(data_name, decode_data_vlue(data_value))
#     return result_data
#
#
#
# async def cmd_gen_usdm_vote_list(return_delegate_list: bool = False, mini=False):
#     account_list = []
#     accounts = await stellar_get_mtl_holders(mini=mini, asset=usdmm_asset)
#
#     # mtl
#     for account in accounts:
#         balances = account["balances"]
#         balance_usdmm = 0
#         for balance in balances:
#             if balance["asset_type"][0:15] == "credit_alphanum":
#                 if balance["asset_code"] == "USDMM" and balance["asset_issuer"] == public_usdm:
#                     balance_usdmm = float(balance["balance"])
#         # lg = round(math.log2((balance_mtl + balance_rect + 0.001) / divider))
#         if account["account_id"] != 'GAQ5ERJVI6IW5UVNPEVXUUVMXH3GCDHJ4BJAXMAAKPR5VBWWAUOMABIZ':
#             vote = round(balance_usdmm)
#             if account["account_id"] in ('GBYH3M3REQM3WQOJY26FYORN23EXY22FWBHVZ74TT5GYOF22IIA7YSOX',
#                                          'GBVIX6CZ57SHXHGPA4AL7DACNNZX4I2LCKIAA3VQUOGTGWYQYVYSE5TU',
#                                          'GDLTH4KKMA4R2JGKA7XKI5DLHJBUT42D5RHVK6SS6YHZZLHVLCWJAYXI'):
#                 vote += 17
#             account_list.append([account["account_id"], balance_usdmm, vote, 0, account['data']])
#     # 2
#     big_list = []
#     for arr in account_list:
#         if float(arr[1]) > 0:
#             big_list.append(arr)
#     big_list.sort(key=lambda k: k[1], reverse=True)
#
#     # find delegate
#     delegate_list = {}
#     for account in big_list:
#         if account[4]:
#             data = account[4]
#             for data_name in list(data):
#                 data_value = data[data_name]
#                 if data_name in ('delegate', 'mtl_delegate'):
#                     delegate_list[account[0]] = decode_data_value(data_value)
#
#     if return_delegate_list:
#         return delegate_list
#
#     # delete blacklist user
#     bl = cmd_getblacklist()
#     for arr in big_list:
#         if bl.get(arr[0]):
#             arr[1] = 0
#             arr[2] = 0
#             # vote_list.remove(arr)
#             # print(arr)
#
#     for arr_from in big_list:
#         if delegate_list.get(arr_from[0]):
#             for arr_for in big_list:
#                 if arr_for[0] == delegate_list[arr_from[0]]:
#                     arr_for[1] += arr_from[1]
#                     arr_from[1] = 0
#                     delegate_list.pop(arr_from[0])
#                     arr_for[2] = round(float(arr_for[1]))
#                     arr_from[2] = 0
#                     break
#             # vote_list.remove(arr)
#             # print(arr,source)
#
#     big_list.sort(key=lambda k: k[1], reverse=True)
#     big_list = big_list[:20]
#     total_sum = 0
#     for account in big_list:
#         total_sum += account[1]
#     # divider = total_sum#ceil() #big_list[19][1]
#     total_vote = 0
#     for account in big_list:
#         total_vote += account[2]
#
#     return big_list
#
#
#
#
#
#
#
# async def get_mrxpinvest_xdr(div_sum: float):
#     accounts = await stellar_get_mtl_holders(mrxpinvest_asset)
#     accounts_list = []
#     total_sum = 0
#
#     for account in accounts:
#         balances = account["balances"]
#         token_balance = 0
#         for balance in balances:
#             if balance["asset_type"][0:15] == "credit_alphanum":
#                 if balance["asset_code"] == mrxpinvest_asset.code:
#                     token_balance = balance["balance"]
#                     token_balance = int(token_balance[0:token_balance.find('.')])
#         if account["account_id"] != 'GDIWYLCDWPXEXFWUI7PGO64UFYWYDIVCXQWD2IKHM3WYFEXA2E4ZOC4Z':
#             accounts_list.append([account["account_id"], token_balance, 0])
#             total_sum += token_balance
#
#     persent = div_sum / total_sum
#
#     for account in accounts_list:
#         account[2] = account[1] * persent
#
#     root_account = Server(horizon_url="https://horizon.stellar.org").load_account(mrxpinvest_asset.issuer)
#     transaction = TransactionBuilder(source_account=root_account, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
#                                      base_fee=base_fee)
#     transaction.set_timeout(60 * 60)
#     for account in accounts_list:
#         transaction.append_payment_op(destination=account[0], asset=mrxpinvest_asset, amount=str(round(account[2], 7)))
#     transaction = transaction.build()
#     xdr = transaction.to_xdr()
#
#     return xdr
#
#
#
#
#
#
# def stellar_check_receive_sum(send_asset: Asset, send_sum: str, receive_asset: Asset) -> str:
#     try:
#         server = Server(horizon_url="https://horizon.stellar.org")
#         call_result = server.strict_send_paths(send_asset, send_sum, [receive_asset]).call()
#         if len(call_result['_embedded']['records']) > 0:
#             # print(call_result)
#             return call_result['_embedded']['records'][0]['destination_amount']
#         else:
#             return '0'
#     except Exception as ex:
#         logger.exception("stellar_check_receive_sum", send_asset.code + ' ' + send_sum + ' ' + receive_asset.code, ex)
#         return '0'
#
#
#
# async def cmd_update_fee_and_send(xdr: str) -> str:
#     transaction = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
#     fee_transaction = TransactionBuilder.build_fee_bump_transaction(public_sign, 10000, transaction,
#                                                                     Network.PUBLIC_NETWORK_PASSPHRASE)
#     transaction.set_timeout(60 * 60)
#     # fee_transaction = FeeBumpTransactionEnvelope(FeeBumpTransaction(public_sign, 10000, transaction),
#     #                                             network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
#     fee_transaction.sign(private_sign)
#     server = Server(horizon_url="https://horizon.stellar.org")
#     resp = await stellar_async_submit(fee_transaction.to_xdr())
#
#     return str(resp)
#
#
#
#
#
#
# def stellar_claimable(source_address, asset, amount, destination_address, xdr=None):
#     if xdr:
#         transaction = TransactionBuilder.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
#     else:
#         server = Server(horizon_url="https://horizon.stellar.org")
#         root_account = server.load_account(source_address)
#         transaction = TransactionBuilder(source_account=root_account,
#                                          network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
#                                          base_fee=base_fee)
#         transaction.set_timeout(60 * 60)
#     from stellar_sdk import Claimant
#     transaction.append_create_claimable_balance_op(asset, amount, [Claimant(destination=source_address),
#                                                                    Claimant(destination=destination_address)])
#     transaction = transaction.build()
#     xdr = transaction.to_xdr()
#     # print(f"xdr: {xdr}")
#     return xdr
#
#
# def stellar_claim_claimable(source_address, balance_id, xdr=None):
#     if xdr:
#         transaction = TransactionBuilder.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
#     else:
#         server = Server(horizon_url="https://horizon.stellar.org")
#         root_account = server.load_account(source_address)
#         transaction = TransactionBuilder(source_account=root_account,
#                                          network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
#                                          base_fee=base_fee)
#         transaction.set_timeout(60 * 60)
#
#     transaction.append_claim_claimable_balance_op(balance_id=balance_id)
#     transaction = transaction.build()
#     xdr = transaction.to_xdr()
#     return xdr
#
#
# async def send_satsmtl_pending():
#     accounts = await stellar_get_mtl_holders()
#     print(len(accounts))
#     cnt = 0
#     xdr = None
#     for account in accounts:
#         cnt += 1
#         xdr = stellar_claimable(public_div, satsmtl_asset, '1', account['id'], xdr=xdr)
#         if cnt > 96:
#             print(xdr)
#             stellar_sync_submit(stellar_sign(xdr, private_sign))
#             xdr = None
#             cnt = 0
#     print(xdr)
#     stellar_sync_submit(stellar_sign(xdr, private_sign))
#
#
# def save_usdc_accounts():
#     server = Server(horizon_url="https://horizon.stellar.org")
#     accounts = []
#     accounts_call_builder = server.accounts().for_asset(
#         Asset('USDC', 'GA5ZSEJYB37JRC5AVCIA5MOP4RHTM335X2KGX3IHOJAPP5RE34K4KZVN')).limit(200)
#
#     accounts += accounts_call_builder.call()["_embedded"]["records"]
#     i = 0
#
#     while page_records := accounts_call_builder.next()["_embedded"]["records"]:
#         accounts += page_records
#         i += 1
#         print(i)
#         for account in accounts:
#             assets = {}
#             for balance in account['balances']:
#                 if balance['asset_type'] == "native":
#                     assets['XLM'] = float(balance['balance'])
#                 elif balance["asset_type"][0:15] == "credit_alphanum":
#                     assets[balance['asset_code']] = float(balance['balance'])
#             fb.execsql('update or insert into t_pending (address_id, xlm, usdc, home_domain) '
#                        'values (?,?,?,?) matching (address_id)',
#                        (account['id'], int(assets['XLM']), int(assets['USDC']), account.get('home_domain')))
#             accounts.remove(account)
#
#     # print(json.dumps(response, indent=4))
#     print(json.dumps(accounts, indent=4))
#
#
# # from loguru import logger
#
#
# @logger.catch
# def send_mtl_pending():
#     records = fb.execsql(f"select address_id from t_pending where dt_send is null and home_domain = ?", ['lobstr.co'])
#     print(len(records))
#     cnt = 0
#     xdr = None
#     for rec in records:
#         cnt += 1
#         xdr = stellar_claimable(public_wallet, mtl_asset, '0.2', rec[0], xdr=xdr)
#         fb.execsql(f"update t_pending set dt_send = localtimestamp where address_id = ?", [rec[0]])
#         if cnt > 96:
#             print(xdr)
#             fb.execsql("insert into T_TRANSACTION (ID_DIV_LIST, XDR_ID, XDR) values (?,?,?)", [5, 10, xdr])
#             stellar_sync_submit(stellar_sign(xdr, private_sign))
#             xdr = None
#             cnt = 0
#     print(xdr)
#     fb.execsql("insert into T_TRANSACTION (ID_DIV_LIST, XDR_ID, XDR) values (?,?,?)", [5, 10, xdr])
#     stellar_sync_submit(stellar_sign(xdr, private_sign))
#
#
# def no_err():
#     with suppress(NotFoundError):
#         cb = Server(horizon_url="https://horizon.stellar.org").transactions().transaction(
#             '8bde064fe81b9383543ba2e043fe47f0a916941f390564a4dcab33d44fd81ab8').call()
#         print(cb)
#
#
# def return_satsmtl_pending():
#     cb_cb = Server(horizon_url="https://horizon.stellar.org").claimable_balances().for_sponsor(public_div).limit(
#         90).call()
#     xdr = None
#     for record in cb_cb['_embedded']['records']:
#         xdr = stellar_claim_claimable(public_div, record['id'], xdr=xdr)
#
#     stellar_sync_submit(stellar_sign(xdr, private_sign))
#
#
# def return_mtl_pending():
#     cb_cb = Server(horizon_url="https://horizon.stellar.org").claimable_balances().for_sponsor(public_wallet).limit(
#         10).call()
#     xdr = None
#     insert = []
#     for record in cb_cb['_embedded']['records']:
#         # print(record['claimants'][1]['destination'])
#         insert.append([record['claimants'][1]['destination']])
#         xdr = stellar_claim_claimable(public_wallet, record['id'], xdr=xdr)
#
#     stellar_sync_submit(stellar_sign(xdr, private_sign))
#     fb.many_insert(f"update t_pending set dt_back = localtimestamp where address_id = ?", insert)
#
#
# def save_transactions():
#     cb_cb = Server(horizon_url="https://horizon.stellar.org").transactions().for_account(public_wallet).limit(
#         200).order()
#     cb_list = []
#     returned_list = []
#     i = 0
#     records = cb_cb.call()
#     while len(records['_embedded']['records']) > 0:
#         for record in records['_embedded']['records']:
#             xdr = record['envelope_xdr']
#             transaction = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
#             txResult = TransactionResult.from_xdr(record["result_xdr"])
#             results = txResult.result.results
#             if type(transaction.transaction.operations[0]).__name__ == 'CreateClaimableBalance':
#                 if transaction.transaction.operations[0].asset.code == 'MTL':
#                     for idx, operation in enumerate(transaction.transaction.operations):
#                         operationResult = results[idx].tr.create_claimable_balance_result
#                         balanceId = operationResult.balance_id.to_xdr_bytes().hex()
#                         # print(f"Balance ID (2): {balanceId}")
#                         # print(operation.claimants[1].destination)
#                         cb_list.append([operation.claimants[1].destination, balanceId])
#             if type(transaction.transaction.operations[0]).__name__ == 'ClaimClaimableBalance':
#                 for operation in transaction.transaction.operations:
#                     # print(operation.balance_id)
#                     returned_list.append([operation.balance_id])
#
#         records = cb_cb.next()
#         i += 1
#         print(i)
#
#     with open(f"cb_list.json", "w") as fp:
#         json.dump(cb_list, fp, indent=2)
#     with open(f"returned_list.json", "w") as fp:
#         json.dump(returned_list, fp, indent=2)
#     #############################
#     with open('returned_list.json', 'r', encoding='UTF-8') as fp:
#         data = json.load(fp)
#     print(data)
#     fb.many_insert(f"update t_pending set dt_back = localtimestamp where dt_back is null and CLAIMABLE_BALANCE_ID = ?",
#                    data)
#
#
# async def send_msg_to_mtl():
#     holders = await stellar_get_mtl_holders(mini=False)
#     i = 0
#     x = 0
#     transaction = TransactionBuilder(
#         source_account=Server(horizon_url="https://horizon.stellar.org").load_account(public_pending),
#         network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
#         base_fee=base_fee)
#     transaction.set_timeout(60 * 60)
#
#     for record in holders:
#         found1 = list(filter(lambda x: x.get('asset_code') == 'EURMTL', record['balances']))
#         found2 = list(filter(lambda x: x.get('asset_code') == 'SATSMTL', record['balances']))
#         if len(found1) > 0 and len(found2) > 0:
#             print('found ' + record['id'])
#         else:
#             print('not found', record['id'], i)
#             i = i + 1
#             x = x + 1
#             transaction.append_payment_op(destination=record['id'], amount='0.0000001', asset=mtl_asset)
#             if i > 90:
#                 i = 0
#                 transaction.add_text_memo('Visit our site for dividends')
#                 xdr = transaction.build().to_xdr()
#                 print(xdr)
#                 stellar_sync_submit(stellar_sign(xdr, private_sign))
#                 # new tr
#                 transaction = TransactionBuilder(
#                     source_account=Server(horizon_url="https://horizon.stellar.org").load_account(public_pending),
#                     network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
#                     base_fee=base_fee)
#                 transaction.set_timeout(60 * 60)
#
#     transaction.add_text_memo('Visit our site for dividends')
#     xdr = transaction.build().to_xdr()
#     print(xdr)
#     stellar_sync_submit(stellar_sign(xdr, private_sign))
#     print(x)
#
#
#
# async def get_clear_data_xdr(address: str):
#     acc = await stellar_get_account(address)
#     xdr = None
#     for data_name in acc['data']:
#         xdr = cmd_gen_data_xdr(address, data_name + ':', xdr)
#     return xdr
#
#
# def get_memo_by_op(op: str):
#     operation = Server(horizon_url="https://horizon.stellar.org").operations().operation(op).call()
#     transaction = Server(horizon_url="https://horizon.stellar.org").transactions().transaction(
#         operation['transaction_hash']).call()
#
#     return transaction.get('memo', 'None')
#
#
# if __name__ == "__main__":
#     print(gen_new('OUT'))
#     # a = asyncio.run(get_defi_xdr(677000))
#     # print('\n'.join(decode_xdr(a)))
#     # print(asyncio.run(get_balances('GDX23CPGMQ4LN55VGEDVFZPAJMAUEHSHAMJ2GMCU2ZSHN5QF4TMZYPIS', return_data=True)))
#     # s = asyncio.run(cmd_show_data(public_div,'LAST_DIVS',True))
#     # print(cmd_check_new_asset_transaction('MTL',BotValueTypes.LastMTLTransaction,10))
#     # xdr = cmd_gen_data_xdr(public_div,'LAST_DIVS:1386')
#     # print(gen_new('USD'))
#     # xdr = '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'
#     # xdr2 = 'AAAAAgAAAAAQoKcL6PJThXuPDvKgGqbyQM0/1HK385wAq65jOhf2/wAAE4gCeukxAAAABAAAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEAAAABAAAAABCgpwvo8lOFe48O8qAapvJAzT/UcrfznACrrmM6F/b/AAAABQAAAAAAAAAAAAAAAAAAAAAAAAABAAAAAQAAAAEAAAABAAAAAQAAAAEAAAAAAAAAAAAAAAAAAAAA'
#     # print(stellar_sync_submit(stellar_sign(xdr, private_sign)))
#     # print(stellar_add_xdr(xdr, xdr2))
#     # print(decode_xdr(
#     #    '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'))
#     pass
