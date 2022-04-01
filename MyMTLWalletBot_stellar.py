from stellar_sdk import Network, Server, TransactionBuilder, Asset, Account, Keypair
from stellar_sdk import TransactionEnvelope  # , Operation, Payment, SetOptions, TextMemo,
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


def stellar_check_xdr(xdr: str):
    result = None
    try:
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
    else:
        transaction.append_payment_op(destination=for_account, amount=str(round(amount, 7)), asset=asset)
    transaction.add_text_memo('New account MyMTLWalletbot')
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


def stellar_get_balance_list(user_id: int):
    user_account = stellar_get_user_account(user_id)
    free_wallet = fb.execsql1(f"select m.free_wallet from mymtlwalletbot m where m.user_id = {user_id} "
                              f"and m.public_key = '{user_account.account.account_id}'")
    account = Server(horizon_url="https://horizon.stellar.org").accounts().account_id(
        user_account.account.account_id).call()
    result = []
    for balance in account['balances']:
        if (balance['asset_type'] == "native") and (free_wallet == 0):
            result.append(
                ['XLM', balance['balance'], Asset('XLM', None)])
        elif balance['asset_type'][:15] == "credit_alphanum":
            result.append(
                [balance['asset_code'], balance['balance'], Asset(balance['asset_code'], balance['asset_issuer'])])
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
        return Server(horizon_url="https://horizon.stellar.org").load_account(public_key)
    except Exception as ex:
        print("stellar_check_account", public_key, ex)


if __name__ == "__main__":
    pass

    print(decrypt(
        'oxb/mtZxmBrYkEECyJ3kg8NS0i+OpnCzoq56Qx+7lHzDblEdQtV7yBgb3gLmGbSeUMYIKx2TZbY=*xWePf7DfSuemS+Xztyz54A==*XgTmdN0JRfmUrmEbusHwzg==*2K4/dQQPiz+AIErDR1fTog==',
        '466CCC'))

    # stellar_delete_account(Keypair.from_secret("SAGI2JR4CFDEFCDMH5L6PWE7UQPBODN3UKEGDFLAH5K7DPHWKPZZHOVP"),
    #                       Keypair.from_secret("SAIALXYAYAR5NP2J5MQKZMEM6DJOITGCPKGL4BMHRKWLAP6E7S2GK5FX"))

    # account = Server(horizon_url="https://horizon.stellar.org").load_account('attid*lobstr.co')
    # account = stellar_get_master()
    # account = Server(horizon_url="https://horizon.stellar.org").load_account(account3)
    # print(type(account))
    # print(encrypt('SAGI2JR4CFDEFCDMH5L6PWE7UQPBODN3UKEGDFLAH5K7DPHWKPZZHOVP','0'))
    # print(encrypt('SBMF2SLBON74N6DNQLS5NHWDOTMC4CPOFOI7NVHLUQVKQ3T2NVVTZABI','84131737'))
    # print(encrypt('SC7L3J4MO7W3GV4ODKCOZXYNF7RBKR2R5N45HT2DKOXS4X6A3KW4NI2T','84131737'))
    # stellar_create_new(84131737, 4)

    # xdr = stellar_add_fond_trustline('GC5MOXE2BI6NUUHDDJRTMQYSDF4GY46G2OQDHYOWNVE4PZDJBYIAQQLY','EURMTL')
    # print(xdr)
    # xdr = stellar_sign(xdr, 'SAGI2JR4CFDEFCDMH5L6PWE7UQPBODN3UKEGDFLAH5K7DPHWKPZZHOVP')
    # print(xdr)
    # xdr = stellar_send(xdr)
    # print(xdr)
    # account = server.accounts().account_id(public_key).call()
    # for balance in account['balances']:

    # = "GD5WQZDL7TUYB3ZOYOVPZFDTWZUW54PIDFNTS5YYX5AXWD2ILI5EKPDX"
    # response = requests.get(f"https://friendbot.stellar.org?addr={public_key}")
    # if response.status_code == 200:
    #    print(f"SUCCESS! You have a new account :)\n{response.text}")
    # else:
    #    print(f"ERROR! Response: \n{response.text}")
    # print(f"Type: {balance['asset_type']}, Balance: {balance['balance']}")
    xdr = stellar_check_xdr('AAAAAgAAAADXM/FKYDkdJMoH7qR0azpDSfND7E9VelL2D5ys9ViskAAAAGQCGVTNAAAA1wAAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEAAAAAAAAAAQAAAACe6w4QHWQIGTfNtks96epEXipzOHDQ8p3gFQqNebrXhgAAAAJERUJURVVSAAAAAAAAAAAA1zPxSmA5HSTKB+6kdGs6Q0nzQ+xPVXpS9g+crPVYrJAAAAAKZoobgAAAAAAAAAAA')
