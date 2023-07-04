import base64
import json
import math
from db.requests import *
from copy import deepcopy

import aiohttp
import requests
from aiogram import Bot
from aiogram.types import Message
from loguru import logger
from stellar_sdk import (FeeBumpTransactionEnvelope, TransactionEnvelope, TextMemo, Network, Server, Asset,
                         AiohttpClient, ServerAsync, Price, TransactionBuilder, Account)
from stellar_sdk.sep.federation import resolve_account_id_async

from config_reader import config
from utils.global_data import float2str
from utils.gspread_tools import agcm

base_fee = config.base_fee


class MTLAddresses:
    public_issuer = "GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V"
    public_pawnshop = "GDASYWP6F44TVNJKZKQ2UEVZOKTENCJFTWVMP6UC7JBZGY4ZNB6YAVD4"
    public_defi = "GBTOF6RLHRPG5NRIU6MQ7JGMCV7YHL5V33YYC76YYG4JUKCJTUP5DEFI"
    public_btc_guards = "GATUN5FV3QF35ZMU3C63UZ63GOFRYUHXV2SHKNTKPBZGYF2DU3B7IW6Z"
    public_fund_city = "GCOJHUKGHI6IATN7AIEK4PSNBPXIAIZ7KB2AWTTUCNIAYVPUB2DMCITY"
    public_fund_defi = "GAEZHXMFRW2MWLWCXSBNZNUSE6SN3ODZDDOMPFH3JPMJXN4DKBPMDEFI"
    public_fund_mabiz = "GAQ5ERJVI6IW5UVNPEVXUUVMXH3GCDHJ4BJAXMAAKPR5VBWWAUOMABIZ"
    public_usdm = "GDHDC4GBNPMENZAOBB4NCQ25TGZPDRK6ZGWUGSI22TVFATOLRPSUUSDM"
    public_fin = "GCSAXEHZBQY65URLO6YYDOCTRLIGTNMGCQHVW2RZPFNPTEJN6VN7TFIN"
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


class MTLAssets:
    mtl_asset = Asset("MTL", MTLAddresses.public_issuer)
    eurmtl_asset = Asset("EURMTL", MTLAddresses.public_issuer)
    eurdebt_asset = Asset("EURDEBT", MTLAddresses.public_issuer)
    xlm_asset = Asset("XLM", None)
    satsmtl_asset = Asset("SATSMTL", MTLAddresses.public_issuer)
    btcmtl_asset = Asset("BTCMTL", MTLAddresses.public_issuer)
    btcdebt_asset = Asset("BTCDEBT", MTLAddresses.public_issuer)
    usdc_asset = Asset("USDC", "GA5ZSEJYB37JRC5AVCIA5MOP4RHTM335X2KGX3IHOJAPP5RE34K4KZVN")
    mrxpinvest_asset = Asset("MrxpInvest", 'GDAJVYFMWNIKYM42M6NG3BLNYXC3GE3WMEZJWTSYH64JLZGWVJPTGGB7')
    defi_asset = Asset("MTLDefi", MTLAddresses.public_defi)
    usdmm_asset = Asset("USDMM", MTLAddresses.public_usdm)
    usdm_asset = Asset("USDM", MTLAddresses.public_usdm)


pack_count = 70  # for select first pack_count - to pack to xdr

exchange_bots = (MTLAddresses.public_exchange_eurmtl_xlm, MTLAddresses.public_exchange_eurmtl_btc,
                 MTLAddresses.public_exchange_eurmtl_usdc, MTLAddresses.public_fire)


def check_url_xdr(url):
    rq = requests.get(url).text
    rq = rq[rq.find('<span class="tx-body">') + 22:]
    # print(rq)
    rq = rq[:rq.find('</span>')]
    rq = rq.replace("&#x3D;", "=")
    # print(rq)
    return decode_xdr(rq)


def cleanhtml(raw_html):
    clean_regex = re.compile('<.*?>')
    cleantext = re.sub(clean_regex, '', raw_html)
    while cleantext.find("\n") > -1:
        cleantext = cleantext.replace("\n", " ")
    while cleantext.find("  ") > -1:
        cleantext = cleantext.replace("  ", " ")
    return cleantext


