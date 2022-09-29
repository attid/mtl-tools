from typing import List

import requests
from stellar_sdk import Network, Server, TransactionBuilder, Asset, Account, Keypair, Price
from stellar_sdk import TransactionEnvelope  # , Operation, Payment, SetOptions, TextMemo,
from stellar_sdk.exceptions import BadRequestError
from stellar_sdk.sep.federation import resolve_stellar_address

import fb
from cryptocode import encrypt, decrypt

from MyMTLWalletBot_main import logger
from mytypes import MyOffers, MyAccount, Balance, MyOffer  # , MyAsset, MyOffer
from settings import base_fee

# from settings import private_div, private_bod_eur

# https://stellar-sdk.readthedocs.io/en/latest/

public_issuer = "GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V"
public_fond = "GDX23CPGMQ4LN55VGEDVFZPAJMAUEHSHAMJ2GMCU2ZSHN5QF4TMZYPIS"
public_pawnshop = "GDASYWP6F44TVNJKZKQ2UEVZOKTENCJFTWVMP6UC7JBZGY4ZNB6YAVD4"
public_distributor = "GB7NLVMVC6NWTIFK7ULLEQDF5CBCI2TDCO3OZWWSFXQCT7OPU3P4EOSR"

public_bod_eur = "GDEK5KGFA3WCG3F2MLSXFGLR4T4M6W6BMGWY6FBDSDQM6HXFMRSTEWBW"
public_bod = "GARUNHJH3U5LCO573JSZU4IOBEVQL6OJAAPISN4JKBG2IYUGLLVPX5OH"
public_div = "GDNHQWZRZDZZBARNOH6VFFXMN6LBUNZTZHOKBUT7GREOWBTZI4FGS7IQ"

xlm_asset = Asset("XLM")
mtl_asset = Asset("MTL", public_issuer)
eurmtl_asset = Asset("EURMTL", public_issuer)
eurdebt_asset = Asset("EURDEBT", public_issuer)

my_server = Server(horizon_url="https://horizon.stellar.org")


def get_good_asset_list() -> List[Balance]:
    return [
        Balance.from_dict(
            {"asset_code": 'AUMTL', "asset_issuer": 'GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V'}),
        Balance.from_dict(
            {"asset_code": 'EURMTL', "asset_issuer": 'GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V'}),
        Balance.from_dict(
            {"asset_code": 'BTCMTL', "asset_issuer": 'GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V'}),
        Balance.from_dict(
            {"asset_code": 'EURDEBT', "asset_issuer": 'GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V'}),
        Balance.from_dict(
            {"asset_code": 'MTL', "asset_issuer": 'GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V'}),
        Balance.from_dict(
            {"asset_code": 'MTLand', "asset_issuer": 'GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V'}),
        Balance.from_dict(
            {"asset_code": 'MTLCITY', "asset_issuer": 'GDUI7JVKWZV4KJVY4EJYBXMGXC2J3ZC67Z6O5QFP4ZMVQM2U5JXK2OK3'}),
        Balance.from_dict(
            {"asset_code": 'MTLDVL', "asset_issuer": 'GAMU3C7Q7CUUC77BAN5JLZWE7VUEI4VZF3KMCMM3YCXLZPBYK5Q2IXTA'}),
        Balance.from_dict(
            {"asset_code": 'MTLGoldriver', "asset_issuer": 'GDUI7JVKWZV4KJVY4EJYBXMGXC2J3ZC67Z6O5QFP4ZMVQM2U5JXK2OK3'}),
        Balance.from_dict(
            {"asset_code": 'MTLMiner', "asset_issuer": 'GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V'}),
        Balance.from_dict(
            {"asset_code": 'MTLRoads', "asset_issuer": 'GDUI7JVKWZV4KJVY4EJYBXMGXC2J3ZC67Z6O5QFP4ZMVQM2U5JXK2OK3'})
    ]


def stellar_add_trust(user_key: str, asset: Asset, xdr: str = None, delete: bool = False):
    if xdr:
        transaction = TransactionBuilder.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
    else:
        source_account = my_server.load_account(user_key)
        transaction = TransactionBuilder(source_account=source_account,
                                         network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE, base_fee=base_fee)
    if delete:
        transaction.append_change_trust_op(asset, '0')
    else:
        transaction.append_change_trust_op(asset)
    transaction = transaction.build()

    xdr = transaction.to_xdr()
    # logger.info(f"xdr: {xdr}")
    return xdr


def stellar_sign(xdr: str, private_key: str):
    transaction = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
    transaction.sign(private_key)
    return transaction.to_xdr()


