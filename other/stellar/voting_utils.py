# other/stellar/voting_utils.py
"""Voting and governance utilities for MTL ecosystem."""

import math
from copy import deepcopy
from datetime import datetime, timedelta

from loguru import logger
from stellar_sdk import Account, TransactionBuilder

from .sdk_utils import load_account_async, get_network_passphrase, get_server, get_server_async
from other.grist_tools import MTLGrist, grist_manager
from other.web_tools import http_session_manager
from other.mytypes import MyShareHolder

from .constants import BASE_FEE, MTLAddresses, MTLAssets
from .balance_utils import stellar_get_account, stellar_get_all_mtl_holders, stellar_get_holders
from .xdr_utils import decode_data_value


async def cmd_get_blacklist() -> dict:
    """
    Fetch the MTL blacklist from GitHub.

    Returns:
        Dictionary of blacklisted addresses
    """
    response = await http_session_manager.get_web_request(
        'GET',
        url='https://raw.githubusercontent.com/montelibero-org/mtl/main/json/blacklist.json',
        return_type='json'
    )
    if isinstance(response.data, dict):
        return response.data
    raise ValueError('Invalid blacklist response format')


def check_mtla_delegate(account: str, result: dict, delegated_list: list = None):
    """
    Recursively check and resolve MTLA delegation chains.

    Args:
        account: Account ID to check
        result: Dictionary of all accounts and their delegation info
        delegated_list: List of accounts in current delegation chain (for cycle detection)

    Returns:
        Final delegate account ID or None
    """
    if delegated_list is None:
        delegated_list = []
    delegate_to_account = result[account]['delegate']
    # Remove self-delegation cycle
    if delegate_to_account and delegate_to_account == account:
        result[account]['delegate'] = None
        return

    # Remove larger delegation cycle
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


async def cmd_get_new_vote_all_mtl(public_key: str, remove_master: bool = False) -> list:
    """
    Generate voting XDR transactions for MTL accounts.

    If public_key is a full Stellar address (>10 chars), generates XDR for that single account.
    Otherwise, generates XDR for all multisp accounts from Grist.

    Args:
        public_key: Stellar public key or short identifier
        remove_master: Whether to remove master key weight

    Returns:
        List of XDR transaction strings
    """
    if len(public_key) > 10:
        vote_list = await cmd_gen_mtl_vote_list()
        result = [gen_vote_xdr(public_key, vote_list, remove_master=remove_master, source=public_key)]
    else:
        vote_list = await cmd_gen_mtl_vote_list()
        accounts = await grist_manager.load_table_data(
            MTLGrist.EURMTL_accounts,
            filter_dict={"signers_type": ['multisp']}
        )

        result = []
        source_account = await load_account_async(MTLAddresses.public_issuer)
        transaction = TransactionBuilder(
            source_account=source_account,
            network_passphrase=get_network_passphrase(), base_fee=BASE_FEE)
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

    return result


async def cmd_gen_mtl_vote_list(trim_count: int = 20, delegate_list: dict = None) -> list[MyShareHolder]:
    """
    Generate MTL signer vote list based on MTLRECT holdings.

    Calculates voting power based on token balance, delegation, and applies
    vote weight normalization to ensure no single holder has >36% of votes.

    Args:
        trim_count: Maximum number of shareholders to return
        delegate_list: Optional pre-existing delegation mapping

    Returns:
        List of MyShareHolder objects sorted by voting power
    """
    if delegate_list is None:
        delegate_list = {}
    shareholder_list = []

    # Get current signers from issuer account
    source_account = await load_account_async(MTLAddresses.public_issuer)
    sg = source_account.load_ed25519_public_key_signers()

    # Create dictionary for quick signer lookup
    signer_weights = {s.account_id: s.weight for s in sg}

    accounts = await stellar_get_all_mtl_holders()

    # mtl
    for account in accounts:
        balances = account["balances"]
        balance_mtl = 0  # no votes from 2025
        balance_rect = 0

        for balance in balances:
            if balance["asset_type"][0:15] == "credit_alphanum":
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

    # Filter shareholder_list, keeping only accounts with balance >= 1
    shareholder_list = [sh for sh in shareholder_list if sh.balance >= 1]

    # Sort shareholder_list by balance descending
    shareholder_list.sort(key=lambda sh: sh.balance, reverse=True)

    # Find delegate
    for shareholder in shareholder_list:
        if shareholder.data:
            data = shareholder.data
            for data_name in list(data):
                data_value = data[data_name]
                if data_name in ('delegate', 'mtl_delegate'):
                    delegate_list[shareholder.account_id] = decode_data_value(data_value)

    # Multi-step delegation
    max_steps = 3  # Maximum delegation steps

    for step in range(max_steps):
        changes_made = False
        temp_delegate_list = delegate_list.copy()  # Create copy for safe modification

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

        # Update delegate_list only after iteration completes
        delegate_list = temp_delegate_list

        # If no changes were made, break the loop
        if not changes_made:
            break

    # Clear delegate_list after all steps complete
    delegate_list.clear()

    # Delete blacklist user
    bl = await cmd_get_blacklist()
    # Process blacklist for shareholder_list
    for shareholder in shareholder_list:
        if bl.get(shareholder.account_id):
            # Zero out corresponding values
            shareholder.balance_mtl = 0
            shareholder.balance_rect = 0
            shareholder.balance_delegated = 0

    # Sort shareholder_list by balance descending
    shareholder_list.sort(key=lambda sh: sh.balance, reverse=True)

    # Filter participants with MTLRECT balance >= 500 for vote calculation
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
                    1 - (1.74 - (big_vote - total_vote / 3) / total_vote) * (big_vote - total_vote / 3) / total_vote))

        major_percent = eligible_shareholders[0].calculated_votes / sum(
            sh.calculated_votes for sh in eligible_shareholders) * 100
        if major_percent < 33 or major_percent > 36:
            logger.warning(f"Warning! Major has {major_percent:.2f}% votes (outside 33-36% range)")
        else:
            logger.info(f"Major has {major_percent:.2f}% votes (within 33-36% range)")

        # Update calculated_votes in main shareholder_list
        # Create dictionary for quick lookup of calculated votes
        calculated_votes_dict = {sh.account_id: sh.calculated_votes for sh in eligible_shareholders}

        # Update calculated_votes for all participants in main list
        for shareholder in shareholder_list:
            if shareholder.account_id in calculated_votes_dict:
                shareholder.calculated_votes = calculated_votes_dict[shareholder.account_id]
            else:
                shareholder.calculated_votes = 0  # Participants without voting rights get 0

    # Double sort: first by calculated_votes, then by votes, then by balance
    shareholder_list.sort(key=lambda sh: (sh.calculated_votes, sh.votes, sh.balance), reverse=True)

    return shareholder_list[:trim_count]


