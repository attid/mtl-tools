import base64

from stellar_sdk import Network, Server, TransactionBuilder, Asset, Account, TextMemo
from stellar_sdk import TransactionEnvelope  # , Operation, Payment, SetOptions
import json, requests, datetime

from stellar_sdk.sep.federation import resolve_stellar_address, resolve_account_id

import fb, re, enum
from settings import private_div, private_bod_eur

# https://stellar-sdk.readthedocs.io/en/latest/

public_mtl = "GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V"
public_fond = "GDX23CPGMQ4LN55VGEDVFZPAJMAUEHSHAMJ2GMCU2ZSHN5QF4TMZYPIS"
public_pawnshop = "GDASYWP6F44TVNJKZKQ2UEVZOKTENCJFTWVMP6UC7JBZGY4ZNB6YAVD4"
public_distributor = "GB7NLVMVC6NWTIFK7ULLEQDF5CBCI2TDCO3OZWWSFXQCT7OPU3P4EOSR"

public_bod_eur = "GDEK5KGFA3WCG3F2MLSXFGLR4T4M6W6BMGWY6FBDSDQM6HXFMRSTEWBW"
public_bod = "GARUNHJH3U5LCO573JSZU4IOBEVQL6OJAAPISN4JKBG2IYUGLLVPX5OH"
public_div = "GDNHQWZRZDZZBARNOH6VFFXMN6LBUNZTZHOKBUT7GREOWBTZI4FGS7IQ"

mtl_asset = Asset("MTL", public_mtl)
eurmtl_asset = Asset("EURMTL", public_mtl)
eurdebt_asset = Asset("EURDEBT", public_mtl)


class BotValueTypes(enum.IntEnum):
    PinnedUrl = 1
    LastFondTransaction = 2
    LastDebtTransaction = 3
    PinnedId = 4
    LastEurTransaction = 5
    LastRectTransaction = 6
    LastMTLTransaction = 7


def stellar_add_fond_trustline(userkey, asset_code):
    return stellar_add_trustline(userkey, asset_code, public_mtl)


def stellar_get_mtl_holders(asset=mtl_asset):
    server = Server(horizon_url="https://horizon.stellar.org")
    accounts = []
    accounts_call_builder = server.accounts().for_asset(asset).limit(50)

    accounts += accounts_call_builder.call()["_embedded"]["records"]

    while page_records := accounts_call_builder.next()["_embedded"]["records"]:
        accounts += page_records
    # print(json.dumps(response, indent=4))

    return accounts


def stellar_add_trustline(userkey, asset_code, asset_issuer):
    # keypair = Keypair.from_public_key(userkey)
    # can_sign = keypair.can_sign()  # False
    # print(keypair)

    server = Server(horizon_url="https://horizon.stellar.org")
    source_account = server.load_account(userkey)
    mysequence = source_account.sequence

    root_account = Account(userkey, sequence=mysequence)
    transaction = TransactionBuilder(source_account=root_account, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                     base_fee=100)
    transaction.append_change_trust_op(Asset(asset_code, asset_issuer))
    transaction = transaction.build()

    xdr = transaction.to_xdr()
    # print(f"xdr: {xdr}")
    return xdr


def stellar_add_drone2(userkey):
    return stellar_add_trustline(userkey, 'DRONE2DEBT', 'GACJQY4DGVRCVCPURAOH7PH2ERWCG5ATAUXKJFD4ON5ON6PWRJWCBQNN')


def stellar_add_mtlcamp(userkey):
    return stellar_add_trustline(userkey, 'MTLCAMP', 'GBK2NV2L6A6TLKJSEJX3YZH7DEEHOOLB56WIK64Y5T2SFGNCG5FABKUB')


def stellar_sign(xdr, signkey):
    transaction = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
    transaction.sign(signkey)
    return transaction.to_xdr()


