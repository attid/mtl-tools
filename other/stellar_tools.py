import asyncio
import base64
import math
import re
from copy import deepcopy
from datetime import datetime, timedelta
from decimal import Decimal
from time import time
from typing import List, Optional
import aiohttp
import requests
from aiogram import Bot
from aiogram.types import Message
from loguru import logger
from sqlalchemy.orm import Session
from stellar_sdk import (Account, Asset, Claimant, ClaimPredicate, FeeBumpTransactionEnvelope, Keypair, Network, Price,
                         Server, TextMemo, TransactionBuilder, TransactionEnvelope)
from stellar_sdk.client.aiohttp_client import AiohttpClient
from stellar_sdk.server_async import ServerAsync
from stellar_sdk.sep.federation import resolve_account_id_async

from db.models import TDivList, TOperations, TPayments, TTransaction
from db.requests import (cmd_load_transactions, db_count_unpacked_payments, db_count_unsent_transactions,
                         db_get_div_list, db_get_new_effects_for_token, db_get_operations_by_asset, db_get_payments,
                         db_get_total_user_div, db_get_user_id)
from other.config_reader import config
from other.global_data import float2str, global_data, MTLChats
from other.grist_tools import MTLGrist, grist_manager
from other.gspread_tools import agcm, gs_get_chicago_premium
from other.mytypes import MyShareHolder
from other.web_tools import get_eurmtl_xdr

base_fee = config.base_fee


class MTLAddresses:
    public_issuer = "GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V"
    public_pawnshop = "GDASYWP6F44TVNJKZKQ2UEVZOKTENCJFTWVMP6UC7JBZGY4ZNB6YAVD4"
    public_farm = "GCAQ3NPOLUPDBN7M32DHGKQPVCNIZ3KQFN6UXPZDPRLRUYJATNQ4FARM"
    public_btc_guards = "GATUN5FV3QF35ZMU3C63UZ63GOFRYUHXV2SHKNTKPBZGYF2DU3B7IW6Z"
    public_fund_city = "GCOJHUKGHI6IATN7AIEK4PSNBPXIAIZ7KB2AWTTUCNIAYVPUB2DMCITY"
    public_fund_defi = "GAEZHXMFRW2MWLWCXSBNZNUSE6SN3ODZDDOMPFH3JPMJXN4DKBPMDEFI"
    public_fund_mabiz = "GAQ5ERJVI6IW5UVNPEVXUUVMXH3GCDHJ4BJAXMAAKPR5VBWWAUOMABIZ"
    public_usdm = "GDHDC4GBNPMENZAOBB4NCQ25TGZPDRK6ZGWUGSI22TVFATOLRPSUUSDM"
    public_fin = "GCSAXEHZBQY65URLO6YYDOCTRLIGTNMGCQHVW2RZPFNPTEJN6VN7TFIN"
    public_tfm = "GDOJK7UAUMQX5IZERYPNBPQYQ3SHPKGLF5MBUKWLDL2UV2AY6BIS3TFM"
    public_mtla = "GCNVDZIHGX473FEI7IXCUAEXUJ4BGCKEMHF36VYP5EMS7PX2QBLAMTLA"
    # bot
    public_bod_eur = "GDEK5KGFA3WCG3F2MLSXFGLR4T4M6W6BMGWY6FBDSDQM6HXFMRSTEWBW"
    public_bod = "GARUNHJH3U5LCO573JSZU4IOBEVQL6OJAAPISN4JKBG2IYUGLLVPX5OH"
    public_div = "GDNHQWZRZDZZBARNOH6VFFXMN6LBUNZTZHOKBUT7GREOWBTZI4FGS7IQ"
    public_usdm_div = "GDAA7YDU6O7F27XUOSU27IHDDHE2XX7CRP427AA73VIJVZQ447E5UDIV"
    public_key_rate = "GDGGHSIA62WGNMN2VOIBW3X66ATOBW5J2FU7CSJZ6XVHI2ZOXZCRRATE"
    public_sign = "GDCGYX7AXIN3EWIBFZ3AMMZU4IUWS4CIZ7Z7VX76WVOIJORCKDDRSIGN"
    public_fire = "GD44EAUQXNUVBJACZMW6GPT2GZ7I26EDQCU5HGKUTVEQTXIDEVGUFIRE"
    public_adm = "GBSCMGJCE4DLQ6TYRNUMXUZZUXGZBM4BXVZUIHBBL5CSRRW2GWEHUADM"
    public_boss = "GC72CB75VWW7CLGXS76FGN3CC5K7EELDAQCPXYMZLNMOTC42U3XJBOSS"
    public_council = "GC3ESR3LZGIDKYG5FFJWKYRR2324PRLUGTJMYCF7L2UG6FS4N6NWCOUN"

    public_exchange_eurmtl_xlm = "GDEMWIXGF3QQE7CJIOKWWMJAXAWGINJRR6DOOOSNO3C4UQGPDOA3OBOT"
    public_exchange_usdm_mtlfarm = "GDBCVYPF2MYMZDHO7HRUG24LZ3UUGROX3WVWSNVZF7Q5B3NBZ2NYVBOT"
    public_exchange_usdm_sats = "GAEO4HE7DJAJPOEE4KU375WEGB2IWO42KVTG3PLBTXL7TSWDSPHPZBOT"
    public_exchange_eurmtl_usdm = "GBQZDXEBW5DGNOSRUPIWUTIYTO7QM65NOU5VHAAACED4HII7FVXPCBOT"
    public_exchange_usdm_usdc = "GDFBQS4TSDNSVGSR62VYGQAJHYKC3K3WIPBKMODNU6J3DKMSKMN3GBOT"
    public_exchange_mtl_xlm = "GDLIKJG7G3DDGK53TCWMXIEJF3D2U4MBUGINZJFPLHI2JLJBNBE3GBOT"
    public_exchange_usdm_xlm = "GARRQAITJSDKJ7QXVHTHGQX4FMQRJJBQ5ZXKZK57AVIMHMPS5FDRZBOT"
    public_exchange_eurmtl_eurc = "GAEMIYH3JPPL54IMXFF42R7T7BTGA25Z5TY3QOBNACFLXATDO2RDXBOT"
    public_exchange_pool = "GCWJOBIPJQRZLFGQ5RQKE4J3H2QXHAOHCFVDM3FH37APAM3QXQR7POOL"

    # user
    public_itolstov = "GDLTH4KKMA4R2JGKA7XKI5DLHJBUT42D5RHVK6SS6YHZZLHVLCWJAYXI"
    public_pending = "GB72L53HPZ2MNZQY4XEXULRD6AHYLK4CO55YTOBZUEORW2ZTSOEQ4MTL"
    public_wallet = "GBSNN2SPYZB2A5RPDTO3BLX4TP5KNYI7UMUABUS3TYWWEWAAM2D7CMMW"
    public_seregan = "GBVIX6CZ57SHXHGPA4AL7DACNNZX4I2LCKIAA3VQUOGTGWYQYVYSE5TU"
    public_damir = "GAUJWORZF3ROOQ2XLYY7ZINSXZ5IVSUSSKAOOEV7QNLWZBVVLSDQBDF2"


class MTLAssets:
    mtl_asset = Asset("MTL", MTLAddresses.public_issuer)
    mtlrect_asset = Asset("MTLRECT", MTLAddresses.public_issuer)
    eurmtl_asset = Asset("EURMTL", MTLAddresses.public_issuer)
    eurdebt_asset = Asset("EURDEBT", MTLAddresses.public_issuer)
    xlm_asset = Asset("XLM", None)
    satsmtl_asset = Asset("SATSMTL", MTLAddresses.public_issuer)
    btcmtl_asset = Asset("BTCMTL", MTLAddresses.public_issuer)
    btcdebt_asset = Asset("BTCDEBT", MTLAddresses.public_issuer)
    usdc_asset = Asset("USDC", "GA5ZSEJYB37JRC5AVCIA5MOP4RHTM335X2KGX3IHOJAPP5RE34K4KZVN")
    yusdc_asset = Asset("yUSDC", "GDGTVWSM4MGS4T7Z6W4RPWOCHE2I6RDFCIFZGS3DOA63LWQTRNZNTTFF")
    btc_asset = Asset("BTC", "GDPJALI4AZKUU2W426U5WKMAT6CN3AJRPIIRYR2YM54TL2GDWO5O2MZM")
    ybtc_asset = Asset("yBTC", "GBUVRNH4RW4VLHP4C5MOF46RRIRZLAVHYGX45MVSTKA2F6TMR7E7L6NW")
    mrxpinvest_asset = Asset("MrxpInvest", 'GDAJVYFMWNIKYM42M6NG3BLNYXC3GE3WMEZJWTSYH64JLZGWVJPTGGB7')
    mtlfarm_asset = Asset("MTLFARM", MTLAddresses.public_farm)
    usd_farm_asset = Asset("USDFARM", MTLAddresses.public_farm)
    usdmm_asset = Asset("USDMM", MTLAddresses.public_usdm)
    usdm_asset = Asset("USDM", MTLAddresses.public_usdm)
    damircoin_asset = Asset("DamirCoin", MTLAddresses.public_damir)
    agora_asset = Asset("Agora", 'GBGGX7QD3JCPFKOJTLBRAFU3SIME3WSNDXETWI63EDCORLBB6HIP2CRR')
    toc_asset = Asset("TOC", 'GBJ3HT6EDPWOUS3CUSIJW5A4M7ASIKNW4WFTLG76AAT5IE6VGVN47TIC')
    aqua_asset = Asset("AQUA", 'GBNZILSTVQZ4R7IKQDGHYGY2QXL5QOFJYQMXPKWRRM5PAV7Y4M67AQUA')
    mtlap_asset = Asset("MTLAP", 'GCNVDZIHGX473FEI7IXCUAEXUJ4BGCKEMHF36VYP5EMS7PX2QBLAMTLA')
    eurc_asset = Asset("EURC", 'GAQRF3UGHBT6JYQZ7YSUYCIYWAF4T2SAA5237Q5LIQYJOHHFAWDXZ7NM')


pack_count = 70  # for select first pack_count - to pack to xdr

exchange_bots = ()


# exchange_bots = ()(MTLAddresses.public_exchange_eurmtl_xlm, MTLAddresses.public_exchange_usdm_mtlfarm,
#                  MTLAddresses.public_exchange_eurmtl_usdm, MTLAddresses.public_fire,
#                  MTLAddresses.public_exchange_usdm_sats)


async def check_url_xdr(url, full_data=True):
    xdr = await get_eurmtl_xdr(url)
    return await decode_xdr(xdr, full_data=full_data)


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