async def cmd_gen_fin_vote_list(account_id: str = MTLAddresses.public_fin) -> list:
    """
    Generate FIN signer vote list based on donation history.

    Analyzes payment history to the FIN account, considering:
    - Payments in the last 365 days
    - Inactive donors (>90 days since last donation) are excluded
    - Top 10 donors get voting power based on log2 of normalized donations

    Args:
        account_id: The FIN account to analyze donations to

    Returns:
        List of [donor_id, total_sum, votes, 0, last_donation_date]
    """
    delegate_key = "tfm_delegate"
    days_to_track = 365
    days_inactive = 90
    top_donors = 10
    coefficients = [12, 5]

    # Step 1
    now = datetime.now()
    one_year_ago = now - timedelta(days=days_to_track)

    donor_dict = {}

    async with get_server_async() as server:
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


def gen_vote_xdr(
    public_key: str,
    vote_list: list[MyShareHolder],
    transaction: TransactionBuilder = None,
    source: str = None,
    remove_master: bool = False,
    max_count: int = 20,
    threshold_style: int = 0
) -> str:
    """
    Create SetOptions XDR with signers for voting.

    Updates the account's signers based on calculated voting weights and
    sets appropriate thresholds.

    Args:
        public_key: Account to update signers for
        vote_list: List of shareholders with calculated votes
        transaction: Optional existing transaction builder to append to
        source: Source account for operations
        remove_master: Whether to set master key weight to 0
        max_count: Maximum number of signers to include
        threshold_style: 0 for 50%+1 threshold, 1 for 2/3 threshold

    Returns:
        XDR transaction string
    """
    # Find out who is in signers
    server = get_server()
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

    # Move users to delete to top
    tmp_list = []
    del_count = 0

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

    server = get_server()
    source_account = server.load_account(public_key)
    root_account = Account(public_key, sequence=source_account.sequence)
    if transaction is None:
        transaction = TransactionBuilder(source_account=root_account,
                                         network_passphrase=get_network_passphrase(), base_fee=BASE_FEE)
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

    return xdr


async def get_mtlap_votes() -> dict:
    """
    Get MTLAP governance votes with delegation resolution.

    Builds a voting tree based on MTLAP token holdings and delegation chains.
    Accounts need at least 2 MTLAP to vote or have delegators with 2+ MTLAP.

    Returns:
        Dictionary mapping account_id to voting info:
        {
            'delegate': delegate account or None,
            'vote': MTLAP balance,
            'can_vote': True if can participate in governance,
            'delegated_list': list of accounts that delegated to this one
        }
    """
    result = {}
    # Build tree based on holders
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

    # Add accounts that don't exist yet
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

    # Check if account can vote
    for account in list(result):
        if not result[account]['can_vote']:
            # Check if there are delegators with 2 or more tokens
            if 'delegated_list' in result[account]:
                for delegator in result[account]['delegated_list']:
                    if result[delegator]['vote'] >= 2:
                        result[account]['can_vote'] = True
                        break

    # Remove accounts that cannot vote
    for account in list(result):
        if not result[account]['can_vote']:
            del result[account]

    del result['GDGC46H4MQKRW3TZTNCWUU6R2C7IPXGN7HQLZBJTNQO6TW7ZOS6MSECR']
    del result['GCNVDZIHGX473FEI7IXCUAEXUJ4BGCKEMHF36VYP5EMS7PX2QBLAMTLA']

    return result


async def stellar_add_mtl_holders_info(accounts: list[MyShareHolder]):
    """
    Enrich account list with signer weight information from MTL issuer.

    Updates the votes attribute of each account in the list based on
    their signer weight on the MTL issuer account.

    Args:
        accounts: List of MyShareHolder objects to update
    """
    async with get_server_async() as server:
        source_account = await server.load_account(MTLAddresses.public_issuer)
        sg = source_account.load_ed25519_public_key_signers()

    # Create dictionary for quick weight lookup by account_id
    signer_weights = {s.account_id: s.weight for s in sg}

    # Update votes for accounts based on signer weights
    for account in accounts:
        if account.account_id in signer_weights:
            account.votes = signer_weights[account.account_id]
