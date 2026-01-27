# other/stellar/balance_utils.py
"""Balance queries and account information utilities."""

from typing import Optional
from decimal import Decimal

import aiohttp
from stellar_sdk import Asset
from stellar_sdk.client.aiohttp_client import AiohttpClient
from stellar_sdk.server_async import ServerAsync

from other.config_reader import config
from .constants import MTLAssets


async def stellar_get_account(account_id: str) -> dict:
    """
    Get account details from Stellar network.

    Args:
        account_id: Stellar public key

    Returns:
        Account data dict or error dict with 'type' key
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{config.horizon_url}/accounts/{account_id}') as resp:
            return await resp.json()


async def stellar_get_issuer_assets(account_id: str) -> dict:
    """
    Get all assets issued by account with their amounts.

    Args:
        account_id: Issuer account public key

    Returns:
        Dict of {asset_code: total_amount}
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{config.horizon_url}/assets?limit=200&asset_issuer={account_id}') as resp:
            data = await resp.json()
            assets = {}
            if data.get('type'):  # Error response
                return {}
            else:
                for balance in data['_embedded']['records']:
                    balances = balance['balances']
                    assets[balance['asset_code']] = (
                        float(balances['authorized']) +
                        float(balance.get('claimable_balances_amount', 0)) +
                        float(balance.get('liquidity_pools_amount', 0)) +
                        float(balance.get('contracts_amount', 0))
                    )
                return assets


async def get_balances(
    address: str,
    return_assets: bool = False,
    return_data: bool = False,
    return_signers: bool = False,
    account_json: Optional[dict] = None
) -> dict | tuple:
    """
    Get all asset balances for account.

    Args:
        address: Stellar public key
        return_assets: If True, return Asset objects as keys instead of codes
        return_data: If True, also return account data
        return_signers: If True, also return account signers
        account_json: Optional pre-fetched account data

    Returns:
        Dict of {asset_code: balance} or tuple with additional data
    """
    if account_json:
        account = account_json
    else:
        account = await stellar_get_account(address)

    assets = {}
    if account.get('type'):  # Error response
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


async def stellar_get_holders(
    asset: Asset = MTLAssets.mtl_asset,
    mini: bool = False
) -> list[dict]:
    """
    Get all holders of specific asset.

    Args:
        asset: Asset to query (defaults to MTL)
        mini: If True, return only first page

    Returns:
        List of account records
    """
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

        return accounts


async def stellar_get_token_amount(asset: Asset = MTLAssets.mtl_asset) -> str:
    """
    Get total supply of token.

    Args:
        asset: Asset to query (defaults to MTL)

    Returns:
        Total token supply as string
    """
    async with ServerAsync(horizon_url=config.horizon_url) as server:
        assets = await server.assets().for_code(asset.code).for_issuer(asset.issuer).call()
        return assets['_embedded']['records'][0]['amount']


async def stellar_get_all_mtl_holders() -> list:
    """
    Get all holders of MTL and MTLRECT assets.

    Returns:
        List of unique account records
    """
    accounts = []
    for asset in (MTLAssets.mtl_asset, MTLAssets.mtlrect_asset):
        asset_accounts = await stellar_get_holders(asset)
        for account in asset_accounts:
            if account not in accounts:
                accounts.append(account)
    return accounts


async def get_pool_info(pool_id: str, session) -> dict:
    """
    Get liquidity pool information from Horizon.

    Args:
        pool_id: Liquidity pool ID
        session: aiohttp ClientSession

    Returns:
        Pool information dict
    """
    async with session.get(f'{config.horizon_url}/liquidity_pools/{pool_id}') as resp:
        return await resp.json()


async def get_pool_balances(address: str) -> list:
    """
    Get liquidity pool balances for an address.

    Args:
        address: Stellar address

    Returns:
        List of pool information dicts with user's share details:
        {
            'pool_id': str,
            'name': 'TOKEN1-TOKEN2',
            'shares': float,
            'token1_amount': float,
            'token2_amount': float
        }
    """
    account = await stellar_get_account(address)
    pools = []

    async with aiohttp.ClientSession() as session:
        for balance in account['balances']:
            if balance['asset_type'] == 'liquidity_pool_shares':
                pool_id = balance['liquidity_pool_id']
                user_shares = float(balance['balance'])

                # Get pool details
                pool_info = await get_pool_info(pool_id, session)
                total_shares = float(pool_info['total_shares'])

                # Calculate user's share percentage
                user_share_percentage = user_shares / total_shares

                # Extract reserve information
                reserves = pool_info['reserves']
                token1 = reserves[0]
                token2 = reserves[1]

                # Calculate user's token amounts
                user_token1_amount = float(token1['amount']) * user_share_percentage
                user_token2_amount = float(token2['amount']) * user_share_percentage

                # Build pool name
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


async def check_mtlap(key: str) -> str:
    """
    Check MTLAP balance for an address.

    Args:
        key: Stellar public key

    Returns:
        String with MTLAP balance or 'not found' message
    """
    balances = await get_balances(address=key)

    if 'MTLAP' in balances:
        return f'Баланс MTLAP: {balances["MTLAP"]}'

    return 'MTLAP не найден'