def get_url_xdr(url):
    rq = requests.get(url).text
    rq = rq[rq.find('<span class="tx-body">') + 22:]
    # logger.info(rq)
    rq = rq[:rq.find('</span>')]
    rq = rq.replace("&#x3D;", "=")
    # logger.info(rq)
    return rq


def stellar_check_xdr(xdr: str):
    result = None
    # "https://mtl.ergvein.net/view?tid=7ec5e397140fadf0d384860a35d19cf9f60e00a49b3b2cc250b832076fab7e7f"
    try:
        if xdr.find('mtl.ergvein.net/view') > -1:
            xdr = get_url_xdr(xdr)
            result = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE).to_xdr()
        else:
            result = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE).to_xdr()

    except Exception as ex:
        logger.info(['stellar_check_xdr', xdr, ex])
    return result


def stellar_user_sign(xdr: str, user_id: int, user_password: str):
    user_keypair = stellar_get_user_keypair(user_id, user_password)
    return stellar_sign(xdr, user_keypair.secret)


def stellar_send(xdr: str):
    transaction = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
    transaction_resp = my_server.submit_transaction(transaction)
    return transaction_resp


def stellar_save_new(user_id: int, secret_key: str, free_wallet: bool):
    new_account = Keypair.from_secret(secret_key)
    i_free_wallet = 1 if free_wallet else 0
    fb.execsql(f"insert into mymtlwalletbot (user_id, public_key, secret_key, credit, default_wallet, free_wallet) "
               f"values ({user_id},'{new_account.public_key}','{encrypt(new_account.secret, str(user_id))}',"
               f"{3},{1},{i_free_wallet})")
    return new_account.public_key


def stellar_create_new(user_id: int):
    new_account = Keypair.random()
    stellar_save_new(user_id, new_account.secret, True)

    master = stellar_get_master()
    xdr = stellar_pay(master.public_key, new_account.public_key, xlm_asset, 3, create=True)
    stellar_send(stellar_sign(xdr, master.secret))

    xdr = stellar_add_trust(new_account.public_key, mtl_asset)
    xdr = stellar_add_trust(new_account.public_key, eurmtl_asset, xdr=xdr)
    stellar_send(stellar_sign(xdr, new_account.secret))


def stellar_pay(from_account: str, for_account: str, asset: Asset, amount: float, create: bool = False):
    source_account = my_server.load_account(from_account)
    transaction = TransactionBuilder(source_account=source_account,
                                     network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE, base_fee=base_fee)
    if create:
        transaction.append_create_account_op(destination=for_account, starting_balance=str(round(amount, 7)))
        transaction.add_text_memo('New account MyMTLWalletbot')
    else:
        transaction.append_payment_op(destination=for_account, amount=str(round(amount, 7)), asset=asset)
    full_transaction = transaction.build()
    logger.info(full_transaction.to_xdr())
    return full_transaction.to_xdr()


def stellar_swap(from_account: str, send_asset: Asset, send_amount: str, receive_asset: Asset,
                 receive_amount: str):
    source_account = my_server.load_account(from_account)
    transaction = TransactionBuilder(source_account=source_account,
                                     network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE, base_fee=base_fee)
    transaction.append_path_payment_strict_send_op(from_account, send_asset, send_amount, receive_asset,
                                                   receive_amount,
                                                   stellar_get_receive_path(send_asset, send_amount, receive_asset))
    full_transaction = transaction.build()
    logger.info(full_transaction.to_xdr())
    return full_transaction.to_xdr()


def stellar_sale(from_account: str, send_asset: Asset, send_amount: str, receive_asset: Asset,
                 receive_amount: str, offer_id: int = 0):
    source_account = my_server.load_account(from_account)
    transaction = TransactionBuilder(source_account=source_account,
                                     network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE, base_fee=base_fee)
    if (float(receive_amount) == 0.0) or (float(send_amount) == 0.0):
        price = '99999999'
    else:
        price = str(round(float(receive_amount) / float(send_amount), 7))

    transaction.append_manage_sell_offer_op(selling=send_asset, buying=receive_asset, amount=str(send_amount),
                                            price=Price.from_raw_price(price),
                                            offer_id=offer_id)
    full_transaction = transaction.build()
    logger.info(full_transaction.to_xdr())
    return full_transaction.to_xdr()


def stellar_get_user_keypair(user_id: int, user_password: str) -> Keypair:
    result = fb.execsql(
        f"select m.public_key, m.secret_key from mymtlwalletbot m where m.user_id = {user_id} "
        f"and m.default_wallet = 1")[0]
    return Keypair.from_secret(decrypt(result[1], user_password))


