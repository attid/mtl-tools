import requests
from stellar_sdk import Network, Server, TransactionBuilder, Asset, Account, Keypair
from stellar_sdk import TransactionEnvelope  # , Operation, Payment, SetOptions, TextMemo,
from stellar_sdk.sep.federation import resolve_stellar_address

import fb
from MyMTLWalletBot_main import logger
from cryptocode import encrypt, decrypt

# from settings import private_div, private_bod_eur

# https://stellar-sdk.readthedocs.io/en/latest/

public_mtl = "GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V"
public_fond = "GDX23CPGMQ4LN55VGEDVFZPAJMAUEHSHAMJ2GMCU2ZSHN5QF4TMZYPIS"
public_pawnshop = "GDASYWP6F44TVNJKZKQ2UEVZOKTENCJFTWVMP6UC7JBZGY4ZNB6YAVD4"
public_distributor = "GB7NLVMVC6NWTIFK7ULLEQDF5CBCI2TDCO3OZWWSFXQCT7OPU3P4EOSR"

public_bod_eur = "GDEK5KGFA3WCG3F2MLSXFGLR4T4M6W6BMGWY6FBDSDQM6HXFMRSTEWBW"
public_bod = "GARUNHJH3U5LCO573JSZU4IOBEVQL6OJAAPISN4JKBG2IYUGLLVPX5OH"
public_div = "GDNHQWZRZDZZBARNOH6VFFXMN6LBUNZTZHOKBUT7GREOWBTZI4FGS7IQ"

xlm_asset = Asset("XLM")
mtl_asset = Asset("MTL", public_mtl)
eurmtl_asset = Asset("EURMTL", public_mtl)


def stellar_add_trust(user_key: str, asset: Asset, xdr: str = None):
    if xdr:
        transaction = TransactionBuilder.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
    else:
        server = Server(horizon_url="https://horizon.stellar.org")
        source_account = server.load_account(user_key)
        transaction = TransactionBuilder(source_account=source_account,
                                         network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE, base_fee=100)
    transaction.append_change_trust_op(asset)
    transaction = transaction.build()

    xdr = transaction.to_xdr()
    # print(f"xdr: {xdr}")
    return xdr


def stellar_sign(xdr: str, private_key: str):
    transaction = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
    transaction.sign(private_key)
    return transaction.to_xdr()


def get_url_xdr(url):
    rq = requests.get(url).text
    rq = rq[rq.find('<span class="tx-body">') + 22:]
    # print(rq)
    rq = rq[:rq.find('</span>')]
    rq = rq.replace("&#x3D;", "=")
    # print(rq)
    return rq


def stellar_check_xdr(xdr: str):
    result = None
    "https://mtl.ergvein.net/view?tid=7ec5e397140fadf0d384860a35d19cf9f60e00a49b3b2cc250b832076fab7e7f"
    try:
        if xdr.find('mtl.ergvein.net/view') > -1:
            xdr = get_url_xdr(xdr)
            result = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE).to_xdr()
        else:
            result = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE).to_xdr()

    except Exception as ex:
        print('stellar_check_xdr', xdr, ex)
    return result


def stellar_user_sign(xdr: str, user_id: int, user_password: str):
    user_keypair = stellar_get_user_keypair(user_id, user_password)
    return stellar_sign(xdr, user_keypair.secret)


def stellar_send(xdr: str):
    transaction = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
    server = Server(horizon_url="https://horizon.stellar.org")
    transaction_resp = server.submit_transaction(transaction)
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
    xdr = stellar_pay(master.public_key, new_account.public_key, xlm_asset, 3, create=1)
    stellar_send(stellar_sign(xdr, master.secret))

    xdr = stellar_add_trust(new_account.public_key, mtl_asset)
    xdr = stellar_add_trust(new_account.public_key, eurmtl_asset, xdr=xdr)
    stellar_send(stellar_sign(xdr, new_account.secret))