def stellar_submite(xdr):
    # Last, you can submit it to the network
    transaction = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
    server = Server(horizon_url="https://horizon.stellar.org")
    resp = server.submit_transaction(transaction)

    # json_dump = json.dumps(resp)
    # print(json_dump)
    # response_json = json.loads(json_dump)

    return json.dumps(resp, indent=2)


def stellar_check_xdr(xdr):
    transaction = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
    transaction.signatures.clear()
    list_op = ''
    i = 0
    for operation in transaction.transaction.operations:
        list_op += f'{i} * {operation} \n'
        i += 1
    return [transaction.to_xdr(), transaction.transaction.sequence, len(transaction.transaction.operations), list_op]


def stellar_set_sequence(xdr, sequence):
    transaction = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
    transaction.signatures.clear()
    transaction.transaction.sequence = sequence
    return [transaction.to_xdr(), transaction.transaction.sequence, len(transaction.transaction.operations)]


def stellar_set_fee(xdr, fee):
    transaction = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
    transaction.signatures.clear()
    transaction.transaction.fee = fee
    return [transaction.to_xdr(), transaction.transaction.sequence, len(transaction.transaction.operations)]


def stellar_set_memo(xdr, memo):
    transaction = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
    transaction.signatures.clear()
    transaction.transaction.memo = TextMemo(memo)
    return [transaction.to_xdr(), transaction.transaction.sequence, len(transaction.transaction.operations)]


def stellar_del_operation(xdr, num):
    transaction = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
    transaction.signatures.clear()
    transaction.signatures.fee -= 100
    operation = transaction.transaction.operations.pop(num)
    return [transaction.to_xdr(), transaction.transaction.sequence, len(transaction.transaction.operations), operation]