async def decode_xdr(xdr, filter_sum: int = -1, filter_operation=None, ignore_operation=None, filter_asset=None,
                     full_data=False):
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
    result.append(
        f"Операции с аккаунта {await address_id_to_username(transaction.transaction.source.account_id, full_data=full_data)}")
    if transaction.transaction.memo.__class__ == TextMemo:
        memo = transaction.transaction.memo
        result.append(f'  Memo "{memo.memo_text.decode()}"\n')
    result.append(f"  Всего {len(transaction.transaction.operations)} операций\n")

    for idx, operation in enumerate(transaction.transaction.operations):
        result.append(f"Операция {idx} - {type(operation).__name__}")
        # print('bad xdr', idx, operation)
        if operation.source:
            result.append(
                f"*** для аккаунта {await address_id_to_username(operation.source.account_id, full_data=full_data)}")
        if good_operation(operation, "Payment", filter_operation, ignore_operation):
            if 'SPAM' in ignore_operation and operation.asset.code == 'XLM' and operation.amount < '0.1':
                continue
            if float(operation.amount) > filter_sum:
                if (filter_asset is None) or (operation.asset == filter_asset):
                    data_exist = True
                    result.append(
                        f"    Перевод {operation.amount} {operation.asset.code} на аккаунт {await address_id_to_username(operation.destination.account_id, full_data=full_data)}")
            continue
        if good_operation(operation, "SetOptions", filter_operation, ignore_operation):
            data_exist = True
            if operation.signer:
                result.append(
                    f"    Изменяем подписанта {await address_id_to_username(operation.signer.signer_key.encoded_signer_key, full_data=full_data)} новые голоса : {operation.signer.weight}")
            if operation.med_threshold:
                data_exist = True
                result.append(f"Установка нового требования. Нужно будет {operation.med_threshold} голосов")
            if operation.home_domain:
                data_exist = True
                result.append(f"Установка нового домена {operation.home_domain}")
            continue
        if good_operation(operation, "ChangeTrust", filter_operation, ignore_operation):
            data_exist = True
            if operation.asset.type == 'liquidity_pool_shares':
                if operation.limit == '0':
                    result.append(
                        f"    Закрываем линию доверия к пулу {operation.asset.asset_a.code}/{operation.asset.asset_b.code}")
                else:
                    result.append(
                        f"    Открываем линию доверия к пулу {operation.asset.asset_a.code}/{operation.asset.asset_b.code}")
            else:
                if operation.limit == '0':
                    result.append(
                        f"    Закрываем линию доверия к токену {operation.asset.code} от аккаунта {await address_id_to_username(operation.asset.issuer, full_data=full_data)}")
                else:
                    result.append(
                        f"    Открываем линию доверия к токену {operation.asset.code} от аккаунта {await address_id_to_username(operation.asset.issuer, full_data=full_data)}")

            continue
        if good_operation(operation, "CreateClaimableBalance", filter_operation, ignore_operation):
            data_exist = True
            result.append(f"  Спам {operation.asset.code}")
            result.append("  Остальные операции игнорируются.")
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
                        f"    Покупка {await address_id_to_username(operation.destination.account_id, full_data=full_data)}, шлем {operation.send_asset.code} {operation.send_amount} в обмен на {operation.dest_asset.code} min {operation.dest_min} ")
            continue
        if good_operation(operation, "PathPaymentStrictReceive", filter_operation, ignore_operation):
            if (float(operation.send_max) > filter_sum) and (float(operation.dest_amount) > filter_sum):
                if (filter_asset is None) or (filter_asset in [operation.send_asset, operation.dest_asset]):
                    data_exist = True
                    result.append(
                        f"    Продажа {await address_id_to_username(operation.destination.account_id, full_data=full_data)}, Получаем {operation.send_asset.code} max {operation.send_max} в обмен на {operation.dest_asset.code} {operation.dest_amount} ")
            continue
        if good_operation(operation, "ManageData", filter_operation, ignore_operation):
            data_exist = True
            result.append(
                f"    ManageData {operation.data_name} = {operation.data_value} ")
            continue
        if good_operation(operation, "SetTrustLineFlags", filter_operation, ignore_operation):
            data_exist = True
            result.append(
                f"    Trustor {await address_id_to_username(operation.trustor, full_data=full_data)} for asset {operation.asset.code}")
            if operation.clear_flags is not None:
                result.append(f"    Clear flags: {operation.clear_flags}")
            if operation.set_flags is not None:
                result.append(f"    Set flags: {operation.set_flags}")
            continue
        if good_operation(operation, "CreateAccount", filter_operation, ignore_operation):
            data_exist = True
            result.append(
                f"    Создание аккаунта {await address_id_to_username(operation.destination, full_data=full_data)} с суммой {operation.starting_balance} XLM")
            continue
        if good_operation(operation, "AccountMerge", filter_operation, ignore_operation):
            data_exist = True
            result.append(
                f"    Слияние аккаунта c {await address_id_to_username(operation.destination.account_id, full_data=full_data)} ")
            continue
        if good_operation(operation, "ClaimClaimableBalance", filter_operation, ignore_operation):
            data_exist = True
            result.append(
                f"    ClaimClaimableBalance {await address_id_to_username(operation.balance_id, full_data=full_data)}")
            continue
        if good_operation(operation, "BeginSponsoringFutureReserves", filter_operation, ignore_operation):
            data_exist = True
            result.append(
                f"    BeginSponsoringFutureReserves {await address_id_to_username(operation.sponsored_id, full_data=full_data)}")
            continue
        if good_operation(operation, "EndSponsoringFutureReserves", filter_operation, ignore_operation):
            data_exist = True
            result.append("    EndSponsoringFutureReserves")
            continue
        if type(operation).__name__ == "Clawback":
            data_exist = True
            result.append(
                f"    Возврат {operation.amount} {operation.asset.code} с аккаунта {await address_id_to_username(operation.from_.account_id)}")
            continue
        if type(operation).__name__ == "LiquidityPoolDeposit":
            data_exist = True
            min_price = operation.min_price.n / operation.min_price.d
            max_price = operation.max_price.n / operation.max_price.d
            result.append(
                f"    LiquidityPoolDeposit {operation.liquidity_pool_id} пополнение {operation.max_amount_a}/{operation.max_amount_b} ограничения цены {min_price}/{max_price}")
            continue
        if type(operation).__name__ == "LiquidityPoolWithdraw":
            data_exist = True
            result.append(
                f"    LiquidityPoolWithdraw {operation.liquidity_pool_id} вывод {operation.amount} минимум {operation.min_amount_a}/{operation.min_amount_b} ")
            continue

        if type(operation).__name__ in ["PathPaymentStrictSend", "ManageBuyOffer", "ManageSellOffer", "AccountMerge",
                                        "PathPaymentStrictReceive", "ClaimClaimableBalance", "CreateAccount",
                                        "CreateClaimableBalance", "ChangeTrust", "SetOptions", "Payment", "ManageData",
                                        "BeginSponsoringFutureReserves", "EndSponsoringFutureReserves",
                                        "CreatePassiveSellOffer"]:
            continue

        data_exist = True
        result.append("Прости хозяин, не понимаю")
        logger.info(['bad xdr', idx, operation])
    if data_exist:
        return result
    else:
        return []


async def address_id_to_username(key, full_data=False) -> str:
    if full_data:
        # cash
        if key in global_data.name_list:
            return global_data.name_list[key]

        # mtla
        user = await grist_manager.load_table_data(
            MTLGrist.MTLA_USERS,
            filter_dict={"Stellar": [key]}
        )
        if user:
            global_data.name_list[key] = user[0]["Telegram"]
            return global_data.name_list[key]

        # eurmtl users
        user = await grist_manager.load_table_data(
            MTLGrist.EURMTL_users,
            filter_dict={"account_id": [key]}
        )
        if user:
            global_data.name_list[key] = user[0]["username"]
            return global_data.name_list[key]

        # eurmtl accounts
        user = await grist_manager.load_table_data(
            MTLGrist.EURMTL_accounts,
            filter_dict={"account_id": [key]}
        )
        if user:
            global_data.name_list[key] = user[0]["description"]
            return global_data.name_list[key]

        # eurmtl assets
        user = await grist_manager.load_table_data(
            MTLGrist.EURMTL_assets,
            filter_dict={"issuer": [key]}
        )
        if user:
            global_data.name_list[key] = 'Issuer of ' + user[0]["code"]
            return global_data.name_list[key]

        return key[:4] + '..' + key[-4:] + ' не найден, возможно скам'

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
                chat_id = db_get_user_id(session, user)
                await bot.send_message(chat_id=chat_id, text=msg)
                good_users.append(user)
            except Exception as ex:
                bad_users.append(user)
                logger.info(ex)
                pass
    await message.reply(f'was send to {" ".join(good_users)} \n can`t send to {" ".join(bad_users)}')


def cmd_check_fee() -> str:
    fee = Server(horizon_url=config.horizon_url).fee_stats().call()["fee_charged"]
    return fee['min'] + '-' + fee['max']
    # print(Server(horizon_url=config.horizon_url).fetch_base_fee())


async def stellar_get_account(account_id) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{config.horizon_url}/accounts/{account_id}') as resp:
            # print(resp.status)
            # print(await resp.text())
            return await resp.json()


async def stellar_get_issuer_assets(account_id) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{config.horizon_url}/assets?limit=200&asset_issuer={account_id}') as resp:
            data = await resp.json()
            # print(data)  # 'liquidity_pools_amount': '1807570.6061503',
            assets = {}
            if assets.get('type'):
                return {}
            else:
                for balance in data['_embedded']['records']:
                    balances = balance['balances']
                    assets[balance['asset_code']] = (
                            float(balances['authorized']) +
                            float(balance.get('claimable_balances_amount', 0)) +
                            float(balance.get('liquidity_pools_amount', 0)))
                return assets


async def get_balances(address: str, return_assets=False, return_data=False, return_signers=False, account_json=None):
    if account_json:
        account = account_json
    else:
        account = await stellar_get_account(address)

    assets = {}
    if account.get('type'):
        return {}
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


async def get_pool_info(pool_id: str, session) -> dict:
    async with session.get(f'{config.horizon_url}/liquidity_pools/{pool_id}') as resp:
        return await resp.json()


async def get_pool_balances(address: str) -> list:
    """
    Получает информацию о пулах ликвидности для заданного адреса

    Args:
        address (str): Stellar адрес аккаунта

    Returns:
        dict: Словарь с информацией о пулах в формате:
        {
            pool_id: {
                'name': 'TOKEN1-TOKEN2',
                'shares': float,
                'token1_amount': float,
                'token2_amount': float
            }
        }
    """

    account = await stellar_get_account(address)
    pools = []

    async with aiohttp.ClientSession() as session:
        for balance in account['balances']:
            if balance['asset_type'] == 'liquidity_pool_shares':
                pool_id = balance['liquidity_pool_id']
                user_shares = float(balance['balance'])

                # Получаем детальную информацию о пуле
                pool_info = await get_pool_info(pool_id, session)
                total_shares = float(pool_info['total_shares'])

                # Вычисляем долю пользователя
                user_share_percentage = user_shares / total_shares

                # Извлекаем информацию о резервах
                reserves = pool_info['reserves']
                token1 = reserves[0]
                token2 = reserves[1]

                # Вычисляем токены пользователя
                user_token1_amount = float(token1['amount']) * user_share_percentage
                user_token2_amount = float(token2['amount']) * user_share_percentage
                # Формируем название пула
                token1_code = token1['asset'].split(':')[0]
                token2_code = token2['asset'].split(':')[0]
                pool_name = f"{token1_code}-{token2_code}"

                pools.append({
                    'pool_id': pool_id,
                    'name': pool_name,
                    'shares': user_shares,
                    'token1_amount': user_token1_amount,
                    'token2_amount': user_token2_amount
                })

    return pools


async def stellar_get_offers(account_id: str):
    async with ServerAsync(
            horizon_url=config.horizon_url, client=AiohttpClient()
    ) as server:
        call = await server.offers().for_account(account_id).limit(200).call()
        return call['_embedded']['records']


async def stellar_get_orders_sum(address, selling_asset, buying_asset) -> float:
    orders = await stellar_get_offers(address)
    total_amount = 0.0

    for order in orders:
        if (order['selling']['asset_type'] == selling_asset.type and
                order['buying']['asset_type'] == buying_asset.type and
                order['selling']['asset_code'] == selling_asset.code and
                order['selling']['asset_issuer'] == selling_asset.issuer and
                order['buying']['asset_code'] == buying_asset.code and
                order['buying']['asset_issuer'] == buying_asset.issuer):
            total_amount += float(order['amount'])

    return total_amount


async def get_asset_swap_spread(selling_asset: Asset, buying_asset: Asset, amount: float = 1):
    """
    Возвращает спред обмена между двумя ассетами для заданного количества ассета для продажи и покупки.
    :param selling_asset: Asset, который продается.
    :param buying_asset: Asset, который покупается.
    :param amount: Количество ассета для продажи.
    :return: Кортеж из двух значений (количество, получаемое при продаже, количество, необходимое для покупки).
    """
    async with ServerAsync(
            horizon_url=config.horizon_url, client=AiohttpClient()
    ) as server:
        sell_to_buy = await server.strict_send_paths(source_asset=selling_asset, source_amount=str(amount),
                                                     destination=[buying_asset]).limit(1).call()
        # print(sell_to_buy['_embedded']['records'])
        destination_amount_sell_to_buy = float(sell_to_buy['_embedded']['records'][0]['destination_amount']) if \
            sell_to_buy['_embedded']['records'] else 0

        # Определяем кол-во отправляемого ассета для покупки указанного кол-ва другого ассета
        # buy_to_sell = server.strict_receive_paths(source=[selling_asset], destination_asset=buying_asset, destination_amount=amount).limit(1).call()
        buy_to_sell = await server.strict_send_paths(source_asset=buying_asset, source_amount=str(1 / amount),
                                                     destination=[selling_asset]).limit(1).call()
        # print(buy_to_sell['_embedded']['records'])
        source_amount_buy_to_sell = 1 / float(buy_to_sell['_embedded']['records'][0]['destination_amount']) if \
            buy_to_sell['_embedded']['records'] else 0

        average = 0 if destination_amount_sell_to_buy == 0 or source_amount_buy_to_sell == 0 else round(
            (destination_amount_sell_to_buy + source_amount_buy_to_sell) / 2, 5)

        return destination_amount_sell_to_buy, source_amount_buy_to_sell, average


def get_private_sign():
    return config.private_sign.get_secret_value()


def stellar_stop_all_exchange():
    xdr = None
    for bot in exchange_bots:
        xdr = stellar_remove_orders(bot, xdr)
    stellar_sync_submit(stellar_sign(xdr, config.private_sign.get_secret_value()))


def stellar_sign(xdr, sign_key=None):
    if sign_key is None:
        sign_key = config.private_sign.get_secret_value()
    transaction = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
    transaction.sign(sign_key)
    return transaction.to_xdr()


