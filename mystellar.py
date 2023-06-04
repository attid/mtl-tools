import asyncio
import base64
import math
from builtins import print
from contextlib import suppress

import aiohttp
import gspread
from stellar_sdk import Network, Server, TransactionBuilder, Asset, TextMemo, Keypair, \
    ServerAsync, AiohttpClient, Price
from stellar_sdk import TransactionEnvelope, FeeBumpTransactionEnvelope  # , Operation, Payment, SetOptions
import json, requests, datetime

from stellar_sdk.exceptions import NotFoundError
from stellar_sdk.sep.federation import resolve_account_id_async

from loguru import logger
from stellar_sdk.xdr import TransactionResult

import fb, re, enum
from settings import base_fee, private_sign
from datetime import datetime

# https://stellar-sdk.readthedocs.io/en/latest/
# https://github.com/StellarCN/py-stellar-base/tree/main/examples

# multi
public_issuer = "GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V"
# public_fund = "GDX23CPGMQ4LN55VGEDVFZPAJMAUEHSHAMJ2GMCU2ZSHN5QF4TMZYPIS"
public_pawnshop = "GDASYWP6F44TVNJKZKQ2UEVZOKTENCJFTWVMP6UC7JBZGY4ZNB6YAVD4"
# public_distributor = "GB7NLVMVC6NWTIFK7ULLEQDF5CBCI2TDCO3OZWWSFXQCT7OPU3P4EOSR"
# public_city = "GDUI7JVKWZV4KJVY4EJYBXMGXC2J3ZC67Z6O5QFP4ZMVQM2U5JXK2OK3"
# public_competition = "GAIKBJYL5DZFHBL3R4HPFIA2U3ZEBTJ72RZLP444ACV24YZ2C73P6COM"
public_defi = "GBTOF6RLHRPG5NRIU6MQ7JGMCV7YHL5V33YYC76YYG4JUKCJTUP5DEFI"
public_btc_guards = "GATUN5FV3QF35ZMU3C63UZ63GOFRYUHXV2SHKNTKPBZGYF2DU3B7IW6Z"
public_fund_city = "GCOJHUKGHI6IATN7AIEK4PSNBPXIAIZ7KB2AWTTUCNIAYVPUB2DMCITY"
public_fund_defi = "GAEZHXMFRW2MWLWCXSBNZNUSE6SN3ODZDDOMPFH3JPMJXN4DKBPMDEFI"
public_fund_mabiz = "GAQ5ERJVI6IW5UVNPEVXUUVMXH3GCDHJ4BJAXMAAKPR5VBWWAUOMABIZ"
public_usdm = "GDHDC4GBNPMENZAOBB4NCQ25TGZPDRK6ZGWUGSI22TVFATOLRPSUUSDM"
# bot
public_bod_eur = "GDEK5KGFA3WCG3F2MLSXFGLR4T4M6W6BMGWY6FBDSDQM6HXFMRSTEWBW"
public_bod = "GARUNHJH3U5LCO573JSZU4IOBEVQL6OJAAPISN4JKBG2IYUGLLVPX5OH"
public_div = "GDNHQWZRZDZZBARNOH6VFFXMN6LBUNZTZHOKBUT7GREOWBTZI4FGS7IQ"
public_key_rate = "GDGGHSIA62WGNMN2VOIBW3X66ATOBW5J2FU7CSJZ6XVHI2ZOXZCRRATE"
public_sign = "GDCGYX7AXIN3EWIBFZ3AMMZU4IUWS4CIZ7Z7VX76WVOIJORCKDDRSIGN"
public_fire = "GD44EAUQXNUVBJACZMW6GPT2GZ7I26EDQCU5HGKUTVEQTXIDEVGUFIRE"
public_adm = "GBSCMGJCE4DLQ6TYRNUMXUZZUXGZBM4BXVZUIHBBL5CSRRW2GWEHUADM"
public_boss = "GC72CB75VWW7CLGXS76FGN3CC5K7EELDAQCPXYMZLNMOTC42U3XJBOSS"

public_exchange_eurmtl_xlm = "GDEMWIXGF3QQE7CJIOKWWMJAXAWGINJRR6DOOOSNO3C4UQGPDOA3OBOT"
public_exchange_eurmtl_btc = "GDBCVYPF2MYMZDHO7HRUG24LZ3UUGROX3WVWSNVZF7Q5B3NBZ2NYVBOT"
public_exchange_eurmtl_sats = "GAEO4HE7DJAJPOEE4KU375WEGB2IWO42KVTG3PLBTXL7TSWDSPHPZBOT"
public_exchange_eurmtl_usdc = "GBQZDXEBW5DGNOSRUPIWUTIYTO7QM65NOU5VHAAACED4HII7FVXPCBOT"

# user
public_itolstov = "GDLTH4KKMA4R2JGKA7XKI5DLHJBUT42D5RHVK6SS6YHZZLHVLCWJAYXI"
public_pending = "GB72L53HPZ2MNZQY4XEXULRD6AHYLK4CO55YTOBZUEORW2ZTSOEQ4MTL"
public_wallet = "GBSNN2SPYZB2A5RPDTO3BLX4TP5KNYI7UMUABUS3TYWWEWAAM2D7CMMW"
public_seregan = "GBVIX6CZ57SHXHGPA4AL7DACNNZX4I2LCKIAA3VQUOGTGWYQYVYSE5TU"

mtl_asset = Asset("MTL", public_issuer)
eurmtl_asset = Asset("EURMTL", public_issuer)
eurdebt_asset = Asset("EURDEBT", public_issuer)
xlm_asset = Asset("XLM", None)
satsmtl_asset = Asset("SATSMTL", public_issuer)
btcmtl_asset = Asset("BTCMTL", public_issuer)
btcdebt_asset = Asset("BTCDEBT", public_issuer)
usdc_asset = Asset("USDC", "GA5ZSEJYB37JRC5AVCIA5MOP4RHTM335X2KGX3IHOJAPP5RE34K4KZVN")
mrxpinvest_asset = Asset("MrxpInvest", 'GDAJVYFMWNIKYM42M6NG3BLNYXC3GE3WMEZJWTSYH64JLZGWVJPTGGB7')
defi_asset = Asset("MTLDefi", public_defi)
usdmm_asset = Asset("USDMM", public_usdm)

pack_count = 70  # for select first pack_count - to pack to xdr

exchange_bots = (public_exchange_eurmtl_xlm, public_exchange_eurmtl_btc,
                 public_exchange_eurmtl_usdc, public_fire)


class BotValueTypes(enum.IntEnum):
    PinnedUrl = 1
    LastFondTransaction = 2
    LastDebtTransaction = 3
    PinnedId = 4
    LastEurTransaction = 5
    LastRectTransaction = 6
    LastMTLTransaction = 7
    LastMTLandTransaction = 8
    LastDefiTransaction = 9
    LastFCMTransaction = 10
    LastLedger = 11
    LastMMWBTransaction = 10


def stellar_add_fond_trustline(userkey, asset_code):
    return stellar_add_trustline(userkey, asset_code, public_issuer)


async def stellar_add_mtl_holders_info(accounts: dict):
    async with ServerAsync(
            horizon_url="https://horizon.stellar.org", client=AiohttpClient()
    ) as server:
        source_account = await server.load_account(public_issuer)
        sg = source_account.load_ed25519_public_key_signers()

    for s in sg:
        for arr in accounts:
            if arr[0] == s.account_id:
                arr[3] = s.weight

    return accounts


async def stellar_get_mtl_holders(asset=mtl_asset, mini=False):
    client = AiohttpClient(request_timeout=3 * 60)

    async with ServerAsync(
            horizon_url="https://horizon.stellar.org", client=client
    ) as server:
        accounts = []
        accounts_call_builder = server.accounts().for_asset(asset).limit(200)

        page_records = await accounts_call_builder.call()
        while page_records["_embedded"]["records"]:
            accounts.extend(page_records["_embedded"]["records"])
            page_records = await accounts_call_builder.next()
            if mini:
                return accounts
        # print(json.dumps(response, indent=4))
        return accounts


def stellar_add_trustline(public_key, asset_code, asset_issuer):
    root_account = Server(horizon_url="https://horizon.stellar.org").load_account(public_key)
    transaction = TransactionBuilder(source_account=root_account, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                     base_fee=base_fee)
    transaction.set_timeout(60 * 60)
    transaction.append_change_trust_op(Asset(asset_code, asset_issuer))
    transaction = transaction.build()

    xdr = transaction.to_xdr()

    return xdr


def stellar_remove_orders(public_key, xdr):
    if xdr:
        transaction = TransactionBuilder.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
    else:
        root_account = Server(horizon_url="https://horizon.stellar.org").load_account(public_key)
        transaction = TransactionBuilder(source_account=root_account,
                                         network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                         base_fee=base_fee)
        transaction.set_timeout(60 * 60)

    call = Server(horizon_url="https://horizon.stellar.org").offers().for_account(public_key).limit(200).call()

    for record in call['_embedded']['records']:
        # print(record['price'], record)
        transaction.append_manage_sell_offer_op(
            selling=Asset(record['selling'].get('asset_code', 'XLM'), record['selling'].get('asset_issuer')),
            buying=Asset(record['buying'].get('asset_code', 'XLM'), record['buying'].get('asset_issuer')),
            amount='0', price=Price(record['price_r']['n'], record['price_r']['d']), offer_id=int(record['id']),
            source=public_key)

    transaction = transaction.build()
    xdr = transaction.to_xdr()

    return xdr


def stellar_stop_all_exchange():
    xdr = None
    for bot in exchange_bots:
        xdr = stellar_remove_orders(bot, xdr)
    stellar_sync_submit(stellar_sign(xdr, private_sign))


def stellar_add_drone2(public_key):
    return stellar_add_trustline(public_key, 'DRONE2DEBT', 'GACJQY4DGVRCVCPURAOH7PH2ERWCG5ATAUXKJFD4ON5ON6PWRJWCBQNN')