def cmd_alarm_url(url):
    rq = requests.get(url).text
    if rq.find('<h4 class="published">') > -1:
        return 'Нечего напоминать, транзакция отправлена.'
    rq = rq[rq.find('<div class="col-10 ignorants-nicks">'):]
    rq = rq[rq.find('">') + 2:]
    rq = rq[:rq.find('</div>')]
    rq = rq.replace("&#x3D;", "=")
    return cleanhtml(rq)


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


def address_id_to_username(key) -> str:
    # toDo to gogledocs
    # with open('members_key.json', 'r', encoding='UTF-8') as fp:
    #    data = json.load(fp)
    # if key in data:
    #    return data[key]
    # else:
    return key[:4] + '..' + key[-4:]


async def send_by_list(bot: Bot, all_users: list, message: Message, session: Session = None, url=None):
    good_users = []
    bad_users = []
    if url is None:
        url = message.reply_to_message.get_url()
    msg = f'@{message.from_user.username} call you here {url}'
    for user in all_users:
        if len(user) > 2 and user[0] == '@':
            try:
                chat_id = cmd_load_user_id(session, user[1:])
                await bot.send_message(chat_id=chat_id, text=msg)
                good_users.append(user)
            except Exception as ex:
                bad_users.append(user)
                logger.info(ex)
                pass
    await message.reply(f'was send to {" ".join(good_users)} \n can`t send to {" ".join(bad_users)}')


def cmd_check_fee() -> str:
    fee = Server(horizon_url="https://horizon.stellar.org").fee_stats().call()["fee_charged"]
    return fee['min'] + '-' + fee['max']
    # print(Server(horizon_url="https://horizon.stellar.org").fetch_base_fee())


async def stellar_get_account(account_id) -> json:
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://horizon.stellar.org/accounts/{account_id}') as resp:
            # print(resp.status)
            # print(await resp.text())
            return await resp.json()


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


def get_private_sign():
    return config.private_sign.get_secret_value()


def stellar_stop_all_exchange():
    xdr = None
    for bot in exchange_bots:
        xdr = stellar_remove_orders(bot, xdr)
    stellar_sync_submit(stellar_sign(xdr, config.private_sign.get_secret_value()))


def stellar_sign(xdr, signkey):
    transaction = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
    transaction.sign(signkey)
    return transaction.to_xdr()


def stellar_sync_submit(xdr: str):
    with Server(
            horizon_url="https://horizon.stellar.org"
    ) as server:
        transaction = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
        transaction_resp = server.submit_transaction(transaction)
        # return json.dumps(resp, indent=2)
        return transaction_resp


async def get_bim_list():
    # ['GARNOMR62CRFSI2G2OQYA5SPGFFDBBY566AWZF4637MNF74UZMBNOZVD', True],
    agc = await agcm.authorize()
    ss = await agc.open("MTL_BIM_register")
    wks = await ss.worksheet("List")

    addresses = []
    data = await wks.get_all_values()
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


async def cmd_show_bim(session: Session):
    result = ''
    bod_list = await get_bim_list()
    good = list(filter(lambda x: x[1], bod_list))

    total_sum = exec_total_user_div(session)

    result += f'Всего {len(bod_list)} участников'
    result += f'\n{len(good)} участников c доступом к EURMTL'
    result += f'\nЧерез систему за всю историю выплачено {round(total_sum, 2)} EURMTL'

    balances = {}
    rq = requests.get(f'https://horizon.stellar.org/accounts/{MTLAddresses.public_bod_eur}').json()
    # print(json.dumps(rq, indent=4))
    for balance in rq["balances"]:
        if balance["asset_type"] == 'credit_alphanum12':
            balances[balance["asset_code"]] = balance["balance"]

    result += f'\n\nСейчас к распределению {balances["EURMTL"]} EURMTL или по {int(float(balances["EURMTL"]) / len(good) * 100) / 100} на участника'
    # result += f'\nНачать выплаты /do_bod'
    return result


