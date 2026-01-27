# other/stellar/asset_xdr.py
"""Asset-specific XDR generation functions for dividends and payments."""

from datetime import datetime, timedelta

from stellar_sdk import TransactionBuilder

from .sdk_utils import load_account_async, get_network_passphrase, get_server_async
from other.gspread_tools import gs_get_chicago_premium
from .constants import MTLAddresses, MTLAssets, BASE_FEE
from .balance_utils import stellar_get_holders


def _determine_working_range():
    """
    Determine the working date range for Chicago cashback calculations.

    Returns:
        tuple: (start_range, end_range) datetime objects
    """
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


async def _stellar_get_transactions(address, start_range, end_range):
    """
    Get transactions for an address within a date range.

    Args:
        address: Stellar account address
        start_range: Start datetime
        end_range: End datetime

    Returns:
        list: Transaction records within the range
    """
    transactions = []
    async with get_server_async() as server:
        payments_call_builder = server.payments().for_account(account_id=address).limit(200).order()
        page_records = await payments_call_builder.call()
        while page_records["_embedded"]["records"]:
            for record in page_records["_embedded"]["records"]:
                tx_date = datetime.strptime(record['created_at'], "%Y-%m-%dT%H:%M:%SZ")
                if tx_date < start_range:
                    return transactions
                if start_range.date() <= tx_date.date() <= end_range.date():
                    transactions.append(record)
            page_records = await payments_call_builder.next()

    return transactions


async def get_damircoin_xdr(div_sum: int):
    """
    Generate XDR for DamirCoin dividend distribution.

    Calculates dividend payments proportional to token holdings.

    Args:
        div_sum: Total dividend sum to distribute in EURMTL

    Returns:
        str: Unsigned XDR envelope
    """
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

    root_account = await load_account_async(MTLAddresses.public_damir)
    transaction = TransactionBuilder(source_account=root_account, network_passphrase=get_network_passphrase(),
                                     base_fee=BASE_FEE)
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
    """
    Generate XDR for AGORA dividend distribution.

    Calculates 2% dividend payments proportional to token holdings.

    Returns:
        str: Unsigned XDR envelope
    """
    accounts = await stellar_get_holders(MTLAssets.agora_asset)
    accounts_list = []
    total_sum = 0

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

    root_account = await load_account_async(MTLAssets.agora_asset.issuer)
    transaction = TransactionBuilder(source_account=root_account, network_passphrase=get_network_passphrase(),
                                     base_fee=BASE_FEE)
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
    """
    Generate XDR for TOC dividend distribution.

    Calculates dividend payments proportional to token holdings,
    excluding the token issuer account.

    Args:
        div_sum: Total dividend sum to distribute in EURMTL

    Returns:
        str: Unsigned XDR envelope
    """
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

    root_account = await load_account_async(MTLAssets.toc_asset.issuer)
    transaction = TransactionBuilder(source_account=root_account, network_passphrase=get_network_passphrase(),
                                     base_fee=BASE_FEE)
    transaction.set_timeout(60 * 60 * 24 * 7)
    for account in accounts_list:
        if account[2] > 0.0001:
            transaction.append_payment_op(destination=account[0], asset=MTLAssets.eurmtl_asset,
                                          amount=str(round(account[2], 7)))
    transaction = transaction.build()
    xdr = transaction.to_xdr()

    return xdr


async def get_btcmtl_xdr(btc_sum, address: str, memo=None):
    """
    Generate XDR for BTCMTL payment with corresponding BTCDEBT.

    Creates a transaction that issues BTCDEBT to guards and
    sends BTCMTL to the specified address.

    Args:
        btc_sum: Amount to send
        address: Destination Stellar address
        memo: Optional text memo

    Returns:
        str: Unsigned XDR envelope
    """
    root_account = await load_account_async(MTLAddresses.public_issuer)
    transaction = TransactionBuilder(source_account=root_account, network_passphrase=get_network_passphrase(),
                                     base_fee=BASE_FEE)
    transaction.set_timeout(60 * 60 * 24 * 7)
    transaction.append_payment_op(destination=MTLAddresses.public_btc_guards, asset=MTLAssets.btcdebt_asset,
                                  amount=btc_sum)
    transaction.append_payment_op(destination=address, asset=MTLAssets.btcmtl_asset, amount=btc_sum)
    if memo:
        transaction.add_text_memo(memo)
    transaction = transaction.build()
    xdr = transaction.to_xdr()

    return xdr


async def get_chicago_xdr():
    """
    Generate XDR for Chicago premium cashback distribution.

    Calculates cashback based on incoming EURMTL transactions:
    - 13% for regular users
    - 26% for premium users

    Returns:
        list: Results including date range, statistics, and XDR envelope
    """
    result = []
    start_range, end_range = _determine_working_range()

    result.append(f'Ищем транзакции с {start_range.strftime("%Y-%m-%d")} по {end_range.strftime("%Y-%m-%d")}')
    accounts_dict = {}

    stellar_address = 'GD6HELZFBGZJUBCQBUFZM2OYC3HKWDNMC3PDTTDGB7EY4UKUQ2MMELSS'

    premium_list = await gs_get_chicago_premium()
    result.append(f'Получено премиум пользователей: {len(premium_list)}')

    transactions = await _stellar_get_transactions(stellar_address, start_range, end_range)
    result.append(f'Получено транзакций в диапазоне: {len(transactions)}')

    for transaction in transactions:
        if (transaction.get('asset_code') == MTLAssets.eurmtl_asset.code
                and transaction.get('asset_issuer') == MTLAssets.eurmtl_asset.issuer):
            if transaction['to'] != transaction['from'] and transaction['to'] == stellar_address:
                accounts_dict[transaction['from']] = (float(transaction['amount']) +
                                                      accounts_dict.get(transaction['from'], 0))

    root_account = await load_account_async(stellar_address)
    transaction = TransactionBuilder(source_account=root_account, network_passphrase=get_network_passphrase(),
                                     base_fee=BASE_FEE)
    transaction.set_timeout(60 * 60 * 24 * 7)
    transaction.add_text_memo('cashback')
    total_sum = 0
    total_income_sum = 0
    premium_sum = 0
    for account in accounts_dict:
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
    result.append(f'Премиум пользователей: {num_premium_accounts} обычных пользователей: {num_regular_accounts}')
    result.append(f'Premium sum: {premium_sum} Total sum: {total_sum}')
    result.append(xdr)

    return result