def stellar_add_mtlcamp(public_key):
    return stellar_add_trustline(public_key, 'MTLCAMP', 'GBK2NV2L6A6TLKJSEJX3YZH7DEEHOOLB56WIK64Y5T2SFGNCG5FABKUB')


def stellar_sign(xdr, signkey):
    transaction = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
    transaction.sign(signkey)
    return transaction.to_xdr()


def stellar_check_xdr(xdr):
    transaction = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
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
    # transaction.transaction.fee -= 100
    operation = transaction.transaction.operations.pop(num)
    return [transaction.to_xdr(), transaction.transaction.sequence, len(transaction.transaction.operations), operation]


def stellar_del_sign(xdr, num):
    transaction = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
    operation = transaction.signatures.pop(num)
    return [transaction.to_xdr(), transaction.transaction.sequence, len(transaction.transaction.operations),
            operation]


def stellar_add_xdr(xdr, xdr2):
    transaction = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
    transaction2 = TransactionEnvelope.from_xdr(xdr2, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
    for operation in transaction2.transaction.operations:
        transaction.transaction.operations.append(operation)
    transaction.transaction.fee += transaction.transaction.fee
    return [transaction.to_xdr(), transaction.transaction.sequence, len(transaction.transaction.operations)]


def address_id_to_username(key) -> str:
    with open('members_key.json', 'r', encoding='UTF-8') as fp:
        data = json.load(fp)
    if key in data:
        return data[key]
    else:
        return key[:4] + '..' + key[-4:]


def username_to_address_id(username: str) -> list:
    with open('members_key.json', 'r', encoding='UTF-8') as fp:
        data: dict = json.load(fp)
    result = []
    if username in data.values():
        for key in data:
            if data[key] == username:
                result.append(data[key])
    return result


def good_operation(operation, operation_name, filter_operation, ignore_operation):
    if operation_name in ignore_operation:
        return False
    elif type(operation).__name__ == operation_name:
        return (not filter_operation) or (operation_name in filter_operation)
    return False


def decode_xdr(xdr, filter_sum: int = -1, filter_operation=None, ignore_operation=None, filter_asset=None):
    if ignore_operation is None:
        ignore_operation = []
    if filter_operation is None:
        filter_operation = []
    result = []
    data_exist = False

    if FeeBumpTransactionEnvelope.is_fee_bump_transaction_envelope(xdr):
        fee_transaction = FeeBumpTransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
        transaction = fee_transaction.transaction.inner_transaction_envelope
    else:
        transaction = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
    result.append(f"Операции с аккаунта {address_id_to_username(transaction.transaction.source.account_id)}")
    if transaction.transaction.memo.__class__ == TextMemo:
        memo: TextMemo = transaction.transaction.memo
        result.append(f'  Memo "{memo.memo_text.decode()}"\n')
    result.append(f"  Всего {len(transaction.transaction.operations)} операций\n")

    for idx, operation in enumerate(transaction.transaction.operations):
        result.append(f"Операция {idx} - {type(operation).__name__}")
        # print('bad xdr', idx, operation)
        if operation.source:
            result.append(f"*** для аккаунта {address_id_to_username(operation.source.account_id)}")
        if good_operation(operation, "Payment", filter_operation, ignore_operation):
            if float(operation.amount) > filter_sum:
                if (filter_asset is None) or (operation.asset == filter_asset):
                    data_exist = True
                    result.append(
                        f"    Перевод {operation.amount} {operation.asset.code} на аккаунт {address_id_to_username(operation.destination.account_id)}")
            continue
        if good_operation(operation, "SetOptions", filter_operation, ignore_operation):
            data_exist = True
            if operation.signer:
                result.append(
                    f"    Изменяем подписанта {address_id_to_username(operation.signer.signer_key.encoded_signer_key)} новые голоса : {operation.signer.weight}")
            if operation.med_threshold:
                data_exist = True
                result.append(f"Установка нового требования. Нужно будет {operation.med_threshold} голосов")
            continue
        if good_operation(operation, "ChangeTrust", filter_operation, ignore_operation):
            data_exist = True
            if operation.limit == '0':
                result.append(
                    f"    Закрываем линию доверия к токену {operation.asset.code} от аккаунта {address_id_to_username(operation.asset.issuer)}")
            else:
                result.append(
                    f"    Открываем линию доверия к токену {operation.asset.code} от аккаунта {address_id_to_username(operation.asset.issuer)}")

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
        if good_operation(operation, "CreatePassiveSellOffer", filter_operation, ignore_operation):
            if float(operation.amount) > filter_sum:
                data_exist = True
                result.append(
                    f"    Пассивный офер на продажу {operation.amount} {operation.selling.code} по цене {operation.price.n / operation.price.d} {operation.buying.code}")
            continue
        if good_operation(operation, "ManageBuyOffer", filter_operation, ignore_operation):
            if float(operation.amount) > filter_sum:
                data_exist = True
                result.append(
                    f"    Офер на покупку {operation.amount} {operation.buying.code} по цене {operation.price.n / operation.price.d} {operation.selling.code}")
            continue
        if good_operation(operation, "PathPaymentStrictSend", filter_operation, ignore_operation):
            if (float(operation.dest_min) > filter_sum) and (float(operation.send_amount) > filter_sum):
                if (filter_asset is None) or (filter_asset in [operation.send_asset, operation.dest_asset]):
                    data_exist = True
                    result.append(
                        f"    Покупка {address_id_to_username(operation.destination.account_id)}, шлем {operation.send_asset.code} {operation.send_amount} в обмен на {operation.dest_asset.code} min {operation.dest_min} ")
            continue
        if good_operation(operation, "PathPaymentStrictReceive", filter_operation, ignore_operation):
            if (float(operation.send_max) > filter_sum) and (float(operation.dest_amount) > filter_sum):
                if (filter_asset is None) or (filter_asset in [operation.send_asset, operation.dest_asset]):
                    data_exist = True
                    result.append(
                        f"    Продажа {address_id_to_username(operation.destination.account_id)}, Получаем {operation.send_asset.code} max {operation.send_max} в обмен на {operation.dest_asset.code} {operation.dest_amount} ")
            continue
        if good_operation(operation, "ManageData", filter_operation, ignore_operation):
            data_exist = True
            result.append(
                f"    ManageData {operation.data_name} = {operation.data_value} ")
            continue
        if good_operation(operation, "CreateAccount", filter_operation, ignore_operation):
            data_exist = True
            result.append(
                f"    Создание аккаунта {address_id_to_username(operation.destination)} с суммой {operation.starting_balance} XLM")
            continue
        if good_operation(operation, "AccountMerge", filter_operation, ignore_operation):
            data_exist = True
            result.append(
                f"    Слияние аккаунта c {address_id_to_username(operation.destination.account_id)} ")
            continue
        if good_operation(operation, "ClaimClaimableBalance", filter_operation, ignore_operation):
            data_exist = True
            result.append(f"    ClaimClaimableBalance {address_id_to_username(operation.balance_id)}")
            continue
        if good_operation(operation, "BeginSponsoringFutureReserves", filter_operation, ignore_operation):
            data_exist = True
            result.append(f"    BeginSponsoringFutureReserves {address_id_to_username(operation.sponsored_id)}")
            continue
        if good_operation(operation, "EndSponsoringFutureReserves", filter_operation, ignore_operation):
            data_exist = True
            result.append(f"    EndSponsoringFutureReserves")
            continue
        if type(operation).__name__ in ["PathPaymentStrictSend", "ManageBuyOffer", "ManageSellOffer", "AccountMerge",
                                        "PathPaymentStrictReceive", "ClaimClaimableBalance", "CreateAccount",
                                        "CreateClaimableBalance", "ChangeTrust", "SetOptions", "Payment", "ManageData",
                                        "BeginSponsoringFutureReserves", "EndSponsoringFutureReserves",
                                        "CreatePassiveSellOffer"]:
            continue

        data_exist = True
        result.append(f"Прости хозяин, не понимаю")
        print('bad xdr', idx, operation)
    if data_exist:
        return result
    else:
        return []


def load_xdr(xdr) -> TransactionEnvelope:
    if FeeBumpTransactionEnvelope.is_fee_bump_transaction_envelope(xdr):
        fee_transaction = FeeBumpTransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
        transaction = fee_transaction.transaction.inner_transaction_envelope
    else:
        transaction = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
    return transaction


def check_url_xdr(url):
    rq = requests.get(url).text
    rq = rq[rq.find('<span class="tx-body">') + 22:]
    # print(rq)
    rq = rq[:rq.find('</span>')]
    rq = rq.replace("&#x3D;", "=")
    # print(rq)
    return decode_xdr(rq)


def get_bim_list():
    # ['GARNOMR62CRFSI2G2OQYA5SPGFFDBBY566AWZF4637MNF74UZMBNOZVD', True],
    gc = gspread.service_account('mtl-google-doc.json')
    wks = gc.open("MTL_BIM_register").worksheet("List")

    addresses = []
    data = wks.get_all_values()
    for record in data[2:]:
        if record[20] and len(record[4]) == 56 and record[10] == 'TRUE' and float(float2str(record[17])) > 0.5:
            # print(record[4], record[10])
            addresses.append(record[4])

    # check eurmtl
    result = []
    for address in addresses:
        # get balance
        balances = {}
        # print(address)
        rq = requests.get(f'https://horizon.stellar.org/accounts/{address}').json()
        # print(json.dumps(rq, indent=4))
        if rq.get("balances"):
            for balance in rq["balances"]:
                if balance["asset_type"] == 'credit_alphanum12':
                    balances[balance["asset_code"]] = balance["balance"]
            has_eurmtl = 'EURMTL' in balances
            result.append([address, has_eurmtl])
    return result


def cmd_show_bim():
    result = ''
    bod_list = get_bim_list()
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
    # result += f'\nНачать выплаты /do_bod'
    return result


def get_key_1(key):
    return key[1]


def cmd_create_list(memo, pay_type):
    return fb.execsql(f"insert into T_DIV_LIST (MEMO,pay_type) values ('{memo}',{pay_type}) returning ID")[0][0]


def get_donate_list(account: dict):
    donate_list = []
    if "data" in account:
        data = account.get("data")
        account_id = account.get("account_id")
        for data_name in list(data):
            data_value = data[data_name]
            if data_name[:10] == 'mtl_donate':
                if data_name.find('=') > 6:
                    persent: str
                    persent = data_name[data_name.find('=') + 1:]
                    if isfloat(persent):
                        donate_data_value = decode_data_value(data_value)
                        # print(account_id, persent, donate_data_value)
                        donate_list.append([account_id, donate_data_value, persent])
    return donate_list


async def cmd_calc_divs(div_list_id: int, donate_list_id: int, test_sum=0):
    server = Server(horizon_url="https://horizon.stellar.org")

    # MTL
    rq = requests.get(f'https://horizon.stellar.org/assets?asset_code=MTL&asset_issuer={public_issuer}')
    mtl_sum = float(rq.json()['_embedded']['records'][0]['amount'])
    rq = requests.get(f'https://horizon.stellar.org/assets?asset_code=MTLRECT&asset_issuer={public_issuer}')
    mtl_sum += float(rq.json()['_embedded']['records'][0]['amount'])
    # FOND
    fund_balance = await get_balances(public_issuer)
    mtl_sum = mtl_sum - fund_balance.get('MTL', 0)

    div_accounts = []
    donates = []
    if test_sum > 0:
        div_sum = test_sum
    else:
        # get balance
        div_sum = await get_balances(public_div)
        div_sum = div_sum['EURMTL']
        logger.info(f'div_sum = {div_sum}')
        await stellar_async_submit(stellar_sign(cmd_gen_data_xdr(public_div, f'LAST_DIVS:{div_sum}'), private_sign))

    sponsor_sum = 0.0

    # print(json.dumps(response, indent=4))
    accounts = await stellar_get_mtl_holders()
    for account in accounts:
        # print(json.dumps(account,indent=4))
        # print('***')
        balances = account["balances"]
        balance_mtl = 0
        balance_rect = 0
        eur = 0
        # check all balance
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
        donates.extend(get_donate_list(account))

        if (eur > 0) and (div > 0.0001) and (account["account_id"] != public_issuer) \
                and (account["account_id"] != public_pawnshop):
            div_accounts.append([account["account_id"], balance_mtl + balance_rect, div, div, div_list_id])

    # calc donate # ['GCPOWDQQDVSAQGJXZW3EWPPJ5JCF4KTTHBYNB4U54AKQVDLZXLLYMXY7', 56428.7, 120.9, 96.7, 26]
    donate_list = []
    for mtl_account in div_accounts:
        found_list = list(filter(lambda x: x[0] == mtl_account[0], donates))
        for donate_rules in found_list:  # ['GACBSNMGR32HMG2AXTE4CSJHTEZ7LUDBU3SNPCG4TBBE4XKVBQZ55I5M', 'GACNFOLV3ATA6N6AHMO3IBZCYMHUMFCT6O452DW3RTU254TZJ5CP3V3Q', '5']
            calc_sum = round(float(donate_rules[2]) * float(mtl_account[2]) / 100, 7)
            # print(f'{calc_sum=}')
            if mtl_account[3] >= calc_sum:
                found_calc = list(filter(lambda x: x[0] == donate_rules[1], donate_list))
                if found_calc:
                    for donate in donate_list:
                        if donate[0] == donate_rules[1]:
                            donate[3] += calc_sum
                            break
                else:
                    donate_list.append([donate_rules[1], 0, 0, calc_sum, donate_list_id])
                mtl_account[3] = mtl_account[3] - calc_sum

    div_accounts.sort(key=get_key_1, reverse=True)
    div_accounts.extend(donate_list)
    fb.many_insert("insert into T_PAYMENTS (USER_KEY, MTL_SUM, USER_CALC, USER_DIV, ID_DIV_LIST) values (?,?,?,?,?)",
                   div_accounts)

    return div_accounts
    # print(*mtl_accounts, sep='\n')


async def cmd_calc_sats_divs(div_list_id: int, test_sum=0):
    # MTL
    rq = requests.get(f'https://horizon.stellar.org/assets?asset_code=MTL&asset_issuer={public_issuer}')
    mtl_sum = float(rq.json()['_embedded']['records'][0]['amount'])
    rq = requests.get(f'https://horizon.stellar.org/assets?asset_code=MTLRECT&asset_issuer={public_issuer}')
    mtl_sum += float(rq.json()['_embedded']['records'][0]['amount'])
    # FOND
    fund_balance = await get_balances(public_issuer)
    mtl_sum = mtl_sum - fund_balance.get('MTL', 0)

    div_accounts = []
    donates = []
    if test_sum > 0:
        div_sum = test_sum
    else:
        # get balance
        div_sum = await get_balances(public_div)
        div_sum = float(div_sum['SATSMTL'])
        logger.info(f"div_sum = {div_sum}")

    sponsor_sum = 0.0

    # print(json.dumps(response, indent=4))
    accounts = await stellar_get_mtl_holders()
    for account in accounts:
        # print(json.dumps(account,indent=4))
        # print('***')
        balances = account["balances"]
        balance_mtl = 0
        balance_rect = 0
        sats_open = 0
        # check all balance
        for balance in balances:
            if balance["asset_type"][0:15] == "credit_alphanum":
                if balance["asset_code"] == "MTL":
                    balance_mtl = round(float(balance["balance"]), 7)
                if balance["asset_code"] == "MTLRECT":
                    balance_rect = round(float(balance["balance"]), 7)
                if balance["asset_code"] == "SATSMTL":
                    sats_open = 1
        div = round(div_sum / mtl_sum * (balance_mtl + balance_rect), 7)
        # print(f'{div_sum=},{mtl_sum},{balance_mtl},{balance_rect}')
        # check sponsor
        donates.extend(get_donate_list(account))

        if (sats_open > 0) and (div > 0.0001) and (account["account_id"] != public_issuer) \
                and (account["account_id"] != public_pawnshop):
            div_accounts.append([account["account_id"], balance_mtl + balance_rect, div, div, div_list_id])

    div_accounts.sort(key=get_key_1, reverse=True)
    fb.many_insert("insert into T_PAYMENTS (USER_KEY, MTL_SUM, USER_CALC, USER_DIV, ID_DIV_LIST) values (?,?,?,?,?)",
                   div_accounts)

    return div_accounts
    # print(*mtl_accounts, sep='\n')


def cmd_gen_xdr(list_id):
    memo = fb.execsql(f'select dl.memo from t_div_list dl where dl.id = {list_id}')[0][0]
    pay_type = fb.execsql(f'select dl.pay_type from t_div_list dl where dl.id = {list_id}')[0][0]
    records = fb.execsql(
        f"select first {pack_count} ID, USER_KEY, USER_DIV from T_PAYMENTS where WAS_PACKED = 0 and ID_DIV_LIST = {list_id}")
    # print(memo)
    # print(*rq)
    server = Server(horizon_url="https://horizon.stellar.org")
    if pay_type == 0:
        div_account = server.load_account(public_div)
        asset = eurmtl_asset

    if pay_type == 1:
        div_account = server.load_account(public_bod_eur)
        asset = eurmtl_asset

    if pay_type == 4:
        div_account = server.load_account(public_div)
        asset = satsmtl_asset

    transaction = TransactionBuilder(source_account=div_account, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                     base_fee=base_fee)
    transaction.set_timeout(60 * 60)

    for record in records:
        if round(record[2], 7) > 0:
            transaction.append_payment_op(destination=record[1], amount=str(round(record[2], 7)), asset=asset)
        fb.execsql('update T_PAYMENTS set WAS_PACKED = 1 where ID = ?', [record[0]])

    transaction.add_text_memo(memo)
    transaction = transaction.build()
    xdr = transaction.to_xdr()
    # print(f"xdr: {xdr}")

    fb.execsql("insert into T_TRANSACTION (ID_DIV_LIST, XDR_ID, XDR) values (?,?,?)", [list_id, 0, xdr])
    need = fb.execsql('select count(*) from T_PAYMENTS where WAS_PACKED = 0 and id_div_list=?', [list_id])[0][0]
    # print(f'need {need} more')
    return need


async def cmd_gen_key_rate_xdr(list_id):
    memo = fb.execsql(f'select dl.memo from t_div_list dl where dl.id = {list_id}')[0][0]
    pay_type = fb.execsql(f'select dl.pay_type from t_div_list dl where dl.id = {list_id}')[0][0]
    records = fb.execsql(f"select first {pack_count} e.asset, e.user_key, sum(e.amount) amount from t_keyrate e "
                         f"where e.was_packed = 0 group by e.user_key, e.asset order by e.asset")

    accounts_list = []
    accounts = await stellar_get_mtl_holders(eurmtl_asset)
    for account in accounts:
        accounts_list.append(f"{account['account_id']}-EURMTL")
    accounts = await stellar_get_mtl_holders(eurdebt_asset)
    for account in accounts:
        accounts_list.append(f"{account['account_id']}-EURDEBT")

    server = Server(horizon_url="https://horizon.stellar.org")
    # if pay_type != 3: exit
    div_account = server.load_account(public_key_rate)

    transaction = TransactionBuilder(source_account=div_account, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                     base_fee=base_fee)
    transaction.set_timeout(60 * 60)

    for record in records:
        if f"{record[1]}-{record[0]}" in accounts_list:
            if round(record[2], 7) > 0:
                transaction.append_payment_op(destination=record[1], amount=str(round(record[2], 7)),
                                              asset=Asset(record[0], public_issuer))
                fb.execsql('update t_keyrate set was_packed = ? where asset = ? and user_key = ? and was_packed = 0',
                           [list_id, record[0], record[1]])
        else:
            fb.execsql('update t_keyrate set was_packed = ? where asset = ? and user_key = ? and was_packed = 0',
                       [-1, record[0], record[1]])

    transaction.add_text_memo(memo)
    transaction = transaction.build()
    xdr = transaction.to_xdr()
    # print(f"xdr: {xdr}")

    fb.execsql("insert into T_TRANSACTION (ID_DIV_LIST, XDR_ID, XDR) values (?,?,?)", [list_id, 0, xdr])
    need = fb.execsql('select count(*) from t_keyrate where was_packed = 0 and amount > 0.0001', [list_id])[0][0]
    # print(f'need {need} more')
    return need


async def cmd_send_by_list_id(list_id):
    records = fb.execsql(f"select first 3 t.id, t.xdr from t_transaction t where t.was_send = 0 and t.id_div_list = ?",
                         [list_id])

    for record in records:
        transaction = TransactionEnvelope.from_xdr(record[1], network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
        server = Server(horizon_url="https://horizon.stellar.org")
        div_account = server.load_account(transaction.transaction.source.account_id)
        sequence = div_account.sequence + 1
        transaction.transaction.sequence = sequence
        transaction.sign(private_sign)
        transaction_resp = await stellar_async_submit(transaction.to_xdr())
        logger.info(transaction_resp)
        fb.execsql('update t_transaction set was_send = 1, xdr_id = ? where id = ?', [sequence, record[0]])

    need = fb.execsql('select count(*) from t_transaction where was_send = 0 and id_div_list = ?', [list_id])[0][0]
    # print(f'need {need} more')
    return need


def cmd_calc_bim_pays(list_id, test_sum=0):
    bod_list = get_bim_list()
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
    fb.many_insert("insert into T_PAYMENTS (USER_KEY, MTL_SUM, USER_CALC, USER_DIV, ID_DIV_LIST) values (?,?,?,?,?)",
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


def cmd_save_bot_user(user_id: int, user_name: str):
    fb.execsql(f"update or insert into bot_users (user_id, user_name) values (?, ?) matching (user_id)",
               (user_id, user_name)
               )


def cmd_load_user_id(user_name: str) -> int:
    result = fb.execsql1('select user_id from bot_users where user_name = ?', (user_name,), 0)
    return result


def cmd_save_url(chat_id, msg_id, msg):
    url = extract_url(msg)
    cmd_save_bot_value(BotValueTypes.PinnedUrl, chat_id, url)
    cmd_save_bot_value(BotValueTypes.PinnedId, chat_id, msg_id)


def extract_url(msg, surl='eurmtl.me'):
    if surl:
        url = re.search("(?P<url>https?://" + surl + "[^\s]+)", msg).group("url")
    else:
        url = re.search("(?P<url>https?://[^\s]+)", msg).group("url")
    return url


def cleanhtml(raw_html):
    CLEAN = re.compile('<.*?>')
    cleantext = re.sub(CLEAN, '', raw_html)
    while cleantext.find("\n") > -1:
        cleantext = cleantext.replace("\n", " ")
    while cleantext.find("  ") > -1:
        cleantext = cleantext.replace("  ", " ")
    return cleantext


def cmd_alarm_pin_url(chat_id):
    url = cmd_load_bot_value(BotValueTypes.PinnedUrl, chat_id)
    return cmd_alarm_url_(url)


def cmd_alarm_url_(url):
    rq = requests.get(url).text
    if rq.find('<h4 class="published">') > -1:
        return 'Нечего напоминать, транзакция отправлена.'
    rq = rq[rq.find('<div class="col-10 ignorants-nicks">'):]
    rq = rq[rq.find('">') + 2:]
    rq = rq[:rq.find('</div>')]
    rq = rq.replace("&#x3D;", "=")
    return cleanhtml(rq)


def cmd_get_info(my_id):
    s = requests.get(f'http://rzhunemogu.ru/RandJSON.aspx?CType={my_id}').text
    return s[12:-2]
    # 1 - Анекдот; 4 - Афоризмы; 6 - Тосты; 8 - Статусы;
    # 11 - Анекдот (+18);#12 - Рассказы (+18); 13 - Стишки (+18);  14 - Афоризмы (+18); 15 - Цитаты (+18);  16 - Тосты (+18); 18 - Статусы (+18);


def cmd_check_new_transaction(ignore_operation=[], value_id=None, stellar_address=public_issuer):
    result = []
    last_id = cmd_load_bot_value(value_id, 0)
    server = Server(horizon_url="https://horizon.stellar.org")
    tr = server.transactions().for_account(stellar_address).order(desc=True).call()
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
            link = f'https://stellar.expert/explorer/public/tx/{transaction["paging_token"]}'
            tr = decode_xdr(transaction["envelope_xdr"])
            tr.insert(0, f'(<a href="{link}">expert link</a>)')
            result.append(tr)
        # print(decode_xdr(transaction["envelope_xdr"]))
        # print('****')
        # print(transaction["paging_token"])

    cmd_save_bot_value(value_id, 0, last_id)

    return result


def cmd_check_new_asset_transaction_old(asset_name: str, save_id: BotValueTypes, filter_sum: int = -1,
                                        filter_operation=None, issuer=public_issuer, filter_asset=None):
    if filter_operation is None:
        filter_operation = []
    result = []
    transactions = {}
    last_id = int(cmd_load_bot_value(save_id, 0, '0'))
    max_id = last_id
    rq = requests.get(
        f"https://api.stellar.expert/explorer/public/asset/{asset_name}-{issuer}/history/all?limit=10&order=desc&sort=id").json()
    # print(json.dumps(rq, indent=4))
    for operation in rq["_embedded"]["records"]:
        current_id = int(operation["id"])
        if current_id == last_id:
            break
        my_operation = Server(horizon_url="https://horizon.stellar.org").operations().operation(operation["id"]).call()
        # print(my_operation["_links"]["transaction"]["href"])
        transaction = requests.get(my_operation["_links"]["transaction"]["href"]).json()
        transactions[transaction["paging_token"]] = {
            'link': f'https://stellar.expert/explorer/public/tx/{transaction["paging_token"]}',
            'envelope_xdr': transaction["envelope_xdr"]}
        if current_id > max_id:
            max_id = current_id

    for paging_token in transactions:
        xdr_result = decode_xdr(transactions[paging_token]["envelope_xdr"], filter_sum=filter_sum,
                                filter_operation=filter_operation,
                                filter_asset=filter_asset)
        if len(xdr_result) > 0:
            link = transactions[paging_token]["link"]
            xdr_result.insert(0, f'(<a href="{link}">expert link</a>)')
            result.append(xdr_result)
        # print(decode_xdr(transaction["envelope_xdr"]))

    cmd_save_bot_value(save_id, 0, max_id)
    return result


def decode_db_effect(row):
    # id, dt, operation, amount1, code1, amount2, code2, from_account, for_account,
    result = f'<a href="https://stellar.expert/explorer/public/op/{row[0].split("-")[0]}">' \
             f'Операция</a> с аккаунта {address_id_to_username(row[8])} \n'
    if row[2] == 'trade':
        result += f'  {row[2]}  {float2str(row[3])} {row[4]} for {float2str(row[5])} {row[6]} \n'
    else:
        result += f'  {row[2]} for {float2str(row[3])} {row[4]} \n'
        # if row[2] == 'account_credited':  if row[2] == 'account_debited':
    return result


def cmd_check_new_asset_transaction(asset_name: str, save_id: BotValueTypes, filter_sum: int = -1,
                                    filter_operation=None, issuer=public_issuer, filter_asset=None):
    if filter_operation is None:
        filter_operation = []
    result = []

    last_id = cmd_load_bot_value(save_id, 0, '0')
    max_id = last_id

    data = fb.get_new_effects_for_token(asset_name, issuer, last_id, filter_sum)
    for row in data:
        result.append(decode_db_effect(row))
        max_id = row[0]

    if max_id > last_id:
        cmd_save_bot_value(save_id, 0, max_id)

    return result


def cmd_gen_div_xdr(div_sum):
    server = Server(horizon_url="https://horizon.stellar.org")

    div_account = server.load_account(public_issuer)

    transaction = TransactionBuilder(source_account=div_account, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                     base_fee=base_fee)
    transaction.set_timeout(60 * 60)

    transaction.append_payment_op(destination=public_div, amount=str(round(div_sum, 7)), asset=eurmtl_asset)

    transaction.add_text_memo(datetime.datetime.now().strftime('mtl div %d/%m/%Y'))
    transaction = transaction.build()
    xdr = transaction.to_xdr()
    # print(f"xdr: {xdr}")
    return xdr


def cmd_gen_data_xdr(account_id: str, data: str, xdr=None):
    if xdr:
        transaction = TransactionBuilder.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
    else:
        server = Server(horizon_url="https://horizon.stellar.org")
        root_account = server.load_account(account_id)
        transaction = TransactionBuilder(source_account=root_account,
                                         network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                         base_fee=base_fee)
        transaction.set_timeout(60 * 60)
    data = data.split(':')
    data_name = data[0]
    data_value = data[1]
    if len(data_value) == 0:
        data_value = None

    transaction.append_manage_data_op(data_name=data_name, data_value=data_value)
    transaction = transaction.build()
    xdr = transaction.to_xdr()
    return xdr


def decode_data_value(data_value: str):
    base64_message = data_value
    base64_bytes = base64_message.encode('ascii')
    message_bytes = base64.b64decode(base64_bytes)
    message = message_bytes.decode('ascii')
    return message


async def cmd_show_guards_list():
    account_json = await stellar_get_account(public_bod_eur)

    result_data = []
    if "data" in account_json:
        data = account_json["data"]
        for data_name in list(data):
            data_value = data[data_name]
            if data_name[:13] == 'bod_guarantor':
                guard = decode_data_value(data_value)
                result_data.append([guard, '', ''])
                account_json2 = await stellar_get_account(guard)
                if "data" in account_json2:
                    data2 = account_json2["data"]
                    for data_name_2 in list(data2):
                        data_value = data2[data_name_2]
                        if data_name_2.find('bod') == 0:
                            result_data.append(['', data_name_2, decode_data_value(data_value)])
            result_data.append(['*', '*', '*'])
    return result_data


def cmd_show_guards():
    account_json = requests.get(
        f'https://horizon.stellar.org/accounts/GDEK5KGFA3WCG3F2MLSXFGLR4T4M6W6BMGWY6FBDSDQM6HXFMRSTEWBW').json()
    result_data = []
    if "data" in account_json:
        data = account_json["data"]
        for data_name in list(data):
            data_value = data[data_name]
            if data_name[:13] == 'bod_guarantor':
                result_data.append(f'{data_name} => {decode_data_value(data_value)}')
                x = cmd_show_data(decode_data_value(data_value), 'bod')
                result_data.extend(x)
            result_data.append('***')
            # print(data_name, decode_data_vlue(data_value))
    return result_data


async def cmd_show_donates(return_json=False, return_table=False):
    accounts = await stellar_get_mtl_holders()
    account_list = []

    for account in accounts:
        if account['data']:
            account_list.append([account["account_id"], account['data']])

    # https://github.com/montelibero-org/mtl/blob/main/json/donation.json
    # "GBOZAJYX43ANOM66SZZFBDG7VZ2EGEOTIK5FGWRO54GLIZAKHTLSXXWM":
    #   [ {  "recipient": "GCPOWDQQDVSAQGJXZW3EWPPJ5JCF4KTTHBYNB4U54AKQVDLZXLLYMXY7",
    #        "percent": "100" } ]

    # find donate
    donate_json = {}
    donate_data = []
    donate_table = []
    for account in account_list:
        if account[1]:
            data = account[1]
            recipients = []
            for data_name in list(data):
                data_value = data[data_name]
                if data_name[:10] == 'mtl_donate':
                    recipient = {"recipient": decode_data_value(data_value),
                                 "percent": data_name[data_name.find('=') + 1:]}
                    recipients.append(recipient)
            if recipients:
                donate_json[account[0]] = recipients
                donate_data.append(f"{account[0]} ==>")
                donate_table.append([account[0], '', ''])
                for recipient in recipients:
                    donate_data.append(f"          {recipient['percent']} ==> {recipient['recipient']}")
                    donate_table.append(['', recipient['percent'], recipient['recipient']])
                donate_data.append(f"******")

    if return_json:
        return donate_json
    if return_table:
        return donate_table
    return donate_data


def cmd_getblacklist():
    return requests.get('https://raw.githubusercontent.com/montelibero-org/mtl/main/json/blacklist.json').json()


async def cmd_gen_mtl_vote_list(return_delegate_list: bool = False, mini=False):
    account_list = []
    divider = 1000

    accounts = await stellar_get_mtl_holders(mini=mini)

    # mtl
    for account in accounts:
        balances = account["balances"]
        balance_mtl = 0
        balance_rect = 0
        for balance in balances:
            if balance["asset_type"][0:15] == "credit_alphanum":
                if balance["asset_code"] == "MTL" and balance["asset_issuer"] == public_issuer:
                    balance_mtl = balance["balance"]
                    balance_mtl = int(balance_mtl[0:balance_mtl.find('.')])
                if balance["asset_code"] == "MTLRECT" and balance["asset_issuer"] == public_issuer:
                    balance_rect = balance["balance"]
                    balance_rect = int(balance_rect[0:balance_rect.find('.')])
        lg = round(math.log2((balance_mtl + balance_rect + 0.001) / divider)) + 1
        if account["account_id"] != public_issuer:
            account_list.append([account["account_id"], balance_mtl + balance_rect, lg, 0, account['data']])
    # 2
    big_list = []
    for arr in account_list:
        if int(arr[1]) >= 1:
            big_list.append(arr)
    big_list.sort(key=lambda k: k[1], reverse=True)

    # find delegate
    delegate_list = {}
    for account in big_list:
        if account[4]:
            data = account[4]
            for data_name in list(data):
                data_value = data[data_name]
                if data_name in ('delegate', 'mtl_delegate'):
                    delegate_list[account[0]] = decode_data_value(data_value)

    if return_delegate_list:
        return delegate_list

    # delete blacklist user
    bl = cmd_getblacklist()
    for arr in big_list:
        if bl.get(arr[0]):
            arr[1] = 0
            arr[2] = 0
            # vote_list.remove(arr)
            # print(arr)

    for arr_from in big_list:
        if delegate_list.get(arr_from[0]):
            for arr_for in big_list:
                if arr_for[0] == delegate_list[arr_from[0]]:
                    arr_for[1] += arr_from[1]
                    arr_from[1] = 0
                    delegate_list.pop(arr_from[0])
                    arr_for[2] = round(math.log2((arr_for[1] + 0.001) / divider)) + 1
                    arr_from[2] = 0
                    break
            # vote_list.remove(arr)
            # print(arr,source)

    big_list.sort(key=lambda k: k[1], reverse=True)
    big_list = big_list[:20]
    total_sum = 0
    for account in big_list:
        total_sum += account[1]
    # divider = total_sum#ceil() #big_list[19][1]
    total_vote = 0
    for account in big_list:
        account[2] = math.ceil(account[1] * 100 / total_sum)
        total_vote += account[2]

    big_vote = big_list[0][2]

    for account in big_list:
        account[2] = round(account[2] ** (
                1 - (1.45 - (big_vote - total_vote / 3) / total_vote) * (big_vote - total_vote / 3) / total_vote))
    # =C8^(1-(1,45-($C$2-$C$22/3)/$C$22)*($C$2-$C$22/3)/$C$22)

    return big_list


async def cmd_gen_usdm_vote_list(return_delegate_list: bool = False, mini=False):
    account_list = []
    accounts = await stellar_get_mtl_holders(mini=mini, asset=usdmm_asset)

    # mtl
    for account in accounts:
        balances = account["balances"]
        balance_usdmm = 0
        for balance in balances:
            if balance["asset_type"][0:15] == "credit_alphanum":
                if balance["asset_code"] == "USDMM" and balance["asset_issuer"] == public_usdm:
                    balance_usdmm = float(balance["balance"])
        # lg = round(math.log2((balance_mtl + balance_rect + 0.001) / divider))
        if account["account_id"] != 'GAQ5ERJVI6IW5UVNPEVXUUVMXH3GCDHJ4BJAXMAAKPR5VBWWAUOMABIZ':
            vote = round(balance_usdmm)
            if account["account_id"] in ('GBYH3M3REQM3WQOJY26FYORN23EXY22FWBHVZ74TT5GYOF22IIA7YSOX',
                                         'GBVIX6CZ57SHXHGPA4AL7DACNNZX4I2LCKIAA3VQUOGTGWYQYVYSE5TU',
                                         'GDLTH4KKMA4R2JGKA7XKI5DLHJBUT42D5RHVK6SS6YHZZLHVLCWJAYXI'):
                vote += 17
            account_list.append([account["account_id"], balance_usdmm, vote, 0, account['data']])
    # 2
    big_list = []
    for arr in account_list:
        if float(arr[1]) > 0:
            big_list.append(arr)
    big_list.sort(key=lambda k: k[1], reverse=True)

    # find delegate
    delegate_list = {}
    for account in big_list:
        if account[4]:
            data = account[4]
            for data_name in list(data):
                data_value = data[data_name]
                if data_name in ('delegate', 'mtl_delegate'):
                    delegate_list[account[0]] = decode_data_value(data_value)

    if return_delegate_list:
        return delegate_list

    # delete blacklist user
    bl = cmd_getblacklist()
    for arr in big_list:
        if bl.get(arr[0]):
            arr[1] = 0
            arr[2] = 0
            # vote_list.remove(arr)
            # print(arr)

    for arr_from in big_list:
        if delegate_list.get(arr_from[0]):
            for arr_for in big_list:
                if arr_for[0] == delegate_list[arr_from[0]]:
                    arr_for[1] += arr_from[1]
                    arr_from[1] = 0
                    delegate_list.pop(arr_from[0])
                    arr_for[2] = round(float(arr_for[1]))
                    arr_from[2] = 0
                    break
            # vote_list.remove(arr)
            # print(arr,source)

    big_list.sort(key=lambda k: k[1], reverse=True)
    big_list = big_list[:20]
    total_sum = 0
    for account in big_list:
        total_sum += account[1]
    # divider = total_sum#ceil() #big_list[19][1]
    total_vote = 0
    for account in big_list:
        total_vote += account[2]

    return big_list


async def cmd_show_data(account_id: str, filter_by: str = None, only_data: bool = False):
    result_data = []
    if account_id == 'delegate':
        # get all delegate
        vote_list = await cmd_gen_mtl_vote_list(return_delegate_list=True)
        for k, v in vote_list.items():
            result_data.append(f'{k} => {v}')
    elif account_id == 'bdm':
        # get all guards
        result_data = cmd_show_guards()
    elif account_id == 'donate':
        # get all guards
        result_data = cmd_show_donates()
    else:
        account_json = requests.get(f'https://horizon.stellar.org/accounts/{account_id}').json()
        if "data" in account_json:
            data = account_json["data"]
            for data_name in list(data):
                data_value = data[data_name]
                # print(data_name, decode_data_vlue(data_value))
                if not filter_by or data_name.find(filter_by) == 0:
                    if only_data:
                        result_data.append(decode_data_value(data_value))
                    else:
                        result_data.append(f'{data_name} => {decode_data_value(data_value)}')
    return result_data


async def resolve_account(account_id: str):
    result = ''
    client = AiohttpClient()
    try:
        result = await resolve_account_id_async(account_id, domain='eurmtl.me', client=client)
        result = result.stellar_address
    except Exception as e:
        pass
    if result == '':
        try:
            result = await resolve_account_id_async(account_id, domain='lobstr.co', client=client)
            result = result.stellar_address
        except Exception as e:
            pass
    if result == '':
        try:
            result = await resolve_account_id_async(account_id, domain='keybase.io', client=client)
            result = result.stellar_address
        except Exception as e:
            pass
    if result == '':
        result = account_id[:4] + '..' + account_id[-4:]
    await client.close()
    return result


def isfloat(value):
    try:
        float(value)
        return True
    except ValueError:
        return False


def gen_new(last_name):
    new_account = Keypair.random()
    i = 0
    while new_account.public_key[-len(last_name):] != last_name:
        new_account = Keypair.random()
        # print(i, new_account.public_key, new_account.secret)
        i += 1
        print(i, new_account.public_key, new_account.secret)
    return [i, new_account.public_key, new_account.secret]


async def get_safe_balance(chat_id):
    total_cash = 0
    total_eurmtl = 0
    result = ''

    treasure_list = [
        ['GAJIOTDOP25ZMXB5B7COKU3FGY3QQNA5PPOKD5G7L2XLGYJ3EDKB2SSS', 'Игоря'],
        ['GBBCLIYOIBVZSMCPDAOP67RJZBDHEDQ5VOVYY2VDXS2B6BLUNFS5242O', 'Соза'],
        ['GC624CN4PZJX3YPMGRAWN4B75DJNT3AWIOLYY5IW3TWLPUAG6ER6IFE6', 'Генриха'],
        ['GAATY6RRLYL4CB6SCSUSSEELPTOZONJZ5WQRZQKSIWFKB4EXCFK4BDAM', 'Дамира'],
        ['GB4TL4G5DRFRCUVVPE5B6542TVLSYAVARNUZUPWARCAEIDR7QMDOGZQQ', 'Егора'],
        ['GBEOQ4VGEH34LRR7SO36EAFSQMGH3VLX443NNZ4DS7WVICO577WOSLOV', 'Артема'],
        ['GDLCYXJLCUBJQ53ZMLTSDTDKR5R4IFRIL4PWEGDPHPIOQMFYHJ3HTVCP', 'Дмитрия'],

    ]

    for treasure in treasure_list:
        assets = await get_balances(treasure[0])
        diff = int(assets['EURDEBT']) - int(assets['EURMTL'])
        name = treasure[1] if chat_id == -1001169382324 else treasure[1][0]
        result += f"Сейчас в кубышке {name} {diff} наличных и {int(assets['EURMTL'])} EURMTL \n"
        total_cash += diff
        total_eurmtl += int(assets['EURMTL'])

    assets = await get_balances('GBQZDXEBW5DGNOSRUPIWUTIYTO7QM65NOU5VHAAACED4HII7FVXPCBOT')
    result += f"А у Skynet {int(assets['USDC'])} USDC и {int(assets['EURMTL'])} EURMTL \n"

    result += f"\n"
    result += f"Итого в кубышках {total_cash} наличных и {total_eurmtl} EURMTL \n"

    return result


async def get_balances(address: str, return_assets=False, return_data=False, return_signers=False):
    account = await stellar_get_account(address)
    assets = {}
    if account.get('type'):
        return []
    else:
        if return_assets:
            for balance in account['balances']:
                if balance["asset_type"][0:15] == "credit_alphanum":
                    assets[Asset(balance['asset_code'], balance['asset_issuer'])] = float(balance['balance'])
        else:
            for balance in account['balances']:
                if balance['asset_type'] == "native":
                    assets['XLM'] = float(balance['balance'])
                elif balance["asset_type"][0:15] == "credit_alphanum":
                    assets[balance['asset_code']] = float(balance['balance'])
        if return_data:
            return assets, account.get('data')
        if return_signers:
            return assets, account.get('signers')
        return assets


async def get_mrxpinvest_xdr(div_sum: float):
    accounts = await stellar_get_mtl_holders(mrxpinvest_asset)
    accounts_list = []
    total_sum = 0

    for account in accounts:
        balances = account["balances"]
        token_balance = 0
        for balance in balances:
            if balance["asset_type"][0:15] == "credit_alphanum":
                if balance["asset_code"] == mrxpinvest_asset.code:
                    token_balance = balance["balance"]
                    token_balance = int(token_balance[0:token_balance.find('.')])
        if account["account_id"] != 'GDIWYLCDWPXEXFWUI7PGO64UFYWYDIVCXQWD2IKHM3WYFEXA2E4ZOC4Z':
            accounts_list.append([account["account_id"], token_balance, 0])
            total_sum += token_balance

    persent = div_sum / total_sum

    for account in accounts_list:
        account[2] = account[1] * persent

    root_account = Server(horizon_url="https://horizon.stellar.org").load_account(mrxpinvest_asset.issuer)
    transaction = TransactionBuilder(source_account=root_account, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                     base_fee=base_fee)
    transaction.set_timeout(60 * 60)
    for account in accounts_list:
        transaction.append_payment_op(destination=account[0], asset=mrxpinvest_asset, amount=str(round(account[2], 7)))
    transaction = transaction.build()
    xdr = transaction.to_xdr()

    return xdr


async def get_defi_xdr(div_sum: int):
    accounts = await stellar_get_mtl_holders(defi_asset)
    accounts_list = []
    total_sum = 0
    div_bonus = div_sum * 0.1
    div_sum = div_sum - div_bonus

    for account in accounts:
        balances = account["balances"]
        token_balance = 0
        for balance in balances:
            if balance["asset_type"][0:15] == "credit_alphanum":
                if balance["asset_code"] == defi_asset.code:
                    token_balance = balance["balance"]
                    token_balance = int(token_balance[0:token_balance.find('.')])
        accounts_list.append([account["account_id"], token_balance, 0])
        total_sum += token_balance

    persent = div_sum / total_sum

    for account in accounts_list:
        if account[0] == 'GBVIX6CZ57SHXHGPA4AL7DACNNZX4I2LCKIAA3VQUOGTGWYQYVYSE5TU':
            account[2] = account[1] * persent + div_bonus
        else:
            account[2] = account[1] * persent

    root_account = Server(horizon_url="https://horizon.stellar.org").load_account(public_defi)
    transaction = TransactionBuilder(source_account=root_account, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                     base_fee=base_fee)
    transaction.set_timeout(60 * 60 * 12)
    for account in accounts_list:
        transaction.append_payment_op(destination=account[0], asset=satsmtl_asset, amount=str(round(account[2], 7)))
    transaction = transaction.build()
    xdr = transaction.to_xdr()

    return xdr


async def get_mtlbtc_xdr(btc_sum, address: str):
    root_account = Server(horizon_url="https://horizon.stellar.org").load_account(public_issuer)
    transaction = TransactionBuilder(source_account=root_account, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                     base_fee=base_fee)
    transaction.set_timeout(60 * 60 * 12)
    transaction.append_payment_op(destination=public_btc_guards, asset=btcdebt_asset, amount=btc_sum)
    transaction.append_payment_op(destination=address, asset=btcmtl_asset, amount=btc_sum)
    transaction = transaction.build()
    xdr = transaction.to_xdr()

    return xdr


def stellar_check_receive_sum(send_asset: Asset, send_sum: str, receive_asset: Asset) -> str:
    try:
        server = Server(horizon_url="https://horizon.stellar.org")
        call_result = server.strict_send_paths(send_asset, send_sum, [receive_asset]).call()
        if len(call_result['_embedded']['records']) > 0:
            # print(call_result)
            return call_result['_embedded']['records'][0]['destination_amount']
        else:
            return '0'
    except Exception as ex:
        logger.exception("stellar_check_receive_sum", send_asset.code + ' ' + send_sum + ' ' + receive_asset.code, ex)
        return '0'


def cmd_check_last_operation(address: str, filter_operation=None) -> datetime:
    operations = Server(horizon_url="https://horizon.stellar.org").operations().for_account(address).order().call()
    op = operations['_embedded']['records'][0]
    # print(operation["created_at"])  # 2022-08-23T13:47:33Z
    dt = datetime.strptime(op["created_at"], '%Y-%m-%dT%H:%M:%SZ')
    # print(dt)

    return dt


def cmd_check_fee() -> str:
    fee = Server(horizon_url="https://horizon.stellar.org").fee_stats().call()["fee_charged"]
    return fee['min'] + '-' + fee['max']
    # print(Server(horizon_url="https://horizon.stellar.org").fetch_base_fee())


async def cmd_update_fee_and_send(xdr: str) -> str:
    transaction = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
    fee_transaction = TransactionBuilder.build_fee_bump_transaction(public_sign, 10000, transaction,
                                                                    Network.PUBLIC_NETWORK_PASSPHRASE)
    transaction.set_timeout(60 * 60)
    # fee_transaction = FeeBumpTransactionEnvelope(FeeBumpTransaction(public_sign, 10000, transaction),
    #                                             network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
    fee_transaction.sign(private_sign)
    server = Server(horizon_url="https://horizon.stellar.org")
    resp = await stellar_async_submit(fee_transaction.to_xdr())

    return str(resp)


async def stellar_async_submit(xdr: str):
    async with ServerAsync(
            horizon_url="https://horizon.stellar.org", client=AiohttpClient()
    ) as server:
        transaction = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
        transaction_resp = await server.submit_transaction(transaction)
        # return json.dumps(resp, indent=2)
        return transaction_resp


def stellar_sync_submit(xdr: str):
    with Server(
            horizon_url="https://horizon.stellar.org"
    ) as server:
        transaction = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
        transaction_resp = server.submit_transaction(transaction)
        # return json.dumps(resp, indent=2)
        return transaction_resp


def stellar_get_receive_path(send_asset: Asset, send_sum: str, receive_asset: Asset) -> list:
    try:
        server = Server(horizon_url="https://horizon.stellar.org")
        call_result = server.strict_send_paths(send_asset, send_sum, [receive_asset]).call()
        if len(call_result['_embedded']['records']) > 0:
            # [{'asset_type': 'credit_alphanum12', 'asset_code': 'EURMTL',
            #  'asset_issuer': 'GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V'},
            # {'asset_type': 'credit_alphanum12', 'asset_code': 'BTCMTL',
            #  'asset_issuer': 'GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V'}]
            if len(call_result['_embedded']['records'][0]['path']) == 0:
                return []
            else:
                result = []
                for record in call_result['_embedded']['records'][0]['path']:
                    if record['asset_type'] == 'native':
                        result.append(xlm_asset)
                    else:
                        result.append(Asset(record['asset_code'],
                                            record['asset_issuer']))
                return result
        else:
            return []
    except Exception as ex:
        logger.exception(["stellar_check_receive_sum", send_asset.code + ' ' + send_sum + ' ' + receive_asset.code, ex])
        return []


async def stellar_get_account(account_id) -> json:
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://horizon.stellar.org/accounts/{account_id}') as resp:
            # print(resp.status)
            # print(await resp.text())
            return await resp.json()


def stellar_swap(from_account: str, send_asset: Asset, send_amount: str, receive_asset: Asset,
                 receive_amount: str):
    server = Server(horizon_url="https://horizon.stellar.org")
    source_account = server.load_account(from_account)
    transaction = TransactionBuilder(source_account=source_account,
                                     network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE, base_fee=base_fee)
    transaction.set_timeout(60 * 60)
    transaction.append_path_payment_strict_send_op(from_account, send_asset, send_amount, receive_asset,
                                                   receive_amount,
                                                   stellar_get_receive_path(send_asset, send_amount, receive_asset))
    transaction.set_timeout(60 * 60)
    full_transaction = transaction.build()
    logger.info(full_transaction.to_xdr())
    return full_transaction.to_xdr()


def stellar_claimable(source_address, asset, amount, destination_address, xdr=None):
    if xdr:
        transaction = TransactionBuilder.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
    else:
        server = Server(horizon_url="https://horizon.stellar.org")
        root_account = server.load_account(source_address)
        transaction = TransactionBuilder(source_account=root_account,
                                         network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                         base_fee=base_fee)
        transaction.set_timeout(60 * 60)
    from stellar_sdk import Claimant
    transaction.append_create_claimable_balance_op(asset, amount, [Claimant(destination=source_address),
                                                                   Claimant(destination=destination_address)])
    transaction = transaction.build()
    xdr = transaction.to_xdr()
    # print(f"xdr: {xdr}")
    return xdr


def stellar_claim_claimable(source_address, balance_id, xdr=None):
    if xdr:
        transaction = TransactionBuilder.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
    else:
        server = Server(horizon_url="https://horizon.stellar.org")
        root_account = server.load_account(source_address)
        transaction = TransactionBuilder(source_account=root_account,
                                         network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                         base_fee=base_fee)
        transaction.set_timeout(60 * 60)

    transaction.append_claim_claimable_balance_op(balance_id=balance_id)
    transaction = transaction.build()
    xdr = transaction.to_xdr()
    return xdr


async def send_satsmtl_pending():
    accounts = await stellar_get_mtl_holders()
    print(len(accounts))
    cnt = 0
    xdr = None
    for account in accounts:
        cnt += 1
        xdr = stellar_claimable(public_div, satsmtl_asset, '1', account['id'], xdr=xdr)
        if cnt > 96:
            print(xdr)
            stellar_sync_submit(stellar_sign(xdr, private_sign))
            xdr = None
            cnt = 0
    print(xdr)
    stellar_sync_submit(stellar_sign(xdr, private_sign))


def save_usdc_accounts():
    server = Server(horizon_url="https://horizon.stellar.org")
    accounts = []
    accounts_call_builder = server.accounts().for_asset(
        Asset('USDC', 'GA5ZSEJYB37JRC5AVCIA5MOP4RHTM335X2KGX3IHOJAPP5RE34K4KZVN')).limit(200)

    accounts += accounts_call_builder.call()["_embedded"]["records"]
    i = 0

    while page_records := accounts_call_builder.next()["_embedded"]["records"]:
        accounts += page_records
        i += 1
        print(i)
        for account in accounts:
            assets = {}
            for balance in account['balances']:
                if balance['asset_type'] == "native":
                    assets['XLM'] = float(balance['balance'])
                elif balance["asset_type"][0:15] == "credit_alphanum":
                    assets[balance['asset_code']] = float(balance['balance'])
            fb.execsql('update or insert into t_pending (address_id, xlm, usdc, home_domain) '
                       'values (?,?,?,?) matching (address_id)',
                       (account['id'], int(assets['XLM']), int(assets['USDC']), account.get('home_domain')))
            accounts.remove(account)

    # print(json.dumps(response, indent=4))
    print(json.dumps(accounts, indent=4))


# from loguru import logger


@logger.catch
def send_mtl_pending():
    records = fb.execsql(f"select address_id from t_pending where dt_send is null and home_domain = ?", ['lobstr.co'])
    print(len(records))
    cnt = 0
    xdr = None
    for rec in records:
        cnt += 1
        xdr = stellar_claimable(public_wallet, mtl_asset, '0.2', rec[0], xdr=xdr)
        fb.execsql(f"update t_pending set dt_send = localtimestamp where address_id = ?", [rec[0]])
        if cnt > 96:
            print(xdr)
            fb.execsql("insert into T_TRANSACTION (ID_DIV_LIST, XDR_ID, XDR) values (?,?,?)", [5, 10, xdr])
            stellar_sync_submit(stellar_sign(xdr, private_sign))
            xdr = None
            cnt = 0
    print(xdr)
    fb.execsql("insert into T_TRANSACTION (ID_DIV_LIST, XDR_ID, XDR) values (?,?,?)", [5, 10, xdr])
    stellar_sync_submit(stellar_sign(xdr, private_sign))


def no_err():
    with suppress(NotFoundError):
        cb = Server(horizon_url="https://horizon.stellar.org").transactions().transaction(
            '8bde064fe81b9383543ba2e043fe47f0a916941f390564a4dcab33d44fd81ab8').call()
        print(cb)


def return_satsmtl_pending():
    cb_cb = Server(horizon_url="https://horizon.stellar.org").claimable_balances().for_sponsor(public_div).limit(
        90).call()
    xdr = None
    for record in cb_cb['_embedded']['records']:
        xdr = stellar_claim_claimable(public_div, record['id'], xdr=xdr)

    stellar_sync_submit(stellar_sign(xdr, private_sign))


def return_mtl_pending():
    cb_cb = Server(horizon_url="https://horizon.stellar.org").claimable_balances().for_sponsor(public_wallet).limit(
        10).call()
    xdr = None
    insert = []
    for record in cb_cb['_embedded']['records']:
        # print(record['claimants'][1]['destination'])
        insert.append([record['claimants'][1]['destination']])
        xdr = stellar_claim_claimable(public_wallet, record['id'], xdr=xdr)

    stellar_sync_submit(stellar_sign(xdr, private_sign))
    fb.many_insert(f"update t_pending set dt_back = localtimestamp where address_id = ?", insert)


def save_transactions():
    cb_cb = Server(horizon_url="https://horizon.stellar.org").transactions().for_account(public_wallet).limit(
        200).order()
    cb_list = []
    returned_list = []
    i = 0
    records = cb_cb.call()
    while len(records['_embedded']['records']) > 0:
        for record in records['_embedded']['records']:
            xdr = record['envelope_xdr']
            transaction = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
            txResult = TransactionResult.from_xdr(record["result_xdr"])
            results = txResult.result.results
            if type(transaction.transaction.operations[0]).__name__ == 'CreateClaimableBalance':
                if transaction.transaction.operations[0].asset.code == 'MTL':
                    for idx, operation in enumerate(transaction.transaction.operations):
                        operationResult = results[idx].tr.create_claimable_balance_result
                        balanceId = operationResult.balance_id.to_xdr_bytes().hex()
                        # print(f"Balance ID (2): {balanceId}")
                        # print(operation.claimants[1].destination)
                        cb_list.append([operation.claimants[1].destination, balanceId])
            if type(transaction.transaction.operations[0]).__name__ == 'ClaimClaimableBalance':
                for operation in transaction.transaction.operations:
                    # print(operation.balance_id)
                    returned_list.append([operation.balance_id])

        records = cb_cb.next()
        i += 1
        print(i)

    with open(f"cb_list.json", "w") as fp:
        json.dump(cb_list, fp, indent=2)
    with open(f"returned_list.json", "w") as fp:
        json.dump(returned_list, fp, indent=2)
    #############################
    with open('returned_list.json', 'r', encoding='UTF-8') as fp:
        data = json.load(fp)
    print(data)
    fb.many_insert(f"update t_pending set dt_back = localtimestamp where dt_back is null and CLAIMABLE_BALANCE_ID = ?",
                   data)


async def send_msg_to_mtl():
    holders = await stellar_get_mtl_holders(mini=False)
    i = 0
    x = 0
    transaction = TransactionBuilder(
        source_account=Server(horizon_url="https://horizon.stellar.org").load_account(public_pending),
        network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
        base_fee=base_fee)
    transaction.set_timeout(60 * 60)

    for record in holders:
        found1 = list(filter(lambda x: x.get('asset_code') == 'EURMTL', record['balances']))
        found2 = list(filter(lambda x: x.get('asset_code') == 'SATSMTL', record['balances']))
        if len(found1) > 0 and len(found2) > 0:
            print('found ' + record['id'])
        else:
            print('not found', record['id'], i)
            i = i + 1
            x = x + 1
            transaction.append_payment_op(destination=record['id'], amount='0.0000001', asset=mtl_asset)
            if i > 90:
                i = 0
                transaction.add_text_memo('Visit our site for dividends')
                xdr = transaction.build().to_xdr()
                print(xdr)
                stellar_sync_submit(stellar_sign(xdr, private_sign))
                # new tr
                transaction = TransactionBuilder(
                    source_account=Server(horizon_url="https://horizon.stellar.org").load_account(public_pending),
                    network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                    base_fee=base_fee)
                transaction.set_timeout(60 * 60)

    transaction.add_text_memo('Visit our site for dividends')
    xdr = transaction.build().to_xdr()
    print(xdr)
    stellar_sync_submit(stellar_sign(xdr, private_sign))
    print(x)


def float2str(f) -> str:
    if isinstance(f, str):
        f = f.replace(',', '.')
        f = float(f)
    s = "%.7f" % f
    while len(s) > 1 and s[-1] in ('0', '.'):
        l = s[-1]
        s = s[0:-1]
        if l == '.':
            break
    return s


def decode_effects_records(watch_list, records, ledger):
    result = []
    for record in records:
        if record['type'] in ('liquidity_pool_trade', 'account_created', 'claimable_balance_sponsorship_removed',
                              'trustline_created', 'trustline_removed', 'claimable_balance_created',
                              'signer_created', 'signer_removed', 'trustline_flags_updated', 'trustline_authorized',
                              'trustline_authorized_to_maintain_liabilities', 'trustline_sponsorship_created',
                              'claimable_balance_claimant_created', 'claimable_balance_sponsorship_created',
                              'data_updated', 'trustline_updated', 'signer_updated', 'account_thresholds_updated',
                              'trustline_deauthorized', 'account_flags_updated', 'liquidity_pool_deposited',
                              'data_created', 'data_removed', 'account_removed', 'account_sponsorship_created',
                              'signer_sponsorship_created', 'account_home_domain_updated', 'liquidity_pool_removed',
                              'trustline_sponsorship_removed', 'liquidity_pool_withdrew', 'liquidity_pool_created',
                              'account_inflation_destination_updated', 'sequence_bumped', 'signer_sponsorship_removed',
                              'account_sponsorship_removed', 'liquidity_pool_revoked', 'claimable_balance_clawed_back'):
            continue

        if record['type'] == 'account_debited':
            if record['account'] in watch_list or record.get('asset_issuer') in watch_list:
                # account_debited
                # 'id': '0193165308029165569-0000000002', 'paging_token': '193165308029165569-2', 'account': 'GAO6SHKSQ3T3COGUWM3PYW4TELCFKCC57OOSM7QFZP6UA5OSDDNCTZPS',
                # 'type': 'account_debited', 'type_i': 3, 'created_at': '2023-02-16T14:50:53Z', 'asset_type': 'native', 'amount': '0.0655842'}
                op_date = datetime.strptime(record['created_at'], '%Y-%m-%dT%H:%M:%SZ')
                # ['Дата', 'Операция', 'Сумма 1', 'Код', 'Сумма 2', 'Код 2', 'От кого', 'Кому', 'Хеш транзы', 'Мемо', 'paging_token']]
                result.append([op_date, record['type'], record['amount'],
                               record.get('asset_code', 'XLM'), None, None, None, record.get('account'), None, '',
                               record['paging_token'], ledger])
            continue

        if record['type'] == 'account_credited':
            if record['account'] in watch_list or record.get('asset_issuer') in watch_list:
                # account_credited
                # 'id': '0193165308029046787-0000000001', 'paging_token': '193165308029046787-1', 'account': 'GBVOXZ3W3ECRPABUNXAW6UWZZ7D7MOW5RQZWBKW3NJZC33JEKO55LXXD',
                # 'type': 'account_credited', 'type_i': 2, 'created_at': '2023-02-16T14:50:53Z', 'asset_type': 'credit_alphanum12', 'asset_code': 'GOLDRESERVE',
                # 'asset_issuer': 'GBVOXZ3W3ECRPABUNXAW6UWZZ7D7MOW5RQZWBKW3NJZC33JEKO55LXXD', 'amount': '2427.0000000'}
                op_date = datetime.strptime(record['created_at'], '%Y-%m-%dT%H:%M:%SZ')
                # ['Дата', 'Операция', 'Сумма 1', 'Код', 'Сумма 2', 'Код 2', 'От кого', 'Кому', 'Хеш транзы', 'Мемо', 'paging_token']]
                result.append([op_date, record['type'], record['amount'],
                               record.get('asset_code', 'XLM'), None, None, None, record.get('account'), None, '',
                               record['paging_token'], ledger])
            continue

        if record['type'] == 'trade':
            if record['account'] in watch_list or record['seller'] in watch_list or record.get(
                    'sold_asset_issuer') in watch_list or record.get('bought_asset_issuer') in watch_list:
                # trade
                # 'id': '0193165308029235201-0000000001', 'paging_token': '193165308029235201-1', 'account': 'GBKGNJW7NYSHKFR3RQECSSB2ZD74SVCAOOJEUINPNK3Q2S5JDS3FFMGX',
                # 'type': 'trade', 'type_i': 33, 'created_at': '2023-02-16T14:50:53Z', 'seller': 'GDXID5C7CB3HRT7OHPNTYO2A53UUQB7EPKTZAMV3HTOPKE5JYJFT2P7P',
                # 'offer_id': '1186493974', 'sold_amount': '690.8303426', 'sold_asset_type': 'credit_alphanum4', 'sold_asset_code': 'EURV',
                # 'sold_asset_issuer': 'GDB6ZOJ46MDSERVTH2B7P6C4LEAWU3UDJZLPUFERROEDV774U4AQIG5G', 'bought_amount': '737.1159935', 'bought_asset_type': 'credit_alphanum4',
                # 'bought_asset_code': 'USDV', 'bought_asset_issuer': 'GDB6ZOJ46MDSERVTH2B7P6C4LEAWU3UDJZLPUFERROEDV774U4AQIG5G'}
                op_date = datetime.strptime(record['created_at'], '%Y-%m-%dT%H:%M:%SZ')
                # ['Дата', 'Операция', 'Сумма 1', 'Код', 'Сумма 2', 'Код 2', 'От кого', 'Кому', 'Хеш транзы', 'Мемо', 'paging_token']]
                result.append([op_date, record['type'], record['sold_amount'],
                               record.get('sold_asset_code', 'XLM'), record['bought_amount'],
                               record.get('bought_asset_code', 'XLM'), record.get('seller'), record.get('account'),
                               None, '', record['paging_token'], ledger])
            continue
        if record['type'] == 'claimable_balance_claimed':
            if record['account'] in watch_list:
                # claimable_balance_claimed
                # 'id': '0193165308029046786-0000000001', 'paging_token': '193165308029046786-1', 'account': 'GCHGRZLYXNTMRIICT2RK6OMABNP7RSNWL7GQCI5MKH5YGOVMUUWTPNGG',
                # 'type': 'claimable_balance_claimed', 'type_i': 52, 'created_at': '2023-02-16T14:50:53Z', 'asset': 'GOLDRESERVE:GBVOXZ3W3ECRPABUNXAW6UWZZ7D7MOW5RQZWBKW3NJZC33JEKO55LXXD',
                # 'balance_id': '00000000bbd6448ce50c7ae88ac7237fb3e83f6ca9b0326093de06508080d9cccf96c460', 'amount': '2427.0000000'}
                op_date = datetime.strptime(record['created_at'], '%Y-%m-%dT%H:%M:%SZ')
                # ['Дата', 'Операция', 'Сумма 1', 'Код', 'Сумма 2', 'Код 2', 'От кого', 'Кому', 'Хеш транзы', 'Мемо', 'paging_token']]
                result.append([op_date, record['type'], record['amount'],
                               record['asset'].split(':')[0], None, None, None, record.get('account'), None, '',
                               record['paging_token'], ledger])

            continue
        print(record['type'], record)
    return result


async def cmd_check_ledger():
    watch_list = fb.get_watch_list()
    ledger_id = int(cmd_load_bot_value(BotValueTypes.LastLedger, 0, '45407700'))
    max_ledger_id = ledger_id + 17
    # print(f'ledger diffrent {ledger_id}')
    while max_ledger_id > ledger_id:
        ledger_data = []
        ledger_id += 1
        logger.info(f'ledger_id {ledger_id}')
        effects = []
        async with ServerAsync(
                horizon_url="https://horizon.stellar.org", client=AiohttpClient(request_timeout=5)
        ) as server:
            call_builder = server.effects().for_ledger(ledger_id).limit(200)
            page_records = await call_builder.call()
            while page_records["_embedded"]["records"]:
                effects.extend(page_records["_embedded"]["records"])
                page_records = await call_builder.next()

        if len(effects) > 0:
            data = decode_effects_records(watch_list, effects, ledger_id)
            if len(data) > 0:
                ledger_data.extend(data)

        # ['Дата', 'Операция', 'Сумма 1', 'Код', 'Сумма 2', 'Код 2', 'От кого', 'Кому', 'Хеш транзы', 'Мемо', 'paging_token', 'ledger']]]
        # logger.info(f'ledger_data {ledger_data}')
        fb.many_insert("insert into t_operations (dt, operation, amount1, code1, amount2, code2, "
                       "from_account, for_account, transaction_hash, memo, id, ledger) "
                       "values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       ledger_data)
        cmd_save_bot_value(BotValueTypes.LastLedger, 0, ledger_id)


async def get_clear_data_xdr(address: str):
    acc = await stellar_get_account(address)
    xdr = None
    for data_name in acc['data']:
        xdr = cmd_gen_data_xdr(address, data_name + ':', xdr)
    return xdr


def get_memo_by_op(op: str):
    operation = Server(horizon_url="https://horizon.stellar.org").operations().operation(op).call()
    transaction = Server(horizon_url="https://horizon.stellar.org").transactions().transaction(
        operation['transaction_hash']).call()

    return transaction.get('memo', 'None')


if __name__ == "__main__":
    # a = asyncio.run(get_defi_xdr(677000))
    # print('\n'.join(decode_xdr(a)))
    # print(asyncio.run(get_balances('GDX23CPGMQ4LN55VGEDVFZPAJMAUEHSHAMJ2GMCU2ZSHN5QF4TMZYPIS', return_data=True)))
    # s = asyncio.run(cmd_show_data(public_div,'LAST_DIVS',True))
    # print(cmd_check_new_asset_transaction('MTL',BotValueTypes.LastMTLTransaction,10))
    # xdr = cmd_gen_data_xdr(public_div,'LAST_DIVS:1386')
    # print(gen_new('USD'))
    # xdr = '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'
    # xdr2 = 'AAAAAgAAAAAQoKcL6PJThXuPDvKgGqbyQM0/1HK385wAq65jOhf2/wAAE4gCeukxAAAABAAAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEAAAABAAAAABCgpwvo8lOFe48O8qAapvJAzT/UcrfznACrrmM6F/b/AAAABQAAAAAAAAAAAAAAAAAAAAAAAAABAAAAAQAAAAEAAAABAAAAAQAAAAEAAAAAAAAAAAAAAAAAAAAA'
    # print(stellar_sync_submit(stellar_sign(xdr, private_sign)))
    # print(stellar_add_xdr(xdr, xdr2))
    # print(decode_xdr(
    #    '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'))
    pass