def stellar_sync_submit(xdr: str):
    with Server(
            horizon_url=config.horizon_url
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
        rq = requests.get(f'{config.horizon_url}/accounts/{address}').json()
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

    total_sum = db_get_total_user_div(session)

    result += f'Всего {len(bod_list)} участников'
    result += f'\n{len(good)} участников c доступом к EURMTL'
    result += f'\nЧерез систему за всю историю выплачено {round(total_sum, 2)} EURMTL'

    balances = {}
    rq = requests.get(f'{config.horizon_url}/accounts/{MTLAddresses.public_bod_eur}').json()
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
    line = '============================\n'
    result = line
    result += '|Кубышка |Наличных| EURMTL |\n'

    treasure_list = await grist_manager.load_table_data(MTLGrist.NOTIFY_TREASURY, sort='order')

    t = """
    ==============================
    |Кубышка | Наличных | EURMTL |
    |Игоря   |      500 |  49500 |
    =========================+====
    |Итого в !     23749! 111535 !
    ========================+=====
    """

    for treasure in treasure_list:
        if len(treasure['account_id']) == 56:
            if not treasure['enabled']:
                continue
            assets = await get_balances(treasure['account_id'])
            diff = int(assets['EURDEBT']) - int(assets['EURMTL'])
            name = treasure['name'] if chat_id == MTLChats.GuarantorGroup else treasure['name'][0]
            s_cash = f'{diff} '.rjust(8)
            s_eurmtl = f'{int(assets["EURMTL"])} '.rjust(8)
            result += f"|{name.ljust(8)}|{s_cash}|{s_eurmtl}|\n"
            total_cash += diff
            total_eurmtl += int(assets['EURMTL'])
        else:
            result += line

    assets = await get_balances('GBQZDXEBW5DGNOSRUPIWUTIYTO7QM65NOU5VHAAACED4HII7FVXPCBOT')
    # result += f"А у Skynet {int(assets['USDM'])} USDC и {int(assets['EURMTL'])} EURMTL \n"
    s_cash = f'*{int(assets["USDM"])} '.rjust(8)
    s_eurmtl = f'{int(assets["EURMTL"])} '.rjust(8)
    result += f"|{'SkyNet'.ljust(8)}|{s_cash}|{s_eurmtl}|\n"

    result += line
    s_cash = f'{total_cash} '.rjust(8)
    s_eurmtl = f'{total_eurmtl} '.rjust(8)
    result += f"|{'Итого'.ljust(8)}|{s_cash}|{s_eurmtl}|\n"

    result += line

    return result


def cmd_create_list(session: Session, memo: str, pay_type: int):
    new = TDivList(memo=memo, pay_type=pay_type)
    session.add(new)
    session.commit()
    return new.id


async def cmd_calc_bim_pays(session: Session, list_id: int, test_sum=0):
    if test_sum > 0:
        div_sum = test_sum
    else:
        div_sum = await get_balances(MTLAddresses.public_bod_eur)
        div_sum = int(float(div_sum['EURMTL']) / 2)  # 50%
        logger.info(f'div_sum = {div_sum}')

    accounts = await stellar_get_holders(MTLAssets.mtlap_asset)

    secretary = 'GDGC46H4MQKRW3TZTNCWUU6R2C7IPXGN7HQLZBJTNQO6TW7ZOS6MSECR'

    valid_accounts = [account for account in accounts if
                      account['account_id'] != secretary and
                      (await get_balances(account['account_id'], account_json=account)).get('EURMTL') is not None]
    one_mtlap_accounts = [account for account in valid_accounts if
                          1 <= (await get_balances(account['account_id'], account_json=account))['MTLAP'] < 2]
    two_or_more_mtlap_accounts = [account for account in valid_accounts if
                                  (await get_balances(account['account_id'], account_json=account))['MTLAP'] >= 2]

    amount_for_one_mtlap_accounts = int(div_sum * 0.2)
    amount_for_two_or_more_mtlap_accounts = int(div_sum * 0.8)

    sdiv_one_mtlap = int(
        amount_for_one_mtlap_accounts / len(one_mtlap_accounts) * 100) / 100 if one_mtlap_accounts else 0
    sdiv_two_mtlap = int(amount_for_two_or_more_mtlap_accounts / len(
        two_or_more_mtlap_accounts) * 100) / 100 if two_or_more_mtlap_accounts else 0

    mtl_accounts = []
    for account in valid_accounts:
        balances = await get_balances(account['account_id'], account_json=account)
        bls = balances['EURMTL']
        if account in two_or_more_mtlap_accounts:
            div = sdiv_two_mtlap
        elif account in one_mtlap_accounts:
            div = sdiv_one_mtlap
        else:
            div = 0
        mtl_accounts.append([account['account_id'], bls, div, div, list_id])

    mtl_accounts.sort(key=lambda x: x[0], reverse=True)
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
    div_list = db_get_div_list(session, list_id)
    memo = div_list.memo
    pay_type = div_list.pay_type
    server = Server(horizon_url=config.horizon_url)
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

    if pay_type == 5:
        div_account = server.load_account(MTLAddresses.public_div)
        asset = MTLAssets.usdm_asset

    if pay_type == 6:
        div_account = server.load_account(MTLAddresses.public_usdm_div)
        asset = MTLAssets.usdm_asset

    transaction = TransactionBuilder(source_account=div_account, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                     base_fee=base_fee)
    transaction.set_timeout(60 * 60 * 24 * 7)

    for payment in db_get_payments(session, list_id, pack_count):
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
    need = db_count_unpacked_payments(session, list_id)
    # print(f'need {need} more')
    return need


async def cmd_send_by_list_id(session: Session, list_id: int):
    # records = fb.execsql(f"select first 3 t.id, t.xdr from t_transaction t where t.was_send = 0 and t.id_div_list = ?",
    #                     [list_id])

    for db_transaction in cmd_load_transactions(session, list_id):
        transaction = TransactionEnvelope.from_xdr(db_transaction.xdr,
                                                   network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
        server = Server(horizon_url=config.horizon_url)
        div_account = server.load_account(transaction.transaction.source.account_id)
        sequence = div_account.sequence + 1
        transaction.transaction.sequence = sequence
        transaction.sign(config.private_sign.get_secret_value())
        transaction_resp = await stellar_async_submit(transaction.to_xdr())
        logger.info(transaction_resp)
        db_transaction.was_send = 1
        db_transaction.xdr_id = sequence
    session.commit()

    return db_count_unsent_transactions(session, list_id)


async def stellar_async_submit(xdr: str):
    async with ServerAsync(
            horizon_url=config.horizon_url, client=AiohttpClient()
    ) as server:
        transaction = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
        transaction_resp = await server.submit_transaction(transaction)
        # return json.dumps(resp, indent=2)
        return transaction_resp


async def cmd_calc_divs(session: Session, div_list_id: int, donate_list_id: int, test_sum=0):
    div_accounts = []
    donates = []

    # Получаем все аккаунты с MTL
    accounts = await stellar_get_all_mtl_holders()

    # Считаем общую сумму MTL и MTLRECT
    mtl_sum = 0.0
    for account in accounts:
        balances = account["balances"]
        for balance in balances:
            if balance["asset_type"][0:15] == "credit_alphanum":
                if balance["asset_issuer"] == MTLAddresses.public_issuer:
                    if balance["asset_code"] == "MTL":
                        mtl_sum += float(balance["balance"])
                    elif balance["asset_code"] == "MTLRECT":
                        mtl_sum += float(balance["balance"])

    # Определяем сумму для распределения
    if test_sum > 0:
        div_sum = test_sum
    else:
        div_sum = await get_balances(MTLAddresses.public_div)
        div_sum = float(div_sum['EURMTL']) - 0.1
        logger.info(f'div_sum = {div_sum}')
        await stellar_async_submit(
            stellar_sign(
                cmd_gen_data_xdr(MTLAddresses.public_div, f'LAST_DIVS:{div_sum}'),
                config.private_sign.get_secret_value()
            )
        )

    # Обрабатываем каждый аккаунт
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
                if balance["asset_issuer"] == MTLAddresses.public_issuer:
                    if balance["asset_code"] == "MTL":
                        balance_mtl = round(float(balance["balance"]), 7)
                    elif balance["asset_code"] == "MTLRECT":
                        balance_rect = round(float(balance["balance"]), 7)
                    elif balance["asset_code"] == "EURMTL":
                        eur = 1

        total_balance = balance_mtl + balance_rect
        div = round(div_sum / mtl_sum * total_balance, 7)
        donates.extend(get_donate_list(account))

        if (eur > 0) and (div > 0.0001) and \
                (account["account_id"] not in [MTLAddresses.public_issuer, MTLAddresses.public_pawnshop]):
            div_accounts.append([account["account_id"], total_balance, div, div, div_list_id])

    # calc donate # ['GCPOWDQQDVSAQGJXZW3EWPPJ5JCF4KTTHBYNB4U54AKQVDLZXLLYMXY7', 56428.7, 120.9, 96.7, 26]
    donate_list = []
    for mtl_account in div_accounts:
        found_list = list(filter(lambda x: x[0] == mtl_account[0], donates))
        for donate_rules in found_list:
            calc_sum = round(float(donate_rules[2]) * float(mtl_account[2]) / 100, 7)
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

    # Сохранение в БД
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


def stellar_get_transaction_builder(xdr: str) -> TransactionBuilder:
    # Преобразуем XDR обратно в TransactionEnvelope
    transaction_envelope = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)

    # Извлекаем существующую транзакцию из TransactionEnvelope
    existing_transaction = transaction_envelope.transaction

    # Загружаем исходную учетную запись
    source_account = Account(account=existing_transaction.source.account_id,
                             sequence=existing_transaction.sequence - 1)
    # await server.load_account(account_id=existing_transaction.source.account_id)

    # Создаем новый TransactionBuilder с той же исходной информацией
    transaction_builder = TransactionBuilder(
        source_account=source_account,
        network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
        base_fee=existing_transaction.fee  # Сохраняем исходную базовую комиссию
    )

    # Устанавливаем временные границы, если они были заданы
    if existing_transaction.preconditions.time_bounds:
        transaction_builder.set_timeout(existing_transaction.preconditions.time_bounds.max_time)
    else:
        # Если временные границы не заданы, задаем неограниченное время
        transaction_builder.set_timeout(0)

    # Добавляем все существующие операции из старой транзакции
    for op in existing_transaction.operations:
        transaction_builder.append_operation(op)

    # Возвращаем объект TransactionBuilder для дальнейших модификаций
    return transaction_builder


def cmd_gen_data_xdr(account_id: str, data: str, xdr=None):
    if xdr:
        transaction = stellar_get_transaction_builder(xdr)
    else:
        server = Server(horizon_url=config.horizon_url)
        root_account = server.load_account(account_id)
        transaction = TransactionBuilder(source_account=root_account,
                                         network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                         base_fee=base_fee)
        transaction.set_timeout(60 * 60 * 24 * 7)
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
    all_issuer = await stellar_get_issuer_assets(MTLAddresses.public_issuer)
    # mtl_sum = float(all_issuer['MTL']) + float(all_issuer['MTLRECT'])
    #
    # div_accounts = []
    # donates = []
    # if test_sum > 0:
    #     div_sum = test_sum
    # else:
    #     # get balance
    #     div_sum = await get_balances(MTLAddresses.public_div)
    #     div_sum = float(div_sum['SATSMTL']) - 1
    #     logger.info(f"div_sum = {div_sum}")
    #     await stellar_async_submit(
    #         stellar_sign(cmd_gen_data_xdr(MTLAddresses.public_div, f'LAST_DIVS_SATSMTL:{div_sum}'),
    #                      config.private_sign.get_secret_value()))
    #
    # sponsor_sum = 0.0
    #
    # # print(json.dumps(response, indent=4))
    # accounts = await stellar_get_all_mtl_holders()
    # for account in accounts:
    #     # print(json.dumps(account,indent=4))
    #     # print('***')
    #     balances = account["balances"]
    #     balance_mtl = 0
    #     balance_rect = 0
    #     sats_open = 0
    #     # check all balance
    #     for balance in balances:
    #         if balance["asset_type"][0:15] == "credit_alphanum":
    #             if balance["asset_code"] == "MTL" and balance["asset_issuer"] == MTLAddresses.public_issuer:
    #                 balance_mtl = round(float(balance["balance"]), 7)
    #             if balance["asset_code"] == "MTLRECT" and balance["asset_issuer"] == MTLAddresses.public_issuer:
    #                 balance_rect = round(float(balance["balance"]), 7)
    #             if balance["asset_code"] == "SATSMTL" and balance["asset_issuer"] == MTLAddresses.public_issuer:
    #                 sats_open = 1
    #     div = round(div_sum / mtl_sum * (balance_mtl + balance_rect), 7)
    #     # print(f'{div_sum=},{mtl_sum},{balance_mtl},{balance_rect}')
    #     # check sponsor
    #     donates.extend(get_donate_list(account))
    #
    #     if (sats_open > 0) and (div > 0.0001) and (account["account_id"] != MTLAddresses.public_issuer) \
    #             and (account["account_id"] != MTLAddresses.public_pawnshop):
    #         div_accounts.append([account["account_id"], balance_mtl + balance_rect, div, div, div_list_id])
    #
    # div_accounts.sort(key=get_key_1, reverse=True)
    # payments = [
    #     TPayments(
    #         user_key=item[0],
    #         mtl_sum=item[1],
    #         user_calc=item[2],
    #         user_div=item[3],
    #         id_div_list=item[4]
    #     )
    #     for item in div_accounts
    # ]
    # session.add_all(payments)
    # session.commit()
    #
    # return div_accounts
    # print(*mtl_accounts, sep='\n')


async def cmd_calc_usdm_divs(session: Session, div_list_id: int, test_sum=0):
    pass
    # all_issuer = await stellar_get_issuer_assets(MTLAddresses.public_issuer)
    # mtl_sum = float(all_issuer['MTL']) + float(all_issuer['MTLRECT'])
    #
    # div_accounts = []
    # donates = []
    # if test_sum > 0:
    #     div_sum = test_sum
    # else:
    #     # get balance
    #     div_sum = await get_balances(MTLAddresses.public_div)
    #     div_sum = float(div_sum['USDM']) - 0.1
    #     logger.info(f"div_sum = {div_sum}")
    #     await stellar_async_submit(stellar_sign(cmd_gen_data_xdr(MTLAddresses.public_div, f'LAST_DIVS_USDM:{div_sum}'),
    #                                             config.private_sign.get_secret_value()))
    #
    # # print(json.dumps(response, indent=4))
    # accounts = await stellar_get_all_mtl_holders()
    # for account in accounts:
    #     # print(json.dumps(account,indent=4))
    #     # print('***')
    #     balances = account["balances"]
    #     balance_mtl = 0
    #     balance_rect = 0
    #     usdm_open = 0
    #     # check all balance
    #     for balance in balances:
    #         if balance["asset_type"][0:15] == "credit_alphanum":
    #             if balance["asset_code"] == "MTL" and balance["asset_issuer"] == MTLAddresses.public_issuer:
    #                 balance_mtl = round(float(balance["balance"]), 7)
    #             if balance["asset_code"] == "MTLRECT" and balance["asset_issuer"] == MTLAddresses.public_issuer:
    #                 balance_rect = round(float(balance["balance"]), 7)
    #             if balance["asset_code"] == "USDM" and balance["asset_issuer"] == MTLAddresses.public_usdm:
    #                 usdm_open = 1
    #     div = round(div_sum / mtl_sum * (balance_mtl + balance_rect), 7)
    #     # print(f'{div_sum=},{mtl_sum},{balance_mtl},{balance_rect}')
    #     # check sponsor
    #     donates.extend(get_donate_list(account))
    #
    #     if (usdm_open > 0) and (div > 0.0001) and (account["account_id"] != MTLAddresses.public_issuer) \
    #             and (account["account_id"] != MTLAddresses.public_pawnshop):
    #         div_accounts.append([account["account_id"], balance_mtl + balance_rect, div, div, div_list_id])
    #
    # div_accounts.sort(key=get_key_1, reverse=True)
    # payments = [
    #     TPayments(
    #         user_key=item[0],
    #         mtl_sum=item[1],
    #         user_calc=item[2],
    #         user_div=item[3],
    #         id_div_list=item[4]
    #     )
    #     for item in div_accounts
    # ]
    # session.add_all(payments)
    # session.commit()
    #
    # return div_accounts
    # print(*mtl_accounts, sep='\n')


async def cmd_calc_usdm_usdm_divs(session: Session, div_list_id: int, test_sum=0, test_for_address=None):
    div_accounts = []
    if test_sum > 0:
        div_sum = test_sum
    else:
        div_sum = await get_balances(MTLAddresses.public_usdm_div)
        div_sum = float(div_sum['USDM']) - 0.1
        logger.info(f"div_sum = {div_sum}")
        if not test_for_address:  # Записываем в блокчейн только если это не тестовый расчет
            await stellar_async_submit(
                stellar_sign(cmd_gen_data_xdr(MTLAddresses.public_usdm_div, f'LAST_DIVS_USDM:{div_sum}'),
                             config.private_sign.get_secret_value()))

    # print(json.dumps(response, indent=4))
    accounts = await stellar_get_holders(MTLAssets.usdm_asset)
    pools = await get_liquidity_pools_for_asset(MTLAssets.usdm_asset)
    total_calc_sum = 0

    for account in accounts:
        balances = account["balances"]
        token_balance = 0
        for balance in balances:
            if balance["asset_type"] == "credit_alphanum4" and balance["asset_code"] == MTLAssets.usdm_asset.code and \
                    balance["asset_issuer"] == MTLAssets.usdm_asset.issuer:
                token_balance += float(balance["balance"])
            elif balance["asset_type"] == "liquidity_pool_shares":
                # Находим пул по его ID и вычисляем долю USDM для аккаунта
                pool_id = balance["liquidity_pool_id"]
                pool_share = float(balance["balance"])
                for pool in pools:
                    if pool['id'] == pool_id:
                        usdm_amount = float(
                            pool['reserves_dict'].get(MTLAssets.usdm_asset.code + ':' + MTLAssets.usdm_asset.issuer, 0))
                        total_shares = float(pool['total_shares'])
                        # Рассчитываем долю USDM в пуле, принадлежащую аккаунту
                        if total_shares > 0 and pool_share > 0:
                            token_balance += (pool_share / total_shares) * usdm_amount

        div_accounts.append([account["account_id"], token_balance, 0, 0, div_list_id])
        total_calc_sum += token_balance

    div_accounts_dict = {account[0]: account[1] for account in div_accounts}

    current_date = datetime.now().date()
    start_current_month = datetime.now().replace(day=1).date()
    start_previous_month = (start_current_month - timedelta(days=1)).replace(day=1)

    while current_date >= start_current_month:
        for record in db_get_operations_by_asset(session, MTLAssets.usdm_asset.code, current_date):
            if record.for_account in div_accounts_dict:
                if record.operation == 'account_credited':
                    div_accounts_dict[record.for_account] -= float(record.amount1)
                elif record.operation == 'account_debited':
                    div_accounts_dict[record.for_account] += float(record.amount1)
                elif record.operation == 'trade':
                    if record.code1 == 'USDM':
                        div_accounts_dict[record.for_account] += float(record.amount1)
                    if record.code2 == 'USDM':
                        div_accounts_dict[record.for_account] -= float(record.amount2)
        current_date = current_date - timedelta(days=1)

    total_token_balance = sum(div_accounts_dict.values())

    div_accounts_dict_month = deepcopy(div_accounts_dict)
    month_full_sum = total_token_balance

    while current_date >= start_previous_month:
        for record in db_get_operations_by_asset(session, MTLAssets.usdm_asset.code, current_date):
            if record.for_account in div_accounts_dict:
                if record.operation == 'account_credited':
                    div_accounts_dict[record.for_account] -= float(record.amount1)
                elif record.operation == 'account_debited':
                    div_accounts_dict[record.for_account] += float(record.amount1)
                elif record.operation == 'trade':
                    if record.code1 == 'USDM':
                        div_accounts_dict[record.for_account] += float(record.amount1)
                    elif record.code2 == 'USDM':
                        div_accounts_dict[record.for_account] -= float(record.amount2)

        for key, value in div_accounts_dict.items():
            if value < 0:
                div_accounts_dict[key] = 0
        current_date = current_date - timedelta(days=1)
        total_token_balance = sum(div_accounts_dict.values())
        month_full_sum += total_token_balance
        for key, value in div_accounts_dict.items():
            div_accounts_dict_month[key] += value

    for record in div_accounts:
        record[2] = round((div_accounts_dict_month[record[0]] / month_full_sum) * div_sum, 7)
        record[3] = record[2]

    div_accounts.sort(key=get_key_1, reverse=True)

    # Фильтруем список div_accounts, оставляя только те элементы, которые удовлетворяют условию
    div_accounts = [record for record in div_accounts if round(record[2], 5) > 0]

    if test_for_address:
        # Ищем запись для тестового адреса
        test_account_data = next((record for record in div_accounts if record[0] == test_for_address), None)
        if test_account_data:
            return [test_account_data]  # Возвращаем только данные тестового адреса
        return []  # Если адрес не найден
    else:
        # Стандартное сохранение в БД только если это не тестовый расчет
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


async def cmd_get_new_vote_all_mtl(public_key, remove_master=False):
    if len(public_key) > 10:
        vote_list = await cmd_gen_mtl_vote_list()
        result = [gen_vote_xdr(public_key, vote_list, remove_master=remove_master, source=public_key)]
    else:
        vote_list = await cmd_gen_mtl_vote_list()
        # address_list = await gs_get_accounts_multi_list()
        accounts = await grist_manager.load_table_data(
            MTLGrist.EURMTL_accounts,
            filter_dict={"signers_type": ['multisp']}
        )

        result = []
        transaction = TransactionBuilder(
            source_account=Server(horizon_url=config.horizon_url).load_account(MTLAddresses.public_issuer),
            network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE, base_fee=base_fee)
        sequence = transaction.source_account.sequence
        transaction.set_timeout(60 * 60 * 24 * 7)
        xdr = None
        for account in accounts:
            account_id = account["account_id"]
            vote_list_copy = deepcopy(vote_list)
            # return sequence because every build inc number
            transaction.source_account.sequence = sequence
            if len(transaction.operations) < 80:
                xdr = gen_vote_xdr(account_id, vote_list_copy, transaction, source=account_id, remove_master=True)

        result.append(xdr)

    # print(gen_vote_xdr(public_new,vote_list2))

    return result


async def get_damircoin_xdr(div_sum: int):
    accounts = await stellar_get_holders(MTLAssets.damircoin_asset)
    accounts_list = []
    total_sum = 0

    for account in accounts:
        balances = account["balances"]
        token_balance = 0
        for balance in balances:
            if balance["asset_type"][0:15] == "credit_alphanum":
                if (balance["asset_code"] == MTLAssets.damircoin_asset.code and
                        balance["asset_issuer"] == MTLAssets.damircoin_asset.issuer):
                    token_balance = balance["balance"]
                    token_balance = int(token_balance[0:token_balance.find('.')])
        accounts_list.append([account["account_id"], token_balance, 0])
        total_sum += token_balance

    persent = div_sum / total_sum

    for account in accounts_list:
        account[2] = account[1] * persent

    root_account = Server(horizon_url=config.horizon_url).load_account(MTLAddresses.public_damir)
    transaction = TransactionBuilder(source_account=root_account, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                     base_fee=base_fee)
    transaction.set_timeout(60 * 60 * 24 * 7)
    transaction.add_text_memo('damircoin divs')
    for account in accounts_list:
        if account[2] > 0.0001:
            transaction.append_payment_op(destination=account[0], asset=MTLAssets.eurmtl_asset,
                                          amount=str(round(account[2], 7)))
    transaction = transaction.build()
    xdr = transaction.to_xdr()

    return xdr


async def get_agora_xdr():
    accounts = await stellar_get_holders(MTLAssets.agora_asset)
    accounts_list = []
    total_sum = 0

    # get total count
    # total_sum = stellar_get_token_amount(MTLAssets.agora_asset)

    for account in accounts:
        balances = account["balances"]
        token_balance = 0
        for balance in balances:
            if balance["asset_type"][0:15] == "credit_alphanum":
                if (balance["asset_code"] == MTLAssets.agora_asset.code and
                        balance["asset_issuer"] == MTLAssets.agora_asset.issuer):
                    token_balance = balance["balance"]
                    token_balance = int(token_balance[0:token_balance.find('.')])
        accounts_list.append([account["account_id"], token_balance, 0])
        total_sum += token_balance

    persent = 0.02  # 2% div_sum / total_sum

    for account in accounts_list:
        account[2] = account[1] * persent

    root_account = Server(horizon_url=config.horizon_url).load_account(MTLAssets.agora_asset.issuer)
    transaction = TransactionBuilder(source_account=root_account, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                     base_fee=base_fee)
    transaction.set_timeout(60 * 60 * 24 * 7)
    transaction.add_text_memo('AGORA divs')
    for account in accounts_list:
        if account[2] > 0.0001:
            transaction.append_payment_op(destination=account[0], asset=MTLAssets.eurmtl_asset,
                                          amount=str(round(account[2], 7)))
    transaction = transaction.build()
    xdr = transaction.to_xdr()

    return xdr


async def get_toc_xdr(div_sum: int):
    accounts = await stellar_get_holders(MTLAssets.toc_asset)
    accounts_list = []
    total_sum = 0

    for account in accounts:
        balances = account["balances"]
        token_balance = 0
        for balance in balances:
            if balance["asset_type"][0:15] == "credit_alphanum":
                if (balance["asset_code"] == MTLAssets.toc_asset.code and
                        balance["asset_issuer"] == MTLAssets.toc_asset.issuer):
                    token_balance = balance["balance"]
                    token_balance = int(token_balance[0:token_balance.find('.')])
        if account["account_id"] != "GDEF73CXYOZXQ6XLUN55UBCW5YTIU4KVZEPOI6WJSREN3DMOBLVLZTOP":
            accounts_list.append([account["account_id"], token_balance, 0])
            total_sum += token_balance

    persent = div_sum / total_sum

    for account in accounts_list:
        account[2] = account[1] * persent

    root_account = Server(horizon_url=config.horizon_url).load_account(MTLAssets.toc_asset.issuer)
    transaction = TransactionBuilder(source_account=root_account, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                     base_fee=base_fee)
    transaction.set_timeout(60 * 60 * 24 * 7)
    for account in accounts_list:
        if account[2] > 0.0001:
            transaction.append_payment_op(destination=account[0], asset=MTLAssets.eurmtl_asset,
                                          amount=str(round(account[2], 7)))
    transaction = transaction.build()
    xdr = transaction.to_xdr()

    return xdr


async def get_btcmtl_xdr(btc_sum, address: str, memo=None):
    root_account = Server(horizon_url=config.horizon_url).load_account(MTLAddresses.public_issuer)
    transaction = TransactionBuilder(source_account=root_account, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                     base_fee=base_fee)
    transaction.set_timeout(60 * 60 * 24 * 7)
    transaction.append_payment_op(destination=MTLAddresses.public_btc_guards, asset=MTLAssets.btcdebt_asset,
                                  amount=btc_sum)
    transaction.append_payment_op(destination=address, asset=MTLAssets.btcmtl_asset, amount=btc_sum)
    if memo:
        transaction.add_text_memo(memo)
    transaction = transaction.build()
    xdr = transaction.to_xdr()

    return xdr


async def cmd_show_data(account_id: str, filter_by: str = None, only_data: bool = False):
    result_data = []
    if account_id == 'delegate':  # не используеться не работает
        pass
        # get all delegate
        # vote_list = await cmd_gen_mtl_vote_list(return_delegate_list=True)
        # for k, v in vote_list.items():
        #    result_data.append(f'{k} => {v}')
    elif account_id == 'donate':
        # get all guards
        result_data = cmd_show_donates()
    else:
        account_json = requests.get(f'{config.horizon_url}/accounts/{account_id}').json()
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
    try:
        base64_message = data_value
        base64_bytes = base64_message.encode('ascii')
        message_bytes = base64.b64decode(base64_bytes)
        message = message_bytes.decode('ascii')
        return message
    except Exception as ex:
        logger.info(f"decode_data_value error: {ex}")
        return 'decode error'


async def cmd_show_donates(return_json=False, return_table=False):
    accounts = await stellar_get_all_mtl_holders()
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
                donate_data.append("******")

    if return_json:
        return donate_json
    if return_table:
        return donate_table
    return donate_data


async def stellar_get_holders(asset=MTLAssets.mtl_asset, mini=False):
    client = AiohttpClient(request_timeout=3 * 60)
    async with ServerAsync(
            horizon_url=config.horizon_url, client=client
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


async def stellar_get_all_mtl_holders() -> list:
    accounts = []
    for asset in (MTLAssets.mtl_asset, MTLAssets.mtlrect_asset):
        asset_accounts = await stellar_get_holders(asset)
        for account in asset_accounts:
            if account not in accounts:
                accounts.append(account)
    return accounts


async def stellar_get_token_amount(asset=MTLAssets.mtl_asset):
    async with ServerAsync(horizon_url=config.horizon_url) as server:
        assets = await server.assets().for_code(asset.code).for_issuer(asset.issuer).call()
        return assets['_embedded']['records'][0]['amount']


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


async def cmd_gen_mtl_vote_list(trim_count=20, delegate_list=None) -> list[MyShareHolder]:
    if delegate_list is None:
        delegate_list = {}
    shareholder_list = []

    # Get current signers from issuer account
    server = Server(horizon_url=config.horizon_url)
    source_account = server.load_account(MTLAddresses.public_issuer)
    sg = source_account.load_ed25519_public_key_signers()

    # Create dictionary for quick signer lookup
    signer_weights = {s.account_id: s.weight for s in sg}

    accounts = await stellar_get_all_mtl_holders()

    # mtl
    for account in accounts:
        balances = account["balances"]
        balance_mtl = 0  # не имею голоса с 2025
        balance_rect = 0

        for balance in balances:
            if balance["asset_type"][0:15] == "credit_alphanum":
                # if balance["asset_code"] == "MTL" and balance["asset_issuer"] == MTLAddresses.public_issuer:
                # balance_mtl = int(float(balance["balance"])) * k  # 0.75 0.5 0.25
                if balance["asset_code"] == "MTLRECT" and balance["asset_issuer"] == MTLAddresses.public_issuer:
                    balance_rect = int(float(balance["balance"]))

        account_id = account["account_id"]
        if account_id != MTLAddresses.public_issuer:
            # Set votes from signer weights
            votes = signer_weights.get(account_id, 0)

            shareholder = MyShareHolder(
                account_id=account_id,
                balance_mtl=balance_mtl,
                balance_rect=balance_rect,
                data=account.get('data'),
                votes=votes
            )
            shareholder_list.append(shareholder)

    # Add signers that are not in shareholder_list but have weight > 0
    existing_account_ids = {sh.account_id for sh in shareholder_list}
    for signer_id, weight in signer_weights.items():
        if weight > 0 and signer_id not in existing_account_ids:
            shareholder = MyShareHolder(
                account_id=signer_id,
                balance_mtl=0,
                balance_rect=0,
                votes=weight
            )
            shareholder_list.append(shareholder)

    # Фильтруем shareholder_list, оставляя только аккаунты с балансом >= 1
    shareholder_list = [sh for sh in shareholder_list if sh.balance >= 1]

    # Сортируем shareholder_list по убыванию баланса
    shareholder_list.sort(key=lambda sh: sh.balance, reverse=True)

    # find delegate
    for shareholder in shareholder_list:
        if shareholder.data:
            data = shareholder.data
            for data_name in list(data):
                data_value = data[data_name]
                if data_name in ('delegate', 'mtl_delegate'):
                    delegate_list[shareholder.account_id] = decode_data_value(data_value)

    # Многошаговая делегация
    max_steps = 3  # Максимальное количество шагов делегирования

    for step in range(max_steps):
        changes_made = False
        temp_delegate_list = delegate_list.copy()  # Создаем копию для безопасного изменения

        for shareholder in shareholder_list:
            if shareholder.account_id in temp_delegate_list:
                delegate_id = temp_delegate_list[shareholder.account_id]
                delegate = next((s for s in shareholder_list if s.account_id == delegate_id), None)

                if delegate:
                    delegate.balance_delegated += shareholder.balance + shareholder.balance_delegated
                    shareholder.balance_delegated = 0
                    shareholder.balance_mtl = 0
                    shareholder.balance_rect = 0
                    changes_made = True

        # Обновляем delegate_list только после завершения итерации
        delegate_list = temp_delegate_list

        # Если изменений не было, прерываем цикл
        if not changes_made:
            break

    # Очищаем delegate_list после завершения всех шагов
    delegate_list.clear()

    # delete blacklist user
    bl = cmd_get_blacklist()
    # Обработка черного списка для shareholder_list
    for shareholder in shareholder_list:
        if bl.get(shareholder.account_id):
            # Обнуляем соответствующие значения
            shareholder.balance_mtl = 0
            shareholder.balance_rect = 0
            shareholder.balance_delegated = 0

    # Если итоговый баланс (с учетом делегирования) меньше 500 MTLRECT,
    # право голоса MTLRECT обнуляется. Участник остается в списке.
    # №for shareholder in shareholder_list:
    #    if shareholder.balance_rect < 500:
    #        shareholder.balance_mtl = 0
    #        shareholder.balance_rect = 0

    # Сортируем shareholder_list по убыванию баланса
    shareholder_list.sort(key=lambda sh: sh.balance, reverse=True)

    # Фильтруем участников с балансом MTLRECT >= 500 для расчета голосов
    eligible_shareholders = [sh for sh in shareholder_list if sh.balance_rect >= 500]

    if eligible_shareholders:
        total_sum = 0
        for account in eligible_shareholders:
            total_sum += account.balance

        total_vote = 0
        for account in eligible_shareholders:
            account.calculated_votes = math.ceil(account.balance * 100 / total_sum)
            total_vote += account.calculated_votes

        big_vote = eligible_shareholders[0].calculated_votes

        for account in eligible_shareholders:
            account.calculated_votes = round(account.calculated_votes ** (
                    1 - (1.45 - (big_vote - total_vote / 3) / total_vote) * (big_vote - total_vote / 3) / total_vote))
        # =C8^(1-(1,45-($C$2-$C$22/3)/$C$22)*($C$2-$C$22/3)/$C$22)

        # Обновляем calculated_votes в основном списке shareholder_list
        # Создаем словарь для быстрого поиска рассчитанных голосов
        calculated_votes_dict = {sh.account_id: sh.calculated_votes for sh in eligible_shareholders}

        # Обновляем calculated_votes для всех участников в основном списке
        for shareholder in shareholder_list:
            if shareholder.account_id in calculated_votes_dict:
                shareholder.calculated_votes = calculated_votes_dict[shareholder.account_id]
            else:
                shareholder.calculated_votes = 0  # Участники без права голоса получают 0

    # Двойная сортировка: сначала по calculated_votes, потом по votes, потом по балансу
    shareholder_list.sort(key=lambda sh: (sh.calculated_votes, sh.votes, sh.balance), reverse=True)

    return shareholder_list[:trim_count]


async def cmd_gen_fin_vote_list(account_id: str = MTLAddresses.public_fin):
    delegate_key = "tfm_delegate"
    days_to_track = 365
    days_inactive = 90
    top_donors = 10
    coefficients = [12, 5]

    # Step 1
    now = datetime.now()
    one_year_ago = now - timedelta(days=days_to_track)

    donor_dict = {}

    async with ServerAsync(horizon_url=config.horizon_url) as server:
        payments_call_builder = server.payments().for_account(account_id).order(desc=True)
        page_records = await payments_call_builder.call()

        while page_records["_embedded"]["records"]:
            for payment in page_records["_embedded"]["records"]:
                if payment.get('to') and payment['to'] == account_id and datetime.strptime(payment['created_at'],
                                                                                           '%Y-%m-%dT%H:%M:%SZ') > one_year_ago:
                    amount = float(payment['amount'])
                    last_donation_date = datetime.strptime(payment['created_at'], '%Y-%m-%dT%H:%M:%SZ')
                    if payment['from'] not in donor_dict:
                        donor_dict[payment['from']] = {'sum': amount, 'date': last_donation_date}
                    else:
                        donor_dict[payment['from']]['sum'] += amount
                        if last_donation_date > donor_dict[payment['from']]['date']:
                            donor_dict[payment['from']]['date'] = last_donation_date
            page_records = await payments_call_builder.next()

        # Step 3
        ninety_days_ago = now - timedelta(days=days_inactive)
        for donor, data in list(donor_dict.items()):
            if data['date'] < ninety_days_ago:
                donor_dict.pop(donor)

        # Step 4 and 5
        for donor, data in donor_dict.items():
            account_data = await server.accounts().account_id(donor).call()
            delegate_data = account_data['data']
            if delegate_key in delegate_data:
                delegate_id = delegate_data[delegate_key]
                payment_amount = data['sum']
                payment_date = data['date']

                if delegate_id in donor_dict:
                    donor_dict[delegate_id]['sum'] += payment_amount
                    if payment_date > donor_dict[delegate_id]['date']:
                        donor_dict[delegate_id]['date'] = payment_date

        # Step 6
        sorted_donors = sorted(donor_dict.items(), key=lambda x: (x[1]['sum'], x[1]['date']), reverse=True)

        # Step 7
        top_sorted_donors = sorted_donors[:top_donors]

        # Step 8
        final_list = []
        for donor, data in top_sorted_donors:
            sum_of_payments = data['sum']
            for coeff in coefficients:
                sum_of_payments /= coeff
            votes = math.log2(sum_of_payments)
            final_list.append([donor, data['sum'], int(votes), 0, data['date']])

    return final_list


def cmd_get_blacklist():
    return requests.get('https://raw.githubusercontent.com/montelibero-org/mtl/main/json/blacklist.json').json()


def stellar_remove_orders(public_key, xdr):
    if xdr:
        transaction = stellar_get_transaction_builder(xdr)
    else:
        root_account = Server(horizon_url=config.horizon_url).load_account(public_key)
        transaction = TransactionBuilder(source_account=root_account,
                                         network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                         base_fee=base_fee)
        transaction.set_timeout(60 * 60 * 24 * 7)

    call = Server(horizon_url=config.horizon_url).offers().for_account(public_key).limit(200).call()

    for record in call['_embedded']['records']:
        # print(record['price'], record)
        transaction.append_manage_sell_offer_op(
            selling=Asset(record['selling'].get('asset_code', 'XLM'), record['selling'].get('asset_issuer')),
            buying=Asset(record['buying'].get('asset_code', 'XLM'), record['buying'].get('asset_issuer')),
            amount='0', price=Price(record['price_r']['n'], record['price_r']['d']), offer_id=int(record['id']),
            source=public_key)

    if transaction.operations:
        transaction = transaction.build()
        xdr = transaction.to_xdr()

    return xdr


def isfloat(value):
    try:
        float(value)
        return True
    except ValueError:
        return False


def gen_vote_xdr(public_key, vote_list: list[MyShareHolder], transaction=None, source=None, remove_master=False,
                 max_count=20, threshold_style=0):
    # узнать кто в подписантах
    server = Server(horizon_url=config.horizon_url)
    source_account = server.load_account(public_key)

    sg = source_account.load_ed25519_public_key_signers()

    for s in sg:
        was_found = False
        for arr in vote_list:
            if arr.account_id == s.account_id:
                arr.votes = s.weight
                was_found = True
        if not was_found and s.account_id != public_key:
            vote_list.append(MyShareHolder(account_id=s.account_id, votes=s.weight))

    vote_list.sort(key=lambda k: k.calculated_votes, reverse=True)

    # up user to delete
    tmp_list = []
    del_count = 0

    # account_list.append([account["account_id"], balance_mtl, lg, 0, account['data'], balance_mtl, balance_rect])
    for arr in vote_list:
        if (int(arr.calculated_votes) == 0) & (int(arr.votes) > 0):
            tmp_list.append(arr)
            vote_list.remove(arr)
            del_count += 1

    tmp_list.extend(vote_list)

    while len(tmp_list) > max_count + del_count:
        arr = tmp_list.pop(max_count + del_count)
        if arr.votes > 0:
            del_count += 1
            tmp_list.insert(0, MyShareHolder(account_id=arr.account_id, votes=arr.votes))

    vote_list = tmp_list
    # 5
    server = Server(horizon_url=config.horizon_url)
    source_account = server.load_account(public_key)
    root_account = Account(public_key, sequence=source_account.sequence)
    if transaction is None:
        transaction = TransactionBuilder(source_account=root_account,
                                         network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE, base_fee=base_fee)
        transaction.set_timeout(60 * 60 * 24 * 7)
    threshold = 0

    for arr in vote_list:
        if int(arr.calculated_votes) != int(arr.votes):
            transaction.append_ed25519_public_key_signer(arr.account_id, int(arr.calculated_votes), source=source)
        threshold += int(arr.calculated_votes)

    if threshold_style == 1:
        threshold = threshold // 3 * 2
    else:
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


async def cmd_check_new_transaction(ignore_operation: List,
                                    account_id=MTLAddresses.public_issuer, cash=None, chat_id=None):
    result = []

    try:
        # Проверяем, есть ли данные в кэше
        if cash is not None and account_id in cash:
            tr = cash[account_id]
        else:
            # Если данных в кэше нет, выполняем запрос
            server = Server(horizon_url=config.horizon_url)
            tr = server.transactions().for_account(account_id).order(desc=True).call()
            # Сохраняем полученные данные в кэш
            if cash is not None:
                cash[account_id] = tr

        # Получаем last_id из базы данных
        last_id = await global_data.mongo_config.load_kv_value(account_id + chat_id)

        # Если last_id равен None, сохраняем текущий last_id и выходим
        if last_id is None:
            if tr["_embedded"]["records"]:
                last_id = tr["_embedded"]["records"][0]["paging_token"]
                await global_data.mongo_config.save_kv_value(account_id + chat_id, last_id)
            return result

        new_transactions = []
        for record in tr["_embedded"]["records"]:
            if record["paging_token"] == last_id:
                break
            new_transactions.append(record)

        for transaction in new_transactions:
            if transaction["paging_token"] > last_id:
                last_id = transaction["paging_token"]
            try:
                tr = await decode_xdr(transaction["envelope_xdr"], ignore_operation=ignore_operation)
                if tr and 0 < len(tr) < 90:
                    link = f'https://stellar.expert/explorer/public/tx/{transaction["paging_token"]}'
                    try:
                        tr_details = await decode_xdr(transaction["envelope_xdr"])
                        if tr_details:
                            tr_details.insert(0, f'(<a href="{link}">expert link</a>)')
                            result.append(tr_details)
                    except Exception as ex:
                        logger.error(f"Error decoding XDR details for transaction {transaction['paging_token']}: {ex}")
                        # Добавляем базовую информацию о транзакции, если детальное декодирование не удалось
                        result.append([f'(<a href="{link}">expert link</a>)', 'Error decoding transaction details'])
            except Exception as ex:
                logger.error(f"Error processing transaction {transaction['paging_token']}: {ex}")
                continue

        await global_data.mongo_config.save_kv_value(account_id + chat_id, last_id)

    except Exception as ex:
        logger.error(f"Error in cmd_check_new_transaction for account {account_id}: {ex}")

    return result


async def cmd_check_new_asset_transaction(session: Session, asset: str, filter_sum: int = -1,
                                          filter_operation=None, filter_asset=None, chat_id=None):
    try:
        if filter_operation is None:
            filter_operation = []
        result = []
        asset_name = asset.split('-')[0]

        # Получаем last_id из базы данных
        last_id = await global_data.mongo_config.load_kv_value(asset + chat_id)

        # Если last_id равен None, просто сохраняем его и выходим
        if last_id is None:
            # Получаем данные для определения текущего max_id
            data = db_get_new_effects_for_token(session, asset_name, '-1', filter_sum)
            if data:
                # Сохраняем id последнего эффекта как начальный last_id
                await global_data.mongo_config.save_kv_value(asset + chat_id, data[-1].id)
            return result

        max_id = last_id

        # Получаем новые эффекты для токена
        data = db_get_new_effects_for_token(session, asset_name, last_id, filter_sum)
        for row in data:
            try:
                effect = await decode_db_effect(row)
                if effect:  # Проверяем, что effect не пустой
                    result.append(effect)
                    max_id = row.id
            except Exception as ex:
                logger.error(f"Error decoding effect for row {row.id}: {ex}")
                continue

        # Сохраняем новый max_id, если он больше last_id
        if max_id > last_id:
            await global_data.mongo_config.save_kv_value(asset + chat_id, max_id)

        return result

    except Exception as ex:
        logger.error(f"Error in cmd_check_new_asset_transaction for asset {asset}: {ex}")
        return []


async def decode_db_effect(row: TOperations):
    try:
        result = f'<a href="https://stellar.expert/explorer/public/op/{row.id.split("-")[0]}">' \
                 f'Операция</a> с аккаунта {await address_id_to_username(row.for_account)} \n'
        if row.operation == 'trade':
            result += f'  {row.operation}  {float2str(row.amount1)} {row.code1} for {float2str(row.amount2)} {row.code2} \n'
        else:
            result += f'  {row.operation} for {float2str(row.amount1)} {row.code1} \n'
        return result
    except Exception as ex:
        logger.error(f"Error in decode_db_effect for operation {row.id}: {ex}")
        return None


def cmd_check_last_operation(address: str, filter_operation=None) -> datetime:
    operations = Server(horizon_url=config.horizon_url).operations().for_account(address).order().limit(
        1).call()
    op = operations['_embedded']['records'][0]
    # print(operation["created_at"])  # 2022-08-23T13:47:33Z
    dt = datetime.strptime(op["created_at"], '%Y-%m-%dT%H:%M:%SZ')
    # print(dt)

    return dt


def get_memo_by_op(op: str):
    operation = Server(horizon_url=config.horizon_url).operations().operation(op).call()
    transaction = Server(horizon_url=config.horizon_url).transactions().transaction(
        operation['transaction_hash']).call()
    return transaction.get('memo', 'None')


async def resolve_account(account_id: str):
    result = ''
    client = AiohttpClient()
    try:
        result = await resolve_account_id_async(account_id, domain='eurmtl.me', client=client)
        result = result.stellar_address
    except Exception:
        pass
    if result == '':
        try:
            result = await resolve_account_id_async(account_id, domain='lobstr.co', client=client)
            result = result.stellar_address
        except Exception:
            pass
    if result == '':
        try:
            result = await resolve_account_id_async(account_id, domain='keybase.io', client=client)
            result = result.stellar_address
        except Exception:
            pass
    if result == '':
        result = account_id[:4] + '..' + account_id[-4:]
    await client.close()
    return result


async def stellar_add_mtl_holders_info(accounts: list[MyShareHolder]):
    async with ServerAsync(
            horizon_url=config.horizon_url, client=AiohttpClient()
    ) as server:
        source_account = await server.load_account(MTLAddresses.public_issuer)
        sg = source_account.load_ed25519_public_key_signers()

    # Создаем словарь для быстрого доступа к весу по account_id
    signer_weights = {s.account_id: s.weight for s in sg}

    # Обновляем голоса аккаунтов в соответствии с весом подписчиков
    for account in accounts:
        if account.account_id in signer_weights:
            account.votes = signer_weights[account.account_id]


async def stellar_get_trade_cost(asset: Asset) -> float:
    """
    Calculate average trade price between given asset and EURMTL based on last 100 trades.

    Args:
        asset: Stellar SDK Asset object to check trades against EURMTL

    Returns:
        float: Average trade price or 0 if no trades found
    """
    try:
        async with ServerAsync(
                horizon_url=config.horizon_url, client=AiohttpClient()
        ) as server:
            # Get last 100 trades for the asset pair
            trades = await server.trades().for_asset_pair(
                asset, MTLAssets.eurmtl_asset
            ).limit(100).order(desc=True).call()

            if not trades['_embedded']['records']:
                return 0

            total_price = 0
            trade_count = 0

            # Calculate average price from trades
            for trade in trades['_embedded']['records']:
                # Check which asset is base/counter to calculate correct price
                if trade['base_asset_code'] == asset.code:
                    price = float(trade['price']['n']) / float(trade['price']['d'])
                else:
                    price = float(trade['price']['d']) / float(trade['price']['n'])

                total_price += price
                trade_count += 1

            return total_price / trade_count if trade_count > 0 else 0

    except Exception as ex:
        logger.error(f"Error getting trade cost for {asset.code}: {ex}")
        return 0


def stellar_get_receive_path(send_asset: Asset, send_sum: str, receive_asset: Asset) -> list:
    try:
        server = Server(horizon_url=config.horizon_url)
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
    server = Server(horizon_url=config.horizon_url)
    source_account = server.load_account(from_account)
    transaction = TransactionBuilder(source_account=source_account,
                                     network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE, base_fee=base_fee)
    transaction.set_timeout(60 * 60 * 24 * 7)
    transaction.append_path_payment_strict_send_op(from_account, send_asset, send_amount, receive_asset,
                                                   receive_amount,
                                                   stellar_get_receive_path(send_asset, send_amount, receive_asset))
    transaction.set_timeout(60 * 60 * 24 * 7)
    full_transaction = transaction.build()
    logger.info(full_transaction.to_xdr())
    return full_transaction.to_xdr()


def gen_new(last_name):
    i = 0
    new_account = None
    while True:
        mnemonic = Keypair.generate_mnemonic_phrase()
        try:
            new_account = Keypair.from_mnemonic_phrase(mnemonic)
        except ValueError:
            print(f"Invalid mnemonic: {mnemonic}")
            continue

        if new_account.public_key[-len(last_name):] == last_name:
            break

        i += 1
        print(f"{i}: Public Key: {new_account.public_key}")
        # print(mnemonic)

    return [i, new_account.public_key, new_account.secret, mnemonic]


def stellar_add_fond_trustline(address_id, asset_code):
    return stellar_add_trustline(address_id, asset_code, MTLAddresses.public_issuer)


def stellar_add_trustline(address_id, asset_code, asset_issuer):
    root_account = Server(horizon_url=config.horizon_url).load_account(address_id)
    transaction = TransactionBuilder(source_account=root_account, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                     base_fee=base_fee)
    transaction.set_timeout(60 * 60 * 24 * 7)
    transaction.append_change_trust_op(Asset(asset_code, asset_issuer))
    transaction = transaction.build()

    xdr = transaction.to_xdr()

    return xdr


# async def cmd_get_new_vote_all_tfm():
#     vote_list = await cmd_gen_fin_vote_list()
#     vote_list2 = deepcopy(vote_list)
#
#     transaction = TransactionBuilder(
#         source_account=Server(horizon_url=config.horizon_url).load_account(MTLAddresses.public_fin),
#         network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE, base_fee=base_fee)
#     sequence = transaction.source_account.sequence
#     transaction.set_timeout(60 * 60 * 24 * 7)
#     xdr = gen_vote_xdr(public_key=MTLAddresses.public_fin, vote_list=vote_list,
#                        threshold_style=1, transaction=transaction)
#
#     # return sequence because every build inc number
#     transaction.source_account.sequence = sequence
#     xdr = gen_vote_xdr(public_key=MTLAddresses.public_tfm, vote_list=vote_list2,
#                        threshold_style=1, transaction=transaction, source=MTLAddresses.public_tfm)
#
#     # print(gen_vote_xdr(public_new,vote_list2))
#     return xdr


def find_stellar_public_key(text):
    # Stellar публичные ключи начинаются с 'G' и содержат 56 символов
    stellar_public_key_pattern = r'G[A-Za-z0-9]{55}'
    match = re.search(stellar_public_key_pattern, text)
    return match.group(0) if match else None


def find_stellar_federation_address(text):
    # Stellar федеральные адреса имеют формат 'username*domain.com'
    stellar_federation_address_pattern = r'[a-z0-9]+[\._]?[a-z0-9]+[*][a-z0-9\-]+[\.][a-z0-9\.]+'
    match = re.search(stellar_federation_address_pattern, text)
    return match.group(0) if match else None


async def check_mtlap(key):
    balances = await get_balances(address=key)

    if 'MTLAP' in balances:
        return f'Баланс MTLAP: {balances["MTLAP"]}'

    return 'MTLAP не найден'


def determine_working_range():
    today = datetime.now()
    if 1 <= today.day <= 14:
        if today.month == 1:
            start_range = datetime(today.year - 1, 12, 15)
        else:
            start_range = datetime(today.year, today.month - 1, 15)
        end_range = datetime(today.year, today.month, 1) - timedelta(days=1)
    else:
        start_range = datetime(today.year, today.month, 1)
        end_range = datetime(today.year, today.month, 14)
    return start_range, end_range


async def stellar_get_transactions(address, start_range, end_range):
    transactions = []
    async with ServerAsync(horizon_url=config.horizon_url, client=AiohttpClient()) as server:
        # Запускаем получение страниц транзакций
        payments_call_builder = server.payments().for_account(account_id=address).limit(200).order()
        page_records = await payments_call_builder.call()
        while page_records["_embedded"]["records"]:
            # Проверяем каждую транзакцию на соответствие диапазону
            for record in page_records["_embedded"]["records"]:
                tx_date = datetime.strptime(record['created_at'], "%Y-%m-%dT%H:%M:%SZ")
                if tx_date < start_range:
                    # Если дата транзакции выходит за пределы начала диапазона, прекращаем получение данных
                    return transactions
                if start_range.date() <= tx_date.date() <= end_range.date():
                    transactions.append(record)
            # Получаем следующую страницу записей
            page_records = await payments_call_builder.next()

    return transactions


async def get_chicago_xdr():
    # Определяем рабочий диапазон
    result = []
    start_range, end_range = determine_working_range()
    # start_range, end_range = datetime(2023, 11, 14), datetime(2023, 11, 14)

    result.append(f'Ищем транзакции с {start_range.strftime("%Y-%m-%d")} по {end_range.strftime("%Y-%m-%d")}')
    accounts_dict = {}

    # Ваш Stellar адрес
    stellar_address = 'GD6HELZFBGZJUBCQBUFZM2OYC3HKWDNMC3PDTTDGB7EY4UKUQ2MMELSS'

    premium_list = await gs_get_chicago_premium()
    result.append(f'Получено премиум пользователей: {len(premium_list)}')

    # Запускаем асинхронное получение транзакций
    transactions = await stellar_get_transactions(stellar_address, start_range, end_range)
    result.append(f'Получено транзакций в диапазоне: {len(transactions)}')

    # Здесь может быть ваш код для обработки транзакций
    for transaction in transactions:
        # {'_links': {'self': {'href': 'https://horizon.stellar.org/operations/209303707773333505'}, 'transaction': {'href': 'https://horizon.stellar.org/transactions/2c46bcae7f62198f5d670bc0f1e990078637afe414f057d6eff016324e933ff9'}, 'effects': {'href': 'https://horizon.stellar.org/operations/209303707773333505/effects'}, 'succeeds': {'href': 'https://horizon.stellar.org/effects?order=desc&cursor=209303707773333505'}, 'precedes': {'href': 'https://horizon.stellar.org/effects?order=asc&cursor=209303707773333505'}}, 'id': '209303707773333505', 'paging_token': '209303707773333505', 'transaction_successful': True, 'source_account': 'GBGGX7QD3JCPFKOJTLBRAFU3SIME3WSNDXETWI63EDCORLBB6HIP2CRR', 'type': 'payment', 'type_i': 1, 'created_at': '2023-10-26T14:03:53Z', 'transaction_hash': '2c46bcae7f62198f5d670bc0f1e990078637afe414f057d6eff016324e933ff9', 'asset_type': 'credit_alphanum12', 'asset_code': 'EURMTL', 'asset_issuer': 'GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V', 'from': 'GBGGX7QD3JCPFKOJTLBRAFU3SIME3WSNDXETWI63EDCORLBB6HIP2CRR', 'to': 'GD6HELZFBGZJUBCQBUFZM2OYC3HKWDNMC3PDTTDGB7EY4UKUQ2MMELSS', 'amount': '11.0000000'}
        if (transaction.get('asset_code') == MTLAssets.eurmtl_asset.code
                and transaction.get('asset_issuer') == MTLAssets.eurmtl_asset.issuer):
            if transaction['to'] != transaction['from'] and transaction['to'] == stellar_address:
                accounts_dict[transaction['from']] = (float(transaction['amount']) +
                                                      accounts_dict.get(transaction['from'], 0))

    # print(accounts_dict)
    root_account = Server(horizon_url=config.horizon_url).load_account(stellar_address)
    transaction = TransactionBuilder(source_account=root_account, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                     base_fee=base_fee)
    transaction.set_timeout(60 * 60 * 24 * 7)
    transaction.add_text_memo('cashback')
    total_sum = 0
    total_income_sum = 0
    premium_sum = 0
    for account in accounts_dict:
        # 13 всем, премиум 26
        if account in premium_list:
            cashback_sum = accounts_dict[account] * 0.26
            premium_sum += cashback_sum
        else:
            cashback_sum = accounts_dict[account] * 0.13
        total_sum += cashback_sum
        total_income_sum += accounts_dict[account]

        transaction.append_payment_op(destination=account, asset=MTLAssets.eurmtl_asset,
                                      amount=str(round(cashback_sum, 7)))
    transaction = transaction.build()
    xdr = transaction.to_xdr()
    result.append('За период - ')
    num_premium_accounts = sum(account in premium_list for account in accounts_dict)
    num_regular_accounts = len(accounts_dict) - num_premium_accounts
    total_sum, total_income_sum, premium_sum = round(total_sum, 2), round(total_income_sum, 2), round(premium_sum, 2)
    result.append(f'Сумма входящих - {total_income_sum}')
    result.append(f'Премиум пользователей: {num_premium_accounts} обычных пользователей: {num_regular_accounts}')
    result.append(f'Premium sum: {premium_sum} Total sum: {total_sum}')
    result.append(xdr)

    return result


def check_mtla_delegate(account, result, delegated_list=None):
    if delegated_list is None:
        delegated_list = []
    delegate_to_account = result[account]['delegate']
    # убираем цикл на себя
    if delegate_to_account and delegate_to_account == account:
        result[account]['delegate'] = None
        return

    # убираем цикл побольше
    if delegate_to_account and delegate_to_account in delegated_list:
        result[account]['delegate'] = None
        return

    if delegate_to_account:
        if result[account]['vote'] > 0:
            delegated_list.append(account)
        if result[delegate_to_account]['delegate']:
            result[account]['was_delegate'] = check_mtla_delegate(delegate_to_account, result, delegated_list)
        else:
            if 'delegated_list' in result[delegate_to_account]:
                result[delegate_to_account]['delegated_list'].extend(delegated_list)
            else:
                result[delegate_to_account]['delegated_list'] = delegated_list
            result[account]['was_delegate'] = delegate_to_account
            return delegate_to_account


async def get_mtlap_votes():
    result = {}
    # составляем дерево по держателям
    accounts = await stellar_get_holders(MTLAssets.mtlap_asset)
    for account in accounts:
        delegate = None
        if account['data'] and account['data'].get('mtla_a_delegate'):
            delegate = decode_data_value(account['data']['mtla_a_delegate'])
        vote = 0
        for balance in account['balances']:
            if balance.get('asset_code') and balance['asset_code'] == MTLAssets.mtlap_asset.code and balance[
                'asset_issuer'] == MTLAssets.mtlap_asset.issuer:
                vote = int(float(balance['balance']))
                break
        result[account['id']] = {'delegate': delegate, 'vote': vote, 'can_vote': vote >= 2}

    # добавляем кого нет
    find_new = True
    while find_new:
        find_new = False
        for account in list(result):
            if result[account]['delegate'] and result[account]['delegate'] not in result:
                find_new = True
                new_account = await stellar_get_account(result[account]['delegate'])
                delegate = None
                if new_account.get('data') and new_account['data'].get('mtla_a_delegate'):
                    delegate = decode_data_value(new_account['data']['mtla_a_delegate'])
                vote = 0
                balances = new_account.get('balances')
                if balances:
                    for balance in balances:
                        if balance.get('asset_code') and balance['asset_code'] == MTLAssets.mtlap_asset.code and \
                                balance['asset_issuer'] == MTLAssets.mtlap_asset.issuer:
                            vote = int(float(balance['balance']))
                            break
                result[new_account['id']] = {'delegate': delegate, 'vote': vote, 'can_vote': vote >= 2}

    for account in list(result):
        check_mtla_delegate(account, result)

    # Проверяем, может ли аккаунт голосовать
    for account in list(result):
        if not result[account]['can_vote']:
            # Проверяем, есть ли делегаты с 2 или более токенами
            if 'delegated_list' in result[account]:
                for delegator in result[account]['delegated_list']:
                    if result[delegator]['vote'] >= 2:
                        result[account]['can_vote'] = True
                        break

    # Удаляем аккаунты, которые не могут голосовать
    for account in list(result):
        if not result[account]['can_vote']:
            del result[account]

    del result['GDGC46H4MQKRW3TZTNCWUU6R2C7IPXGN7HQLZBJTNQO6TW7ZOS6MSECR']
    del result['GCNVDZIHGX473FEI7IXCUAEXUJ4BGCKEMHF36VYP5EMS7PX2QBLAMTLA']

    return result


async def get_get_income():
    address = 'GD6HELZFBGZJUBCQBUFZM2OYC3HKWDNMC3PDTTDGB7EY4UKUQ2MMELSS'
    transactions = await stellar_get_transactions(address,
                                                  datetime.strptime('15.11.2023', '%d.%m.%Y'),
                                                  datetime.strptime('30.11.2023', '%d.%m.%Y'))
    # total_amount = sum(transaction.amount for transaction in transactions if transaction)
    total_amount = 0
    for transaction in transactions:
        # {'_links': {'self': {'href': 'https://horizon.stellar.org/operations/209303707773333505'}, 'transaction': {'href': 'https://horizon.stellar.org/transactions/2c46bcae7f62198f5d670bc0f1e990078637afe414f057d6eff016324e933ff9'}, 'effects': {'href': 'https://horizon.stellar.org/operations/209303707773333505/effects'}, 'succeeds': {'href': 'https://horizon.stellar.org/effects?order=desc&cursor=209303707773333505'}, 'precedes': {'href': 'https://horizon.stellar.org/effects?order=asc&cursor=209303707773333505'}}, 'id': '209303707773333505', 'paging_token': '209303707773333505', 'transaction_successful': True, 'source_account': 'GBGGX7QD3JCPFKOJTLBRAFU3SIME3WSNDXETWI63EDCORLBB6HIP2CRR', 'type': 'payment', 'type_i': 1, 'created_at': '2023-10-26T14:03:53Z', 'transaction_hash': '2c46bcae7f62198f5d670bc0f1e990078637afe414f057d6eff016324e933ff9', 'asset_type': 'credit_alphanum12', 'asset_code': 'EURMTL', 'asset_issuer': 'GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V', 'from': 'GBGGX7QD3JCPFKOJTLBRAFU3SIME3WSNDXETWI63EDCORLBB6HIP2CRR', 'to': 'GD6HELZFBGZJUBCQBUFZM2OYC3HKWDNMC3PDTTDGB7EY4UKUQ2MMELSS', 'amount': '11.0000000'}
        if (transaction.get('asset_code') == MTLAssets.eurmtl_asset.code
                and transaction.get('asset_issuer') == MTLAssets.eurmtl_asset.issuer
                and transaction.get('type') == 'payment' and transaction.get('to') == address):
            total_amount += float(transaction['amount'])
    print(total_amount)


def test_xdr():
    server = Server(horizon_url=config.horizon_url)
    transaction = TransactionBuilder(source_account=server.load_account(MTLAddresses.public_itolstov),
                                     network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
                                     base_fee=base_fee)
    transaction.set_timeout(60 * 60 * 24 * 7)
    transaction.append_create_claimable_balance_op(
        asset=Asset(code='TestCode2023', issuer=MTLAddresses.public_itolstov),
        amount='100',
        claimants=[
            Claimant(
                destination='GCPOWDQQDVSAQGJXZW3EWPPJ5JCF4KTTHBYNB4U54AKQVDLZXLLYMXY7',
                predicate=ClaimPredicate.predicate_not(
                    ClaimPredicate.predicate_before_absolute_time(
                        int(time()) + 60 * 60 * 24 * 7
                    ))
            ),
            Claimant(destination=MTLAddresses.public_itolstov)
        ])
    print(ClaimPredicate.predicate_before_absolute_time(int(time()) + 60 * 60 * 24 * 7))
    print(transaction.build().to_xdr())


async def get_liquidity_pools_for_asset(asset):
    client = AiohttpClient(request_timeout=3 * 60)

    async with ServerAsync(
            horizon_url=config.horizon_url, client=client
    ) as server:
        pools = []
        pools_call_builder = server.liquidity_pools().for_reserves([asset]).limit(200)

        page_records = await pools_call_builder.call()
        while page_records["_embedded"]["records"]:
            for pool in page_records["_embedded"]["records"]:
                # Удаление _links из результатов
                pool.pop('_links', None)

                # Преобразование списка reserves в словарь reserves_dict
                reserves_dict = {reserve['asset']: reserve['amount'] for reserve in pool['reserves']}
                pool['reserves_dict'] = reserves_dict

                # Удаление исходного списка reserves
                pool.pop('reserves', None)

                pools.append(pool)

            page_records = await pools_call_builder.next()
        return pools


async def copy_trustlines(from_address: str, to_address: str, exclude_assets: List[Asset] = None):
    if exclude_assets is None:
        exclude_assets = []

    # Получаем балансы исходного аккаунта
    balances = await get_balances(from_address, return_assets=True)

    # Открываем трастлайны на целевом аккаунте
    server = Server(horizon_url=config.horizon_url)
    to_account = server.load_account(to_address)
    transaction = TransactionBuilder(
        source_account=to_account,
        network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
        base_fee=base_fee
    )
    transaction.set_timeout(60 * 60 * 24 * 7)

    for asset, balance in balances.items():
        if isinstance(asset, Asset) and asset not in exclude_assets:
            transaction.append_change_trust_op(asset)

    print("XDR для открытия трастлайнов:")
    print(transaction.build().to_xdr())

    # Переводим средства
    from_account = server.load_account(from_address)
    transaction = TransactionBuilder(
        source_account=from_account,
        network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
        base_fee=base_fee
    )
    transaction.set_timeout(60 * 60 * 24 * 7)

    for asset, balance in balances.items():
        if isinstance(asset, Asset) and asset not in exclude_assets and float(balance) > 0:
            transaction.append_payment_op(
                destination=to_address,
                asset=asset,
                amount=str(balance)
            )

    print("XDR для перевода средств:")
    print(transaction.build().to_xdr())

    # Закрываем трастлайны на исходном аккаунте
    from_account = server.load_account(from_address)
    transaction = TransactionBuilder(
        source_account=from_account,
        network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
        base_fee=base_fee
    )
    transaction.set_timeout(60 * 60 * 24 * 7)

    for asset, balance in balances.items():
        if isinstance(asset, Asset) and asset not in exclude_assets and float(balance) == 0:
            transaction.append_change_trust_op(asset, limit='0')

    print("XDR для закрытия трастлайнов:")
    print(transaction.build().to_xdr())

    return "XDR для операций копирования трастлайнов сгенерированы."


text_to_save = '''### Charter of the MTLA Cyberocracy Faction ###

### 1. General Provisions
1.1 The MTLA Cyberocracy Faction (hereinafter "the Faction") is an autonomous association of enthusiasts within the broader libertarian group, the Montelibero Association.

1.2 The purpose of the Faction is to create an extraterritorial contractual jurisdiction governed by artificial intelligence (hereinafter "AI") to eliminate the influence of personalities' emotions and ambitions on governance.

### 2. Principles and values
2.1 Inviolability of private property.

2.2 Freedom of contract.

2.3 Freedom and accessibility of information.

2.4 Minimization of the human factor in decision-making. 2.5.

2.5 Transparency and accountability of AI.

### 3. Organizational structure
3.1 The Faction operates on the basis of the principles of fluid democracy, where each member can delegate his/her vote.

3.2 Members of the Caucus shall delegate their vote in the Caucus Association Council. The exception is when a member of the Caucus is the representative of the Caucus in the Association Council.

3.3 The Caucus has a representative in the Association Council, to whom the Caucus delegates the votes of its members and is obliged to fulfill the decisions made by the Caucus, as well as to inform the Caucus about the activities of the Council.

### 4. Administration and decision making
4.1 The Faction shall endeavor to have all administrative and managerial activities performed by the AI.

4.2 The AI shall be guided by the interests of the members of the Faction. Members may articulate their interests in text form to the AI.

4.3 Caucus members may delegate their voice within the Caucus to the AI.

4.4 The AI has a deliberative voice within the Caucus.

4.5 Decisions in the Faction are divided into binding and recommended. Mandatory decisions are made by 2/3 of votes, recommended decisions - by majority of votes.

4.6 If during the voting period (minimum 2 days) a member has not voted, his/her vote is transferred to the representative in the Association Council.

4.7 Voting is conducted electronically on a platform approved by the Caucus Council. Participants are notified of the start of voting at least 5 days in advance.

4.8 All voting results are published on the official platform of the Caucus within 24 hours after the voting is completed.

4.9 An annual audit of AI actions and decisions shall be conducted by an independent commission selected by Caucus members. The auditors' report is published for public access.

### 5. Membership and rights of participants
5.1 Members of the Fraction can be any physical persons who have transferred delegation of their vote in the Council of the Association of the Fraction.

5.2 Caucus members have the right to participate in the discussion and policy making of the Caucus.

5.3 All members of the Faction are obliged to respect the decisions made by the AI and the Faction.

5.4 The Faction undertakes to respect the confidentiality of its members' data, following modern data protection standards.

5.5 Faction members are obliged to declare any possible conflicts of interest and abstain from voting in cases where their personal interests may affect the objectivity of decisions.

### 6. Financial and material resources
6.1 The financing of the Faction's activity is carried out at the expense of voluntary contributions of its members and supporters.

6.2 All financial transactions must be transparent and available for inspection by the members of the Faction.

6.3 The address of the Caucus is GCAYT4PKYSSCS2R7RD5PNTWSA6ZWDR52NPUUCSJAGB5GIUI53TW4AIAI.

6.4 All financial transactions are subject to an annual audit by an independent audit committee. The auditors' report shall be published for public access.

### 7. Supporters of the Faction
7.1 Supporters of the Fraction can be natural and legal persons who support its goals and principles.

7.2 Supporters may participate in discussions and make proposals, but have no right to vote in decision-making.

7.3 Supporters may make voluntary contributions to support the activities of the Caucus and receive reports on its activities.

### 8. Final provisions
8.1 The present Charter comes into force from the moment of its adoption by the members of the Faction.

8.2 Amendments and additions to the Charter can be made only by the decision of the Caucus members and must be approved by 2/3 of votes.'''


def prepare_and_send_transaction(soroban_server, source_keypair, contract_address, function_name, parameters):
    from stellar_sdk import Network, TransactionBuilder
    from stellar_sdk.exceptions import PrepareTransactionException
    from stellar_sdk.soroban_rpc import SendTransactionStatus
    source_account = soroban_server.load_account(source_keypair.public_key)

    transaction = (
        TransactionBuilder(
            source_account=source_account,
            base_fee=10_000,
            network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
        )
        .append_invoke_contract_function_op(
            contract_id=contract_address,
            function_name=function_name,
            parameters=parameters,
        )
        .set_timeout(30)
        .build()
    )

    try:
        prepared_transaction = soroban_server.prepare_transaction(transaction)
    except PrepareTransactionException as e:
        print(f"Exception preparing transaction: {e}")
        raise e

    prepared_transaction.sign(source_keypair)
    send_response = soroban_server.send_transaction(prepared_transaction)

    if send_response.status != SendTransactionStatus.PENDING:
        raise Exception("Sending transaction failed")

    return send_response.hash


def wait_for_transaction(soroban_server, transaction_hash):
    import time
    from stellar_sdk.soroban_rpc import GetTransactionStatus
    while True:
        print("Waiting for transaction confirmation...")
        get_response = soroban_server.get_transaction(transaction_hash)
        if get_response.status != GetTransactionStatus.NOT_FOUND:
            break
        time.sleep(1)

    print(f"Get transaction response: {get_response}")

    if get_response.status == GetTransactionStatus.SUCCESS:
        print("Transaction succeeded!")
        return True
    else:
        print(f"Transaction failed: {get_response.result_xdr}")
        return False


def save_texts_to_contract(contract_address, name, texts):
    from stellar_sdk import Keypair, SorobanServer, xdr as stellar_xdr

    soroban_server = SorobanServer('https://soroban-rpc.mainnet.stellar.gateway.fm')
    source_keypair = Keypair.from_secret(config.private_sign.get_secret_value())

    lines = []
    for line in texts:
        lines.append(
            stellar_xdr.SCVal(type=stellar_xdr.SCValType.SCV_STRING, str=stellar_xdr.SCString(line.encode('utf-8'))))

    parameters = [
        stellar_xdr.SCVal(stellar_xdr.SCValType.SCV_STRING,
                          str=stellar_xdr.SCString(sc_string=name.encode('utf-8'))),

        stellar_xdr.SCVal(stellar_xdr.SCValType.SCV_VEC, vec=stellar_xdr.SCVec(lines))
    ]

    transaction_hash = prepare_and_send_transaction(
        soroban_server,
        source_keypair,
        contract_address,
        "save_texts",
        parameters
    )

    return wait_for_transaction(soroban_server, transaction_hash)


# Пример использования
async def test2():
    contract_address = 'CDCUT3LZX4QP26P5TUTLESX3COFQO6X5OY5B7FIH6A44KX3YF72LLKSB'

    lines = text_to_save.split('\n')

    success = save_texts_to_contract(contract_address, "charter_en", lines)

    if success:
        print("Texts successfully saved to the contract.")
    else:
        print("Failed to save texts to the contract.")


async def test1():
    import time
    from stellar_sdk import Keypair, Network, SorobanServer, TransactionBuilder, xdr as stellar_xdr
    from stellar_sdk.exceptions import PrepareTransactionException
    from stellar_sdk.soroban_rpc import GetTransactionStatus, SendTransactionStatus
    source_keypair = Keypair.from_secret(config.private_sign.get_secret_value())
    config.horizon_url = 'https://mainnet.stellar.validationcloud.io/v1/zLR8If1YxHyKtdE1EvW1EBczkjZ6Y8TVcLzBtdVeTYQ'
    config.horizon_url = 'https://soroban-rpc.mainnet.stellar.gateway.fm'
    soroban_server = SorobanServer(config.horizon_url)

    contract_address = 'CA4F7EARNNPSFJ5GSZDROYMOLSK6X75UAIIZBLVSTXFSJO3D2YUSXJI4'

    source_account = soroban_server.load_account(source_keypair.public_key)

    built_transaction = (
        TransactionBuilder(
            source_account=source_account,
            base_fee=10_000,
            network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
        )

        .append_invoke_contract_function_op(
            contract_id=contract_address,
            function_name="get_weight",
            parameters=[
                stellar_xdr.SCVal(stellar_xdr.SCValType.SCV_SYMBOL, sym=stellar_xdr.SCSymbol('Soz'.encode('utf-8'))),

            ],
        )
        # This transaction will be valid for the next 30 seconds
        .set_timeout(30)
        .build()
    )

    # We use the RPC server to "prepare" the transaction. This simulating the
    # transaction, discovering the storage footprint, and updating the transaction
    # to include that footprint. If you know the footprint ahead of time, you could
    # manually use `addFootprint` and skip this step.
    print(built_transaction)
    print(built_transaction.to_xdr())
    try:
        prepared_transaction = soroban_server.prepare_transaction(built_transaction)
    except PrepareTransactionException as e:
        print(f"Exception preparing transaction: {e}")
        raise e

    # Sign the transaction with the source account's keypair.
    prepared_transaction.sign(source_keypair)

    # Let's see the base64-encoded XDR of the transaction we just built.
    print(f"Signed prepared transaction XDR: {prepared_transaction.to_xdr()}")

    # Submit the transaction to the Soroban-RPC server. The RPC server will then
    # submit the transaction into the network for us. Then we will have to wait,
    # polling `getTransaction` until the transaction completes.
    send_response = soroban_server.send_transaction(prepared_transaction)
    print(f"Sent transaction: {send_response}")

    if send_response.status != SendTransactionStatus.PENDING:
        raise Exception("sending transaction failed")

    # Poll `getTransaction` until the status is not "NOT_FOUND"
    while True:
        print("Waiting for transaction confirmation...")
        # See if the transaction is complete
        get_response = soroban_server.get_transaction(send_response.hash)
        if get_response.status != GetTransactionStatus.NOT_FOUND:
            break
        # Wait one second
        time.sleep(1)

    print(f"get_transaction response: {get_response}")

    if get_response.status == GetTransactionStatus.SUCCESS:
        # Make sure the transaction's resultMetaXDR is not empty
        assert get_response.result_meta_xdr is not None

        # Find the return value from the contract and return it
        transaction_meta = stellar_xdr.TransactionMeta.from_xdr(
            get_response.result_meta_xdr
        )
        return_value = transaction_meta.v3.soroban_meta.return_value
        #        output = return_value.u32.uint32
        print(f"Transaction result: {return_value}")
    else:
        print(f"Transaction failed: {get_response.result_xdr}")


async def pay_ny():
    # need pay from MTLAddresses.public_div
    # get address by     accounts = await stellar_get_all_mtl_holders()
    # create transaction for 0.002025 MTLAssets.mtl_asset
    # add memo Happy New Year and send
    server = Server(horizon_url=config.horizon_url)
    last = 'GCAVQ52ST23HPZX2QOF3PIDG6ZPPNWKHJIG3FZFU44GQKLD52D6RK7RD'
    need_send = False
    num = 0

    accounts = await stellar_get_holders(MTLAssets.mtl_asset)
    for account in accounts:
        num += 1
        if account["account_id"] == last:
            need_send = True
        print(num, account["account_id"])

        if not need_send:
            continue

        source_account = server.load_account(MTLAddresses.public_div)
        transaction = TransactionBuilder(
            source_account=source_account,
            network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
            base_fee=base_fee
        )
        transaction.set_timeout(60 * 60 * 24 * 7)
        transaction.add_text_memo("Happy New Year")
        transaction.append_payment_op(
            destination=account["account_id"],
            asset=MTLAssets.mtl_asset,
            amount="0.002025"
        )

        transaction = transaction.build()
        transaction.sign(get_private_sign())

        server.submit_transaction(transaction)


async def get_market_price(
        asset1: Asset,
        asset2: Asset,
        amount: str = "1"
) -> Optional[dict]:
    """
    Получает детальную информацию о ценах на рынке между двумя активами.

    Returns:
        dict: Словарь с деталями цен или None в случае ошибки
    """
    async with ServerAsync(
            horizon_url=config.horizon_url, client=AiohttpClient()
    ) as server:
        try:
            # Получаем цены в обоих направлениях
            forward_result = await server.strict_send_paths(
                asset1,
                amount,
                [asset2]
            ).call()
            reverse_result = await server.strict_send_paths(
                asset2,
                amount,
                [asset1]
            ).call()

            if (not forward_result['_embedded']['records'] or
                    not reverse_result['_embedded']['records']):
                return None

            # Извлекаем данные
            forward_amount = Decimal(
                forward_result['_embedded']['records'][0]['destination_amount']
            )
            reverse_amount = Decimal(
                reverse_result['_embedded']['records'][0]['destination_amount']
            )

            forward_price = forward_amount / Decimal(amount)
            reverse_price = Decimal(amount) / reverse_amount
            average_price = (forward_price + reverse_price) / Decimal('2')

            return {
                'forward_price': forward_price,
                'reverse_price': reverse_price,
                'average_price': average_price,
                'forward_amount': forward_amount,
                'reverse_amount': reverse_amount,
                'input_amount': Decimal(amount),
                # 'timestamp': datetime.utcnow().isoformat(),
                'asset1': asset1.code,
                'asset2': asset2.code
            }

        except Exception as ex:
            logger.exception(
                f"Error getting market price details for {asset1.code}/{asset2.code}: {ex}"
            )
            return None


async def test():
    a = await cmd_gen_mtl_vote_list(30)
    print('\n'.join(str(x) for x in a))


if __name__ == '__main__':
    pass
    print(asyncio.run(test()))