def stellar_pay(from_account: str, for_account: str, asset: Asset, amount: float, create: int = 0):
    source_account = Server(horizon_url="https://horizon.stellar.org").load_account(from_account)
    transaction = TransactionBuilder(source_account=source_account,
                                     network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE, base_fee=100)
    if create == 1:
        transaction.append_create_account_op(destination=for_account, starting_balance=str(round(amount, 7)))
        transaction.add_text_memo('New account MyMTLWalletbot')
    else:
        transaction.append_payment_op(destination=for_account, amount=str(round(amount, 7)), asset=asset)
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
    return Server(horizon_url="https://horizon.stellar.org").load_account(result)


def stellar_get_master() -> Keypair:
    return stellar_get_user_keypair(0, '0')


def stellar_can_new(user_id: int):
    result = fb.execsql1(f"select count(*) from mymtlwalletbot m where m.user_id = {user_id} and m.free_wallet = 1")
    if int(result) > 2:
        return False
    else:
        return True


def stellar_delete_account(master_account: Keypair, delete_account: Keypair):
    print('delete_account', delete_account.public_key)
    source_account = Server(horizon_url="https://horizon.stellar.org").load_account(master_account)
    transaction = TransactionBuilder(source_account=source_account,
                                     network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE, base_fee=100)
    account = Server(horizon_url="https://horizon.stellar.org").accounts().account_id(delete_account.public_key).call()
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


def stellar_get_balance(user_id: int, public_key=None):
    user_account = stellar_get_user_account(user_id, public_key)
    free_wallet = fb.execsql1(f"select m.free_wallet from mymtlwalletbot m where m.user_id = {user_id} "
                              f"and m.public_key = '{user_account.account.account_id}'")
    account = Server(horizon_url="https://horizon.stellar.org").accounts().account_id(
        user_account.account.account_id).call()
    result = ''
    for balance in account['balances']:
        if (balance['asset_type'] == "native") and (free_wallet == 0):
            result += f"XLM : {balance['balance']}\n"
        elif balance['asset_type'][:15] == "credit_alphanum":
            result += f"{balance['asset_code']} : {balance['balance']}\n"
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
    return free_wallet


def stellar_get_balance_list(user_id: int, asset_filter: str = None):
    user_account = stellar_get_user_account(user_id)
    free_wallet = fb.execsql1(f"select m.free_wallet from mymtlwalletbot m where m.user_id = {user_id} "
                              f"and m.public_key = '{user_account.account.account_id}'")
    account = Server(horizon_url="https://horizon.stellar.org").accounts().account_id(
        user_account.account.account_id).call()
    result = []
    for balance in account['balances']:
        if (balance['asset_type'] == "native") and (free_wallet == 0):
            result.append(
                ['XLM', balance['balance'], 'XLM', None])
        elif balance['asset_type'][:15] == "credit_alphanum":
            if asset_filter:
                pass
            else:
                result.append(
                    [balance['asset_code'], balance['balance'], balance['asset_code'], balance['asset_issuer']])
    return result


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
        return Server(horizon_url="https://horizon.stellar.org").load_account(public_key)
    except Exception as ex:
        print("stellar_check_account", public_key, ex)


if __name__ == "__main__":
    pass

    # decode
    # print(decrypt('', '3213541654'))
    # print(encrypt('', '32165432154'))

    # gen new
    # new_account = Keypair.random()
    # while new_account.public_key[-3:] != 'MTL':
    #    new_account = Keypair.random()
    # print(new_account.public_key, new_account.secret)

    # delete
    # stellar_delete_account(Keypair.from_secret("**"),
    #                       Keypair.from_secret("**"))

    #xdr = stellar_check_xdr(
    #    "https://mtl.ergvein.net/view?tid=ba0f728a8f0c62609a34789b2283ed70e60875c5ff91827a0b375f98b4bf3c9a")
    #print({"tx_body": xdr})
    #rq = requests.post("https://mtl.ergvein.net/update", data={"tx_body": xdr})
    #result = rq.text[rq.text.find('<section id="main">'):rq.text.find("</section>")]
    #print(result)