def stellar_get_user_account(user_id: int, public_key=None) -> Account:
    if public_key:
        result = public_key
    else:
        result = fb.execsql1(
            f"select m.public_key from mymtlwalletbot m where m.user_id = {user_id} "
            f"and m.default_wallet = 1")
    return my_server.load_account(result)


def stellar_get_master() -> Keypair:
    return stellar_get_user_keypair(0, '0')


def stellar_can_new(user_id: int):
    result = fb.execsql1(f"select count(*) from mymtlwalletbot m where m.user_id = {user_id} and m.free_wallet = 1")
    if int(result) > 2:
        return False
    else:
        return True


def stellar_delete_account(master_account: Keypair, delete_account: Keypair):
    logger.info(['delete_account', delete_account.public_key])
    source_account = my_server.load_account(master_account)
    transaction = TransactionBuilder(source_account=source_account,
                                     network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE, base_fee=base_fee)
    account = my_server.accounts().account_id(delete_account.public_key).call()
    for balance in account['balances']:
        if balance['asset_type'] != "native":
            if float(balance['balance']) > 0.0:
                transaction.append_payment_op(destination=master_account.public_key, amount=balance['balance'],
                                              asset=Asset(balance['asset_code'], balance['asset_issuer']),
                                              source=delete_account.public_key)
            transaction.append_change_trust_op(asset=Asset(balance['asset_code'], balance['asset_issuer']), limit='0',
                                               source=delete_account.public_key)

    transaction.append_account_merge_op(master_account.public_key, delete_account.public_key)
    transaction.add_text_memo('Eat MyMTLWalletbot')
    full_transaction = transaction.build()
    xdr = full_transaction.to_xdr()
    stellar_send(stellar_sign(stellar_sign(xdr, master_account.secret), delete_account.secret))


def stellar_get_balance_str(user_id: int, public_key=None):
    balances = stellar_get_balances(user_id, public_key)
    result = ''
    for balance in balances:
        result += f"{balance.asset_code} : {balance.balance}\n"

    return result


def stellar_get_pin_type(user_id: int):
    result = fb.execsql1(
        f"select m.use_pin from mymtlwalletbot m where m.user_id = {user_id} "
        f"and m.default_wallet = 1")
    return result


def stellar_is_free_wallet(user_id: int):
    user_account = stellar_get_user_account(user_id)
    free_wallet = fb.execsql1(f"select m.free_wallet from mymtlwalletbot m where m.user_id = {user_id} "
                              f"and m.public_key = '{user_account.account.account_id}'")
    return free_wallet == 1


def stellar_get_balances(user_id: int, public_key=None, asset_filter: str = None) -> List[Balance]:
    user_account = stellar_get_user_account(user_id, public_key)
    free_wallet = stellar_is_free_wallet(user_id)
    balances = MyAccount.from_dict(my_server.accounts().account_id(
        user_account.account.account_id).call()).balances
    result = []
    for balance in balances:
        if (balance.asset_type == "native") and (free_wallet == 0):
            result.append(balance)
        elif balance.asset_type[:15] == "credit_alphanum":
            if asset_filter and (balance.asset_code.find(asset_filter) == -1):
                pass
            else:
                result.append(balance)
    return result


def stellar_get_offers(user_id: int, public_key=None) -> List[MyOffer]:
    user_account = stellar_get_user_account(user_id, public_key)
    offers = MyOffers.from_dict(my_server.offers().for_seller(
        user_account.account.account_id).call())

    return offers.embedded.records


def stellar_get_wallets_list(user_id: int):
    wallets = fb.execsql(
        f"select public_key, default_wallet, free_wallet from mymtlwalletbot where user_id = {user_id}")
    return wallets


def stellar_set_default_wallets(user_id: int, public_key: str):
    fb.execsql(
        f"update mymtlwalletbot set default_wallet = 1 where user_id = {user_id} and public_key = '{public_key}'")
    return True


def stellar_delete_wallets(user_id: int, public_key: str):
    wallets = fb.execsql(
        f"update mymtlwalletbot set user_id = -1 * user_id where user_id = {user_id} and public_key = '{public_key}'")
    return wallets


def stellar_change_password(user_id: int, public_key: str, old_password: str, new_password: str, password_type: int):
    account = Keypair.from_secret(decrypt(fb.execsql1(
        f"select m.secret_key from mymtlwalletbot m where m.user_id = {user_id} "
        f"and m.public_key = '{public_key}'"), old_password))
    fb.execsql(
        f"update mymtlwalletbot set secret_key = '{encrypt(account.secret, new_password)}', "
        f"use_pin = {password_type} where user_id = {user_id} "
        f"and public_key = '{public_key}'")
    return account.public_key