async def get_cash_balance(chat_id):
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


def cmd_create_list(session: Session, memo: str, pay_type: int):
    new = TDivList(memo=memo, pay_type=pay_type)
    session.add(new)
    session.commit()
    return new.id


async def cmd_calc_bim_pays(session: Session, list_id: int, test_sum=0):
    bod_list = await get_bim_list()
    good = list(filter(lambda x: x[1], bod_list))

    balances = {}
    rq = requests.get(f'https://horizon.stellar.org/accounts/{MTLAddresses.public_bod_eur}').json()
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
    payments = [
        TPayments(
            user_key=item[0],
            mtl_sum=item[1],
            user_calc=item[2],
            user_div=item[3],
            id_div_list=item[4]
        )
        for item in mtl_accounts
    ]
    session.add_all(payments)
    session.commit()

    return mtl_accounts


def get_key_1(key):
    return key[1]


def cmd_gen_xdr(session: Session, list_id: int):
    div_list = get_div_list(session, list_id)
    memo = div_list.memo
    pay_type = div_list.pay_type
    server = Server(horizon_url="https://horizon.stellar.org")
    div_account, asset = None, None
    if pay_type == 0:
        div_account = server.load_account(MTLAddresses.public_div)
        asset = MTLAssets.eurmtl_asset

    if pay_type == 1:
        div_account = server.load_account(MTLAddresses.public_bod_eur)
        asset = MTLAssets.eurmtl_asset

    if pay_type == 4:
        div_account = server.load_account(MTLAddresses.public_div)
        asset = MTLAssets.satsmtl_asset

    transaction = TransactionBuilder(source_account=div_account, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                     base_fee=base_fee)
    transaction.set_timeout(60 * 60)

    for payment in get_payments(session, list_id, pack_count):
        if round(payment.user_div, 7) > 0:
            transaction.append_payment_op(destination=payment.user_key, amount=str(round(payment.user_div, 7)),
                                          asset=asset)
        payment.was_packed = 1
    session.commit()

    transaction.add_text_memo(memo)
    transaction = transaction.build()
    xdr = transaction.to_xdr()
    # print(f"xdr: {xdr}")

    session.add(TTransaction(xdr=xdr, id_div_list=list_id, xdr_id=0))
    session.commit()
    need = count_unpacked_payments(session, list_id)
    # print(f'need {need} more')
    return need