def stellar_add_xdr(xdr, xdr2):
    transaction = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
    transaction2 = TransactionEnvelope.from_xdr(xdr2, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
    for operation in transaction2.transaction.operations:
        transaction.transaction.operations.append(operation)
    transaction.transaction.fee += transaction.transaction.fee
    return [transaction.to_xdr(), transaction.transaction.sequence, len(transaction.transaction.operations)]


def key_name(key):
    with open('members_key.json', 'r', encoding='UTF-8') as fp:
        data = json.load(fp)
    if key in data:
        return data[key]
    else:
        return key[:4] + '..' + key[-4:]


def good_operation(operation, operation_name, filter_operation, ignore_operation):
    if operation_name in ignore_operation:
        return False
    elif type(operation).__name__ == operation_name:
        return (not filter_operation) or (operation_name in filter_operation)
    return False


def decode_xdr(xdr, filter_sum: int = -1, filter_operation=[], ignore_operation=[]):
    result = []
    data_exist = False

    transaction = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
    result.append(f"Операции с аккаунта {key_name(transaction.transaction.source.account_id)}")
    result.append(f"  Memo {transaction.transaction.memo}\n")
    result.append(f"  Всего {len(transaction.transaction.operations)} операций\n")

    for idx, operation in enumerate(transaction.transaction.operations):
        result.append(f"Операция {idx} - {type(operation).__name__}")
        # print('bad xdr', idx, operation)
        if operation.source:
            result.append(f"*** для аккаунта {key_name(operation.source.account_id)}")
        if good_operation(operation, "Payment", filter_operation, ignore_operation):
            if float(operation.amount) > filter_sum:
                data_exist = True
                result.append(
                    f"    Перевод {operation.amount} {operation.asset.code} на аккаунт {key_name(operation.destination.account_id)}")
            continue
        if good_operation(operation, "SetOptions", filter_operation, ignore_operation):
            data_exist = True
            if operation.signer:
                result.append(
                    f"    Изменяем подписанта {key_name(operation.signer.signer_key.encoded_signer_key)} новые голоса : {operation.signer.weight}")
            if operation.med_threshold:
                data_exist = True
                result.append(f"Установка нового требования. Нужно будет {operation.med_threshold} голосов")
            continue
        if good_operation(operation, "ChangeTrust", filter_operation, ignore_operation):
            data_exist = True
            result.append(
                f"    Открываем линию доверия к токену {operation.asset.code} от аккаунта {key_name(operation.asset.issuer)}")
            continue
        if good_operation(operation, "CreateClaimableBalance", filter_operation, ignore_operation):
            data_exist = True
            result.append(f"  Спам {operation.asset.code}")
            result.append(f"  Остальные операции игнорируются.")
            break
        if good_operation(operation, "ManageSellOffer", filter_operation, ignore_operation):
            if float(operation.amount) > filter_sum:
                data_exist = True
                result.append(
                    f"    Офер на продажу {operation.amount} {operation.selling.code} по цене {operation.price.n / operation.price.d} {operation.buying.code}")
            continue
        if good_operation(operation, "ManageBuyOffer", filter_operation, ignore_operation):
            if float(operation.amount) > filter_sum:
                data_exist = True
                result.append(
                    f"    Офер на покупку {operation.amount} {operation.buying.code} по цене {operation.price.n / operation.price.d} {operation.selling.code}")
            continue
        if good_operation(operation, "PathPaymentStrictSend", filter_operation, ignore_operation):
            data_exist = True
            result.append(
                f"    Покупка {key_name(operation.destination.account_id)}, шлем {operation.send_asset.code} {operation.send_amount} в обмен на {operation.dest_asset.code} min {operation.dest_min} ")
            continue
        if good_operation(operation, "PathPaymentStrictReceive", filter_operation, ignore_operation):
            data_exist = True
            result.append(
                f"    Продажа ? {key_name(operation.destination.account_id)}, Получаем {operation.send_asset.code} max {operation.send_max} в обмен на {operation.dest_asset.code} {operation.dest_amount} ")
            continue
        if good_operation(operation, "ManageData", filter_operation, ignore_operation):
            data_exist = True
            result.append(
                f"    ManageData {operation.data_name} = {operation.data_value} ")
            continue
        if type(operation).__name__ in ["PathPaymentStrictSend", "ManageBuyOffer", "ManageSellOffer",
                                        "PathPaymentStrictReceive",
                                        "CreateClaimableBalance", "ChangeTrust", "SetOptions", "Payment", "ManageData"]:
            continue

        data_exist = True
        result.append(f"Прости хозяин, не понимаю")
        print('bad xdr', idx, operation)
    if data_exist:
        return result
    else:
        return []


def check_url_xdr(url):
    rq = requests.get(url).text
    rq = rq[rq.find('<span class="tx-body">') + 22:]
    # print(rq)
    rq = rq[:rq.find('</span>')]
    rq = rq.replace("&#x3D;", "=")
    # print(rq)
    return decode_xdr(rq)


def get_bod_list():
    server = Server(horizon_url="https://horizon.stellar.org")
    tr = server.transactions().for_account(public_bod).order(desc=True).call()
    # print(json.dumps(tr["_embedded"]["records"][1], indent=4))
    adresses = []
    for record in tr["_embedded"]["records"]:
        if (record["memo_type"] == "text") and (record["memo"] == "Basic Income"):
            # print(record["created_at"])
            #                                                      "2021-12-17T00:00:50Z"
            dt1 = datetime.datetime.strptime(record["created_at"], '%Y-%m-%dT%H:%M:%SZ')
            # print(dt1.date())
            dt2 = datetime.datetime(2021, 12, 17)  # datetime.datetime.now()
            # print(dt2.date())
            # if dt1.date() == dt2.date():
            # print(record["envelope_xdr"])
            xdr = record["envelope_xdr"]
            transaction = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
            for operation in transaction.transaction.operations:
                adresses.append(operation.destination.account_id)
                # print(operation.destination.account_id)
            break
            # check eurmtl
    result = []
    for adress in adresses:
        # print(val)
        # get balance
        balances = {}
        rq = requests.get(f'https://horizon.stellar.org/accounts/{adress}').json()
        # print(json.dumps(rq, indent=4))
        for balance in rq["balances"]:
            if balance["asset_type"] == 'credit_alphanum12':
                balances[balance["asset_code"]] = balance["balance"]
        haseur = 'EURMTL' in balances
        result.append([adress, haseur])
    return result


def cmd_show_bod():
    result = ''
    bod_list = get_bod_list()
    good = list(filter(lambda x: x[1], bod_list))

    total_sum = \
        fb.execsql(
            'select sum(p.user_div) from t_payments p join t_div_list d on d.id = p.id_div_list and d.pay_type = 1')[
            0][0]

    result += f'Всего {len(bod_list)} участников'
    result += f'\n{len(good)} участников c доступом к EURMTL'
    result += f'\nЧерез систему за всю историю выплачено {round(total_sum, 2)} EURMTL'

    balances = {}
    rq = requests.get(f'https://horizon.stellar.org/accounts/{public_bod_eur}').json()
    # print(json.dumps(rq, indent=4))
    for balance in rq["balances"]:
        if balance["asset_type"] == 'credit_alphanum12':
            balances[balance["asset_code"]] = balance["balance"]

    result += f'\n\nСейчас к распределению {balances["EURMTL"]} EURMTL или по {int(float(balances["EURMTL"]) / len(good) * 100) / 100} на участника'
    result += f'\nНачать выплаты /do_bod'
    return result


def get_key_1(key):
    return key[1]


def cmd_create_list(memo, paytype):
    return fb.execsql(f"insert into T_DIV_LIST (MEMO,pay_type) values ('{memo}',{paytype}) returning ID")[0][0]


def cmd_calc_divs(div_list_id: int, donate_list_id: int, test_sum=0):
    server = Server(horizon_url="https://horizon.stellar.org")

    # MTL
    rq = requests.get(f'https://horizon.stellar.org/assets?asset_code=MTL&asset_issuer={public_mtl}')
    mtl_sum = float(rq.json()['_embedded']['records'][0]['amount'])
    # FOND
    rq = requests.get('https://horizon.stellar.org/accounts/GDX23CPGMQ4LN55VGEDVFZPAJMAUEHSHAMJ2GMCU2ZSHN5QF4TMZYPIS')
    assets = {}
    for balance in rq.json()['balances']:
        if balance['asset_type'] == "native":
            assets['XLM'] = float(balance['balance'])
        else:
            assets[balance['asset_code']] = float(balance['balance'])
    mtl_sum = mtl_sum - assets['MTL']

    sponsors = requests.get('https://raw.githubusercontent.com/montelibero-org/mtl/main/json/bodreplenish.json').json()
    donates = requests.get("https://raw.githubusercontent.com/montelibero-org/mtl/main/json/donation.json").json()

    div_accounts = []
    if test_sum > 0:
        div_sum = test_sum
    else:
        # get balance
        rq = requests.get(f'https://horizon.stellar.org/accounts/{public_div}').json()
        div_sum = float(rq["balances"][0]['balance'])
    sponsor_sum = 0.0

    # print(json.dumps(response, indent=4))
    accounts = stellar_get_mtl_holders()
    for account in accounts:
        # print(json.dumps(account,indent=4))
        # print('***')
        balances = account["balances"]
        balance_mtl = 0
        balance_rect = 0
        div = 0
        sdiv = 0
        eur = 0
        # check all balanse
        for balance in balances:
            if balance["asset_type"][0:15] == "credit_alphanum":
                if balance["asset_code"] == "MTL":
                    balance_mtl = round(float(balance["balance"]), 7)
                if balance["asset_code"] == "MTLRECT":
                    balance_rect = round(float(balance["balance"]), 7)
                if balance["asset_code"] == "EURMTL":
                    eur = 1
        div = round(div_sum / mtl_sum * (balance_mtl + balance_rect), 7)
        # print(f'{div_sum=},{mtl_sum},{balance_mtl},{balance_rect}')
        # check sponsor
        if sponsors.get(account["account_id"]) != None:
            calc = round(div * float(sponsors.get(account["account_id"])) / 100, 7)
            sponsor_sum += calc
            sdiv = div - calc
            # print(f'calc {calc} sponsor_sum {sponsor_sum} sdiv {sdiv}')
        else:
            sdiv = div

        if (eur > 0) and (div > 0.0001) and (account["account_id"] != public_fond) \
                and (account["account_id"] != public_pawnshop):
            div_accounts.append([account["account_id"], balance_mtl + balance_rect, div, sdiv, div_list_id])

    # calc donate # ['GCPOWDQQDVSAQGJXZW3EWPPJ5JCF4KTTHBYNB4U54AKQVDLZXLLYMXY7', 56428.7, 120.9, 96.7, 26]
    donate_list = []
    for mtl_account in div_accounts:
        if mtl_account[0] in donates:
            for recipient in donates[mtl_account[0]]["recipients"]:
                calc_sum = round(float(recipient['percent']) * float(mtl_account[2]) / 100, 7)
                # print(f'{calc_sum=}')
                if mtl_account[3] >= calc_sum:
                    found = list(filter(lambda x: x[0] == recipient["recipient"], donate_list))
                    if len(found) > 0:
                        for donate in donate_list:
                            if donate[0] == recipient["recipient"]:
                                donate[3] += calc_sum
                                break
                    else:
                        donate_list.append([recipient["recipient"], 0, 0, calc_sum, donate_list_id])
                    mtl_account[3] = mtl_account[3] - calc_sum

    div_accounts.sort(key=get_key_1, reverse=True)
    donate_list.append([public_bod_eur, 0, 0, sponsor_sum, donate_list_id])
    div_accounts.extend(donate_list)
    fb.manyinsert("insert into T_PAYMENTS (USER_KEY, MTL_SUM, USER_CALC, USER_DIV, ID_DIV_LIST) values (?,?,?,?,?)",
                  div_accounts)

    return div_accounts
    # print(*mtl_accounts, sep='\n')


def cmd_gen_xdr(list_id):
    memo = fb.execsql(f'select dl.memo from t_div_list dl where dl.id = {list_id}')[0][0]
    pay_type = fb.execsql(f'select dl.pay_type from t_div_list dl where dl.id = {list_id}')[0][0]
    records = fb.execsql(
        f"select first 30 ID, USER_KEY, USER_DIV from T_PAYMENTS where WAS_PACKED = 0 and ID_DIV_LIST = {list_id}")

    # print(memo)
    # print(*rq)
    server = Server(horizon_url="https://horizon.stellar.org")
    if pay_type == 0:
        div_account = server.load_account(public_div)

    if pay_type == 1:
        div_account = server.load_account(public_bod_eur)

    transaction = TransactionBuilder(source_account=div_account, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                     base_fee=100)

    for record in records:
        if round(record[2], 7) > 0:
            transaction.append_payment_op(destination=record[1], amount=str(round(record[2], 7)), asset=eurmtl_asset)
        fb.execsql('update T_PAYMENTS set WAS_PACKED = 1 where ID = ?', [record[0]])

    transaction.add_text_memo(memo)
    transaction = transaction.build()
    xdr = transaction.to_xdr()
    # print(f"xdr: {xdr}")

    fb.execsql("insert into T_TRANSACTION (ID_DIV_LIST, XDR_ID, XDR) values (?,?,?)", [list_id, 0, xdr])
    need = fb.execsql('select count(*) from T_PAYMENTS where WAS_PACKED = 0 and id_div_list=?', [list_id])[0][0]
    # print(f'need {need} more')
    return need


def cmd_send(list_id):
    records = fb.execsql(f"select first 3 t.id, t.xdr from t_transaction t where t.was_send = 0 and t.id_div_list = ?",
                         [list_id])
    paytype = fb.execsql(f'select dl.pay_type from t_div_list dl where dl.id = {list_id}')[0][0]

    for record in records:
        transaction = TransactionEnvelope.from_xdr(record[1], network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
        server = Server(horizon_url="https://horizon.stellar.org")
        div_account = server.load_account(public_div) if paytype == 0 else server.load_account(public_bod_eur)
        sequence = div_account.sequence + 1
        transaction.transaction.sequence = sequence
        n = transaction.sign(private_div) if paytype == 0 else transaction.sign(private_bod_eur)
        transaction_resp = server.submit_transaction(transaction)
        fb.execsql('update t_transaction set was_send = 1, xdr_id = ? where id = ?', [sequence, record[0]])

    need = fb.execsql('select count(*) from t_transaction where was_send = 0 and id_div_list = ?', [list_id])[0][0]
    # print(f'need {need} more')
    return need


def cmd_calc_bods(list_id, test_sum=0):
    bod_list = get_bod_list()
    good = list(filter(lambda x: x[1], bod_list))

    balances = {}
    rq = requests.get(f'https://horizon.stellar.org/accounts/{public_bod_eur}').json()
    # print(json.dumps(rq, indent=4))
    for balance in rq["balances"]:
        if balance["asset_type"] == 'credit_alphanum12':
            balances[balance["asset_code"]] = balance["balance"]

    mtl_accounts = []
    if test_sum > 0:
        div_sum = test_sum
    else:
        div_sum = float(balances["EURMTL"])

    for account in good:
        bls = 0
        div = 0
        sdiv = div_sum
        eur = 1
        sdiv = int(div_sum / len(good) * 100) / 100

        mtl_accounts.append([account[0], bls, div, sdiv, list_id])

    mtl_accounts.sort(key=get_key_1, reverse=True)
    fb.manyinsert("insert into T_PAYMENTS (USER_KEY, MTL_SUM, USER_CALC, USER_DIV, ID_DIV_LIST) values (?,?,?,?,?)",
                  mtl_accounts)

    return mtl_accounts


def cmd_save_bot_value(param_id: BotValueTypes, key_id, value):
    # print(f"update or insert into BOT_TABLE (MYPARAM, MYKEY, MYVALUE) values ({param_id}, {key_id}, '{value}') matching (MYPARAM, MYKEY)")
    fb.execsql(
        f"update or insert into BOT_TABLE (MYPARAM, MYKEY, MYVALUE) values ({param_id.value}, {key_id}, '{value}') matching (MYPARAM, MYKEY)")


def cmd_load_bot_value(param_id: BotValueTypes, key_id: int, default_value: any = ''):
    result = fb.execsql(f"select MYVALUE from BOT_TABLE where MYPARAM = {param_id} and MYKEY = {key_id}")
    if result != []:
        return result[0][0]

    return default_value


def cmd_save_url(chat_id, msg_id, msg):
    url = re.search("(?P<url>https?://[^\s]+)", msg).group("url")
    cmd_save_bot_value(BotValueTypes.PinnedUrl, chat_id, url)
    cmd_save_bot_value(BotValueTypes.PinnedId, chat_id, msg_id)


def cleanhtml(raw_html):
    CLEANR = re.compile('<.*?>')
    cleantext = re.sub(CLEANR, '', raw_html)
    while cleantext.find("\n") > -1:
        cleantext = cleantext.replace("\n", " ")
    while cleantext.find("  ") > -1:
        cleantext = cleantext.replace("  ", " ")
    return cleantext


def cmd_alarm_url(chat_id):
    url = cmd_load_bot_value(BotValueTypes.PinnedUrl, chat_id)
    rq = requests.get(url).text
    if rq.find('<h4 class="published">') > -1:
        return 'Нечего напоминать, транзакция отправлена.'
    rq = rq[rq.find('<div class="col-10 ignorants-nicks">'):]
    rq = rq[rq.find('">') + 2:]
    # print(rq)
    # print(rq.find('</div>'))
    rq = rq[:rq.find('</div>')]
    rq = rq.replace("&#x3D;", "=")

    return cleanhtml(rq)


def cmd_get_info(my_id):
    s = requests.get(f'http://rzhunemogu.ru/RandJSON.aspx?CType={my_id}').text
    return s[12:-2]
    # 1 - Анекдот; 4 - Афоризмы; 6 - Тосты; 8 - Статусы;
    # 11 - Анекдот (+18);#12 - Рассказы (+18); 13 - Стишки (+18);  14 - Афоризмы (+18); 15 - Цитаты (+18);  16 - Тосты (+18); 18 - Статусы (+18);


def cmd_check_new_fond_transaction(ignore_operation=[]):
    result = []
    last_id = cmd_load_bot_value(BotValueTypes.LastFondTransaction, 0)
    server = Server(horizon_url="https://horizon.stellar.org")
    tr = server.transactions().for_account(public_fond).order(desc=True).call()
    # print(json.dumps(tr["_embedded"]["records"], indent=4))
    new_transactions = []
    for record in tr["_embedded"]["records"]:
        if record["paging_token"] == last_id:
            break
        new_transactions.append(record)

        # print(new_transactions)
    for transaction in new_transactions:
        if transaction["paging_token"] > last_id:
            last_id = transaction["paging_token"]
        tr = decode_xdr(transaction["envelope_xdr"], ignore_operation=ignore_operation)
        # print(tr)
        if len(tr) > 0:
            result.append(decode_xdr(transaction["envelope_xdr"]))
        # print(decode_xdr(transaction["envelope_xdr"]))
        # print('****')
        # print(transaction["paging_token"])

    cmd_save_bot_value(BotValueTypes.LastFondTransaction, 0, last_id)

    return result


def cmd_check_new_asset_transaction(asset_name: str, save_id: BotValueTypes, filter_sum: int = -1,
                                    filter_operation=[]):
    result = []
    last_id = int(cmd_load_bot_value(save_id, 0, 0))
    max_id = last_id
    rq = requests.get(
        f"https://api.stellar.expert/explorer/public/asset/{asset_name}-GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V/history/all?limit=10&order=desc&sort=id").json()
    # print(json.dumps(rq, indent=4))
    for operation in rq["_embedded"]["records"]:
        current_id = int(operation["id"])
        if current_id == last_id:
            break
        myoperation = Server(horizon_url="https://horizon.stellar.org").operations().operation(operation["id"])
        # print(myoperation.call()["_links"]["transaction"]["href"])
        transaction = requests.get(myoperation.call()["_links"]["transaction"]["href"]).json()
        if current_id > max_id:
            max_id = current_id
        xdr_result = decode_xdr(transaction["envelope_xdr"], filter_sum=filter_sum, filter_operation=filter_operation)
        if len(xdr_result) > 0:
            result.append(xdr_result)
        # print(decode_xdr(transaction["envelope_xdr"]))

    cmd_save_bot_value(save_id, 0, max_id)
    return result


def cmd_gen_div_xdr(div_sum):
    server = Server(horizon_url="https://horizon.stellar.org")

    div_account = server.load_account(public_fond)

    transaction = TransactionBuilder(source_account=div_account, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                     base_fee=100)

    transaction.append_payment_op(destination=public_div, amount=str(round(div_sum, 7)), asset=eurmtl_asset)

    transaction.add_text_memo(datetime.datetime.now().strftime('mtl div %d/%m/%Y'))
    transaction = transaction.build()
    xdr = transaction.to_xdr()
    # print(f"xdr: {xdr}")
    return xdr


def cmd_check_donate_list():
    donates = requests.get("https://raw.githubusercontent.com/montelibero-org/mtl/main/json/donation.json").json()
    # print(donates)
    donors = list(dict.fromkeys(donates))
    # donates = list(donates)
    # print(donates)
    recipients = []
    for donor in donors:
        for recipient in donates[donor]["recipients"]:
            if recipient['recipient'] not in recipients:
                recipients.append(recipient['recipient'])
    recipients.extend(donors)
    recipients = list(dict.fromkeys(recipients))
    names = []
    for recipient in recipients:
        names.append(key_name(recipient))
    return names


def cmd_gen_data_xdr(account_id: str, data: str):
    server = Server(horizon_url="https://horizon.stellar.org")
    root_account = server.load_account(account_id)
    transaction = TransactionBuilder(source_account=root_account, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                     base_fee=100)
    data = data.split(':')
    data_name = data[0]
    data_value = data[1]
    if len(data_value) == 0:
        data_value = None

    transaction.append_manage_data_op(data_name=data_name, data_value=data_value)
    transaction = transaction.build()
    xdr = transaction.to_xdr()
    return xdr


def decode_data_vlue(data_value: str):
    base64_message = data_value
    base64_bytes = base64_message.encode('ascii')
    message_bytes = base64.b64decode(base64_bytes)
    message = message_bytes.decode('ascii')
    return message


def cmd_show_guards():
    account_json = requests.get(f'https://horizon.stellar.org/accounts/GDEK5KGFA3WCG3F2MLSXFGLR4T4M6W6BMGWY6FBDSDQM6HXFMRSTEWBW').json()
    result = []
    if "data" in account_json:
        data = account_json["data"]
        for data_name in list(data):
            data_value = data[data_name]
            if data_name[:13] == 'bod_guarantor':
                result.append(f'{data_name}:{decode_data_vlue(data_value)}')
                x = cmd_show_data(decode_data_vlue(data_value))
                result.extend(x)
            result.append('***')
            # print(data_name, decode_data_vlue(data_value))
    return result


def cmd_show_data(account_id: str):
    result = []
    if account_id == 'bod':
        # get all guards
        result = cmd_show_guards()
    else:
        account_json = requests.get(f'https://horizon.stellar.org/accounts/{account_id}').json()
        if "data" in account_json:
            data = account_json["data"]
            for data_name in list(data):
                data_value = data[data_name]
                # print(data_name, decode_data_vlue(data_value))
                result.append(f'{data_name}:{decode_data_vlue(data_value)}')
    return result


if __name__ == "__main__":
    pass
    # result = cmd_check_donate_list()
    # result = cmd_check_new_fond_transaction(ignore_operation=['CreateClaimableBalance'])
    # print(*result, sep='\n')
    # print(' '.join(result))
    # print(resolve_stellar_address('attid*lobstr.co'))
    #print(resolve_stellar_address('asmin8976*lobstr.co'))
    # print(resolve_account_id('GDLTH4KKMA4R2JGKA7XKI5DLHJBUT42D5RHVK6SS6YHZZLHVLCWJAYXI', domain='eurmtl.me'))

    # s = base64.b16encode()
    # print(str(s))
    # base64_message = 'SU4gVVNFIDY1Mi40NiBNVExNaW5lcg=='
    # base64_bytes = base64_message.encode('ascii')
    # message_bytes = base64.b64decode(base64_bytes)
    # message = message_bytes.decode('ascii')
    # print(message)

    # add bod_guarantor1
    # xdr = cmd_get_data_xdr('GDEK5KGFA3WCG3F2MLSXFGLR4T4M6W6BMGWY6FBDSDQM6HXFMRSTEWBW', "bod_guarantor6:")
    # xdr = stellar_sign(xdr, private_bod_eur)
    # print(stellar_submite(xdr))

    #print(cmd_show_data('bod'))
    print(cmd_show_bod())