def stellar_check_account(public_key: str) -> Account:
    try:
        if public_key.find('*') > 0:
            public_key = resolve_stellar_address(public_key).account_id
        return my_server.load_account(public_key)
    except Exception as ex:
        logger.info(["stellar_check_account", public_key, ex])
        # return None


def stellar_check_receive_sum(send_asset: Asset, send_sum: str, receive_asset: Asset) -> str:
    try:
        call_result = my_server.strict_send_paths(send_asset, send_sum, [receive_asset]).call()
        if len(call_result['_embedded']['records']) > 0:
            return call_result['_embedded']['records'][0]['destination_amount']
        else:
            return '0'
    except Exception as ex:
        logger.info(["stellar_check_receive_sum", send_asset.code + ' ' + send_sum + ' ' + receive_asset.code, ex])
        return '0'


def stellar_get_receive_path(send_asset: Asset, send_sum: str, receive_asset: Asset) -> list:
    try:
        call_result = my_server.strict_send_paths(send_asset, send_sum, [receive_asset]).call()
        if len(call_result['_embedded']['records']) > 0:
            # [{'asset_type': 'credit_alphanum12', 'asset_code': 'EURMTL',
            #  'asset_issuer': 'GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V'}]
            if len(call_result['_embedded']['records'][0]['path']) == 0:
                return []
            else:
                if call_result['_embedded']['records'][0]['path'][0]['asset_type'] == 'native':
                    return [xlm_asset]
                else:
                    return [Asset(call_result['_embedded']['records'][0]['path'][0]['asset_code'],
                                  call_result['_embedded']['records'][0]['path'][0]['asset_issuer'])]
        else:
            return []
    except Exception as ex:
        logger.info(["stellar_check_receive_sum", send_asset.code + ' ' + send_sum + ' ' + receive_asset.code, ex])
        return []


def stellar_check_receive_asset(send_asset: Asset, send_sum: str, receive_assets: list) -> list:
    try:
        records = []
        while len(receive_assets) > 0:
            call_result = my_server.strict_send_paths(send_asset, send_sum, receive_assets[:3]).call()
            records.extend(call_result['_embedded']['records'])
            if len(receive_assets) > 0:
                receive_assets.pop(0)
            if len(receive_assets) > 0:
                receive_assets.pop(0)
            if len(receive_assets) > 0:
                receive_assets.pop(0)
        result = []
        for record in records:
            asset_code = ''
            if record['destination_asset_type'] == "native":
                asset_code = "XLM"
            elif record['destination_asset_type'][:15] == "credit_alphanum":
                asset_code = record['destination_asset_code']

            if (len(asset_code) > 0) and not (asset_code in result):
                result.append(asset_code)

        return result
    except BadRequestError as ex:
        logger.info(
            ["stellar_check_receive_sum", send_asset.code + ' ' + send_sum + ' ' + str(receive_assets)[:15],
             ex.message])
    except Exception as ex:
        logger.info(
            ["stellar_check_receive_sum", send_asset.code + ' ' + send_sum + ' ' + str(receive_assets)[:15], ex])
        return []


def get_last_message_id(user_id: int):
    try:
        return fb.execsql1(f"select first 1 m.message_id from mymtlwalletbot m where m.user_id = ?", (user_id,), 0)
    except Exception as ex:
        return 0


def set_last_message_id(user_id: int, message_id: int):
    if get_last_message_id(user_id) != message_id:
        fb.execsql(f"update mymtlwalletbot set message_id = ? where user_id = ?", (message_id, user_id))


if __name__ == "__main__":
    xdr = stellar_sale('GDLTH4KKMA4R2JGKA7XKI5DLHJBUT42D5RHVK6SS6YHZZLHVLCWJAYXI', eurmtl_asset, '10', mtl_asset, '20')
    print(xdr)
    # print(stellar_get_balance_str(0, 'GDLTH4KKMA4R2JGKA7XKI5DLHJBUT42D5RHVK6SS6YHZZLHVLCWJAYXI'))
    # print(get_good_asset_list())
    # account = MyAccount.from_dict(my_server.accounts().account_id(
    #    'GDLTH4KKMA4R2JGKA7XKI5DLHJBUT42D5RHVK6SS6YHZZLHVLCWJAYXI').call())

    # print(account)
    # print(account.balances)
    # print(account.data)
    # print(json.dumps(account, indent=4))
    # orders = stellar_get_offers_list(0, public_key='GDLTH4KKMA4R2JGKA7XKI5DLHJBUT42D5RHVK6SS6YHZZLHVLCWJAYXI')
    # print(orders)