async def cmd_send_by_list_id(session: Session, list_id: int):
    # records = fb.execsql(f"select first 3 t.id, t.xdr from t_transaction t where t.was_send = 0 and t.id_div_list = ?",
    #                     [list_id])

    for db_transaction in cmd_load_transactions(session, list_id):
        transaction = TransactionEnvelope.from_xdr(db_transaction.xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
        server = Server(horizon_url="https://horizon.stellar.org")
        div_account = server.load_account(transaction.transaction.source.account_id)
        sequence = div_account.sequence + 1
        transaction.transaction.sequence = sequence
        transaction.sign(config.private_sign.get_secret_value())
        transaction_resp = await stellar_async_submit(transaction.to_xdr())
        logger.info(transaction_resp)
        db_transaction.was_send = 1
        db_transaction.xdr_id = sequence
    session.commit()

    return cmd_count_unsent_transactions(session, list_id)


async def stellar_async_submit(xdr: str):
    async with ServerAsync(
            horizon_url="https://horizon.stellar.org", client=AiohttpClient()
    ) as server:
        transaction = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
        transaction_resp = await server.submit_transaction(transaction)
        # return json.dumps(resp, indent=2)
        return transaction_resp


async def cmd_calc_divs(session: Session, div_list_id: int, donate_list_id: int, test_sum=0):
    # server = Server(horizon_url="https://horizon.stellar.org")

    # MTL
    rq = requests.get(f'https://horizon.stellar.org/assets?asset_code=MTL&asset_issuer={MTLAddresses.public_issuer}')
    mtl_sum = float(rq.json()['_embedded']['records'][0]['amount'])
    rq = requests.get(
        f'https://horizon.stellar.org/assets?asset_code=MTLRECT&asset_issuer={MTLAddresses.public_issuer}')
    mtl_sum += float(rq.json()['_embedded']['records'][0]['amount'])
    # FOND
    fund_balance = await get_balances(MTLAddresses.public_issuer)
    mtl_sum = mtl_sum - fund_balance.get('MTL', 0)

    div_accounts = []
    donates = []
    if test_sum > 0:
        div_sum = test_sum
    else:
        # get balance
        div_sum = await get_balances(MTLAddresses.public_div)
        div_sum = div_sum['EURMTL']
        logger.info(f'div_sum = {div_sum}')
        await stellar_async_submit(stellar_sign(cmd_gen_data_xdr(MTLAddresses.public_div, f'LAST_DIVS:{div_sum}'),
                                                config.private_sign.get_secret_value()))

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

        if (eur > 0) and (div > 0.0001) and (account["account_id"] != MTLAddresses.public_issuer) \
                and (account["account_id"] != MTLAddresses.public_pawnshop):
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
    payments = [
        TPayments(
            user_key=item[0],
            mtl_sum=item[1],
            user_calc=item[2],
            user_div=item[3],
            id_div_list=item[4]
        )
        for item in div_accounts
    ]
    session.add_all(payments)
    session.commit()

    return div_accounts
    # print(*mtl_accounts, sep='\n')


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


async def cmd_calc_sats_divs(session: Session, div_list_id: int, test_sum=0):
    # MTL
    rq = requests.get(f'https://horizon.stellar.org/assets?asset_code=MTL&asset_issuer={MTLAddresses.public_issuer}')
    mtl_sum = float(rq.json()['_embedded']['records'][0]['amount'])
    rq = requests.get(
        f'https://horizon.stellar.org/assets?asset_code=MTLRECT&asset_issuer={MTLAddresses.public_issuer}')
    mtl_sum += float(rq.json()['_embedded']['records'][0]['amount'])
    # FOND
    fund_balance = await get_balances(MTLAddresses.public_issuer)
    mtl_sum = mtl_sum - fund_balance.get('MTL', 0)

    div_accounts = []
    donates = []
    if test_sum > 0:
        div_sum = test_sum
    else:
        # get balance
        div_sum = await get_balances(MTLAddresses.public_div)
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

        if (sats_open > 0) and (div > 0.0001) and (account["account_id"] != MTLAddresses.public_issuer) \
                and (account["account_id"] != MTLAddresses.public_pawnshop):
            div_accounts.append([account["account_id"], balance_mtl + balance_rect, div, div, div_list_id])

    div_accounts.sort(key=get_key_1, reverse=True)
    payments = [
        TPayments(
            user_key=item[0],
            mtl_sum=item[1],
            user_calc=item[2],
            user_div=item[3],
            id_div_list=item[4]
        )
        for item in div_accounts
    ]
    session.add_all(payments)
    session.commit()

    return div_accounts
    # print(*mtl_accounts, sep='\n')


async def cmd_get_new_vote_all_mtl(public_key, remove_master=False):
    if len(public_key) > 10:
        vote_list = await cmd_gen_mtl_vote_list()
        result = [gen_vote_xdr(public_key, vote_list, remove_master=remove_master, source=public_key)]
    else:
        vote_list = await cmd_gen_mtl_vote_list()
        # vote_list1 = copy.deepcopy(vote_list)
        vote_list2 = deepcopy(vote_list)
        vote_list3 = deepcopy(vote_list)
        vote_list4 = deepcopy(vote_list)
        vote_list5 = deepcopy(vote_list)
        vote_list6 = deepcopy(vote_list)
        # print(vote_list)
        result = []
        transaction = TransactionBuilder(
            source_account=Server(horizon_url="https://horizon.stellar.org").load_account(MTLAddresses.public_issuer),
            network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE, base_fee=base_fee)
        sequence = transaction.source_account.sequence
        xdr = gen_vote_xdr(MTLAddresses.public_issuer, vote_list, transaction)
        xdr = gen_vote_xdr(MTLAddresses.public_adm, vote_list2, transaction, MTLAddresses.public_adm,
                           remove_master=True)
        xdr = gen_vote_xdr(MTLAddresses.public_fund_defi, vote_list3, transaction, MTLAddresses.public_fund_defi,
                           remove_master=True)
        xdr = gen_vote_xdr(MTLAddresses.public_fund_city, vote_list4, transaction, MTLAddresses.public_fund_city,
                           remove_master=True)
        xdr = gen_vote_xdr(MTLAddresses.public_fund_mabiz, vote_list5, transaction, MTLAddresses.public_fund_mabiz,
                           remove_master=True)
        # return sequence because every build inc number
        transaction.source_account.sequence = sequence
        transaction.set_timeout(60 * 60 * 48)
        xdr = gen_vote_xdr(MTLAddresses.public_pawnshop, vote_list6, transaction, MTLAddresses.public_pawnshop, )
        result.append(xdr)

    # print(gen_vote_xdr(public_new,vote_list2))

    return result


async def get_defi_xdr(div_sum: int):
    accounts = await stellar_get_mtl_holders(MTLAssets.defi_asset)
    accounts_list = []
    total_sum = 0
    # div_bonus = div_sum * 0.1
    # div_sum = div_sum - div_bonus

    for account in accounts:
        balances = account["balances"]
        token_balance = 0
        for balance in balances:
            if balance["asset_type"][0:15] == "credit_alphanum":
                if balance["asset_code"] == MTLAssets.defi_asset.code:
                    token_balance = balance["balance"]
                    token_balance = int(token_balance[0:token_balance.find('.')])
        accounts_list.append([account["account_id"], token_balance, 0])
        total_sum += token_balance

    persent = div_sum / total_sum

    for account in accounts_list:
        # if account[0] == 'GBVIX6CZ57SHXHGPA4AL7DACNNZX4I2LCKIAA3VQUOGTGWYQYVYSE5TU':
        #    account[2] = account[1] * persent + div_bonus
        # else:
        account[2] = account[1] * persent

    root_account = Server(horizon_url="https://horizon.stellar.org").load_account(MTLAddresses.public_defi)
    transaction = TransactionBuilder(source_account=root_account, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                     base_fee=base_fee)
    transaction.set_timeout(60 * 60 * 12)
    for account in accounts_list:
        if account[2] > 0.0001:
            transaction.append_payment_op(destination=account[0], asset=MTLAssets.satsmtl_asset,
                                          amount=str(round(account[2], 7)))
    transaction = transaction.build()
    xdr = transaction.to_xdr()

    return xdr


async def get_usdm_xdr(div_sum: int):
    accounts = await stellar_get_mtl_holders(MTLAssets.usdm_asset)
    accounts_list = []
    total_sum = 0

    for account in accounts:
        balances = account["balances"]
        token_balance = 0
        for balance in balances:
            if balance["asset_type"][0:15] == "credit_alphanum":
                if (balance["asset_code"] == MTLAssets.usdm_asset.code and
                        balance["asset_issuer"] == MTLAssets.usdm_asset.issuer):
                    token_balance = balance["balance"]
                    token_balance = int(token_balance[0:token_balance.find('.')])
        accounts_list.append([account["account_id"], token_balance, 0])
        total_sum += token_balance

    persent = div_sum / total_sum

    for account in accounts_list:
        account[2] = account[1] * persent

    root_account = Server(horizon_url="https://horizon.stellar.org").load_account(MTLAddresses.public_usdm)
    transaction = TransactionBuilder(source_account=root_account, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                     base_fee=base_fee)
    transaction.set_timeout(60 * 60 * 12)
    for account in accounts_list:
        if account[2] > 0.0001:
            transaction.append_payment_op(destination=account[0], asset=MTLAssets.usdm_asset,
                                          amount=str(round(account[2], 7)))
    transaction = transaction.build()
    xdr = transaction.to_xdr()

    return xdr


async def get_mtlbtc_xdr(btc_sum, address: str):
    root_account = Server(horizon_url="https://horizon.stellar.org").load_account(MTLAddresses.public_issuer)
    transaction = TransactionBuilder(source_account=root_account, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                     base_fee=base_fee)
    transaction.set_timeout(60 * 60 * 12)
    transaction.append_payment_op(destination=MTLAddresses.public_btc_guards, asset=MTLAssets.btcdebt_asset,
                                  amount=btc_sum)
    transaction.append_payment_op(destination=address, asset=MTLAssets.btcmtl_asset, amount=btc_sum)
    transaction = transaction.build()
    xdr = transaction.to_xdr()

    return xdr


async def cmd_show_data(account_id: str, filter_by: str = None, only_data: bool = False):
    result_data = []
    if account_id == 'delegate':
        # get all delegate
        vote_list = await cmd_gen_mtl_vote_list(return_delegate_list=True)
        for k, v in vote_list.items():
            result_data.append(f'{k} => {v}')
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


def decode_data_value(data_value: str):
    base64_message = data_value
    base64_bytes = base64_message.encode('ascii')
    message_bytes = base64.b64decode(base64_bytes)
    message = message_bytes.decode('ascii')
    return message


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


async def stellar_get_mtl_holders(asset=MTLAssets.mtl_asset, mini=False):
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


async def cmd_show_guards_list():
    account_json = await stellar_get_account(MTLAddresses.public_bod_eur)

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
                if balance["asset_code"] == "MTL" and balance["asset_issuer"] == MTLAddresses.public_issuer:
                    balance_mtl = balance["balance"]
                    balance_mtl = int(balance_mtl[0:balance_mtl.find('.')])
                if balance["asset_code"] == "MTLRECT" and balance["asset_issuer"] == MTLAddresses.public_issuer:
                    balance_rect = balance["balance"]
                    balance_rect = int(balance_rect[0:balance_rect.find('.')])
        lg = round(math.log2((balance_mtl + balance_rect + 0.001) / divider)) + 1
        if account["account_id"] != MTLAddresses.public_issuer:
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


def cmd_getblacklist():
    return requests.get('https://raw.githubusercontent.com/montelibero-org/mtl/main/json/blacklist.json').json()


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


def isfloat(value):
    try:
        float(value)
        return True
    except ValueError:
        return False


def gen_vote_xdr(public_key, vote_list, transaction=None, source=None, remove_master=False):
    # узнать кто в подписантах
    server = Server(horizon_url="https://horizon.stellar.org")
    source_account = server.load_account(public_key)

    sg = source_account.load_ed25519_public_key_signers()

    for s in sg:
        bfound = False
        for arr in vote_list:
            if arr[0] == s.account_id:
                arr[3] = s.weight
                bfound = True
        if (bfound == False) and (s.account_id != public_key):
            vote_list.append([s.account_id, 0, 0, s.weight])

    vote_list.sort(key=lambda k: k[2], reverse=True)

    # up user to delete
    tmp_list = []
    del_count = 0

    for arr in vote_list:
        if (int(arr[2]) == 0) & (int(arr[3]) > 0):
            tmp_list.append(arr)
            vote_list.remove(arr)
            del_count += 1

    tmp_list.extend(vote_list)

    while len(tmp_list) > 20 + del_count:
        arr = tmp_list.pop(20 + del_count)
        if arr[3] > 0:
            del_count += 1
            tmp_list.insert(0, [arr[0], 0, 0, arr[3]])

    vote_list = tmp_list
    # 5
    server = Server(horizon_url="https://horizon.stellar.org")
    source_account = server.load_account(public_key)
    root_account = Account(public_key, sequence=source_account.sequence)
    if transaction is None:
        transaction = TransactionBuilder(source_account=root_account,
                                         network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE, base_fee=base_fee)
        transaction.set_timeout(60 * 60 * 48)
    threshold = 0

    for arr in vote_list:
        if int(arr[2]) != int(arr[3]):
            transaction.append_ed25519_public_key_signer(arr[0], int(arr[2]), source=source)
        threshold += int(arr[2])

    threshold = threshold // 2 + 1

    if remove_master:
        transaction.append_set_options_op(low_threshold=threshold, med_threshold=threshold, high_threshold=threshold,
                                          source=source, master_weight=0)
    else:
        transaction.append_set_options_op(low_threshold=threshold, med_threshold=threshold, high_threshold=threshold,
                                          source=source)

    transaction = transaction.build()
    xdr = transaction.to_xdr()
    # print(f"xdr: {xdr}")

    return xdr


def cmd_check_new_transaction(session: requests.Session, ignore_operation: List, value_id=None,
                              stellar_address=MTLAddresses.public_issuer):
    result = []
    last_id = cmd_load_bot_value(session, 0, value_id)
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
        if 0 < len(tr) < 90:
            link = f'https://stellar.expert/explorer/public/tx/{transaction["paging_token"]}'
            tr = decode_xdr(transaction["envelope_xdr"])
            tr.insert(0, f'(<a href="{link}">expert link</a>)')
            result.append(tr)
        # print(decode_xdr(transaction["envelope_xdr"]))
        # print('****')
        # print(transaction["paging_token"])

    cmd_save_bot_value(session, 0, value_id, last_id)

    return result


def cmd_check_new_asset_transaction(session: Session, asset_name: str, save_id: int, filter_sum: int = -1,
                                    filter_operation=None, issuer=MTLAddresses.public_issuer, filter_asset=None):
    if filter_operation is None:
        filter_operation = []
    result = []

    last_id = cmd_load_bot_value(session, 0, save_id, '0')
    max_id = last_id

    data = get_new_effects_for_token(session, asset_name, last_id, filter_sum)
    for row in data:
        result.append(decode_db_effect(row))
        max_id = row.id

    if max_id > last_id:
        cmd_save_bot_value(session, 0, save_id, max_id)

    return result


def decode_db_effect(row: TOperations):
    result = f'<a href="https://stellar.expert/explorer/public/op/{row.id.split("-")[0]}">' \
             f'Операция</a> с аккаунта {address_id_to_username(row.for_account)} \n'
    if row.operation == 'trade':
        result += f'  {row.operation}  {float2str(row.amount1)} {row.code1} for {float2str(row.amount2)} {row.code2} \n'
    else:
        result += f'  {row.operation} for {float2str(row.amount1)} {row.code1} \n'
    return result


def cmd_check_last_operation(address: str, filter_operation=None) -> datetime:
    operations = Server(horizon_url="https://horizon.stellar.org").operations().for_account(address).order().limit(
        1).call()
    op = operations['_embedded']['records'][0]
    # print(operation["created_at"])  # 2022-08-23T13:47:33Z
    dt = datetime.strptime(op["created_at"], '%Y-%m-%dT%H:%M:%SZ')
    # print(dt)

    return dt


def get_memo_by_op(op: str):
    operation = Server(horizon_url="https://horizon.stellar.org").operations().operation(op).call()
    transaction = Server(horizon_url="https://horizon.stellar.org").transactions().transaction(
        operation['transaction_hash']).call()
    return transaction.get('memo', 'None')


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


async def stellar_add_mtl_holders_info(accounts: dict):
    async with ServerAsync(
            horizon_url="https://horizon.stellar.org", client=AiohttpClient()
    ) as server:
        source_account = await server.load_account(MTLAddresses.public_issuer)
        sg = source_account.load_ed25519_public_key_signers()

    for s in sg:
        for arr in accounts:
            if arr[0] == s.account_id:
                arr[3] = s.weight

    return accounts


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
                        result.append(MTLAssets.xlm_asset)
                    else:
                        result.append(Asset(record['asset_code'],
                                            record['asset_issuer']))
                return result
        else:
            return []
    except Exception as ex:
        logger.exception(["stellar_check_receive_sum", send_asset.code + ' ' + send_sum + ' ' + receive_asset.code, ex])
        return []


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
