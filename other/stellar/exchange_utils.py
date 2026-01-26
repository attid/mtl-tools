# other/stellar/exchange_utils.py
"""Exchange operations: swaps, orders, spreads."""

from typing import Optional

from stellar_sdk import Asset, Network, Server, TransactionBuilder, Price
from stellar_sdk.client.aiohttp_client import AiohttpClient
from stellar_sdk.server_async import ServerAsync

from other.config_reader import config
from .constants import BASE_FEE, MTLAssets


async def stellar_get_offers(account_id: str) -> list[dict]:
    """
    Get all open offers for account.

    Args:
        account_id: Stellar public key

    Returns:
        List of offer dicts
    """
    async with ServerAsync(
        horizon_url=config.horizon_url, client=AiohttpClient()
    ) as server:
        call = await server.offers().for_account(account_id).limit(200).call()
        return call['_embedded']['records']


async def stellar_get_orders_sum(
    address: str,
    selling_asset: Asset,
    buying_asset: Asset
) -> float:
    """
    Calculate total order amount for asset pair.

    Args:
        address: Account address
        selling_asset: Asset being sold
        buying_asset: Asset being bought

    Returns:
        Total amount in selling asset
    """
    orders = await stellar_get_offers(address)
    total_amount = 0.0

    for order in orders:
        selling = order.get('selling', {})
        buying = order.get('buying', {})

        # Check if this order matches the asset pair
        selling_matches = (
            selling.get('asset_type') == selling_asset.type and
            selling.get('asset_code') == selling_asset.code and
            selling.get('asset_issuer') == selling_asset.issuer
        )
        buying_matches = (
            buying.get('asset_type') == buying_asset.type and
            buying.get('asset_code') == buying_asset.code and
            buying.get('asset_issuer') == buying_asset.issuer
        )

        if selling_matches and buying_matches:
            total_amount += float(order['amount'])

    return total_amount


async def get_asset_swap_spread(
    selling_asset: Asset,
    buying_asset: Asset,
    amount: float = 1
) -> tuple[float, float, float]:
    """
    Get spread information for asset pair.

    Args:
        selling_asset: Asset to sell
        buying_asset: Asset to buy
        amount: Amount to use for calculation

    Returns:
        Tuple of (destination_amount_sell_to_buy, source_amount_buy_to_sell, average)
    """
    async with ServerAsync(
        horizon_url=config.horizon_url, client=AiohttpClient()
    ) as server:
        # Calculate amount received when selling
        sell_to_buy = await server.strict_send_paths(
            source_asset=selling_asset,
            source_amount=str(amount),
            destination=[buying_asset]
        ).limit(1).call()

        destination_amount_sell_to_buy = 0.0
        if sell_to_buy['_embedded']['records']:
            destination_amount_sell_to_buy = float(
                sell_to_buy['_embedded']['records'][0]['destination_amount']
            )

        # Calculate amount needed for reverse swap
        buy_to_sell = await server.strict_send_paths(
            source_asset=buying_asset,
            source_amount=str(1 / amount),
            destination=[selling_asset]
        ).limit(1).call()

        source_amount_buy_to_sell = 0.0
        if buy_to_sell['_embedded']['records']:
            dest_amount = float(buy_to_sell['_embedded']['records'][0]['destination_amount'])
            if dest_amount > 0:
                source_amount_buy_to_sell = 1 / dest_amount

        # Calculate average
        average = 0.0
        if destination_amount_sell_to_buy > 0 and source_amount_buy_to_sell > 0:
            average = round((destination_amount_sell_to_buy + source_amount_buy_to_sell) / 2, 5)

        return destination_amount_sell_to_buy, source_amount_buy_to_sell, average


def stellar_get_receive_path(
    send_asset: Asset,
    send_sum: str,
    receive_asset: Asset
) -> list[Asset]:
    """
    Find optimal path for strict send swap.

    Args:
        send_asset: Asset to send
        send_sum: Amount to send
        receive_asset: Asset to receive

    Returns:
        List of intermediate path assets (empty if direct)
    """
    try:
        server = Server(horizon_url=config.horizon_url)
        call_result = server.strict_send_paths(send_asset, send_sum, [receive_asset]).call()

        if len(call_result['_embedded']['records']) > 0:
            path_records = call_result['_embedded']['records'][0]['path']
            if len(path_records) == 0:
                return []

            result = []
            for record in path_records:
                if record['asset_type'] == 'native':
                    result.append(MTLAssets.xlm_asset)
                else:
                    result.append(Asset(record['asset_code'], record['asset_issuer']))
            return result
        else:
            return []
    except Exception:
        return []


def build_swap_xdr(
    source_address: str,
    send_asset: Asset,
    send_amount: str,
    receive_asset: Asset,
    receive_amount: str,
    path: Optional[list[Asset]] = None,
) -> str:
    """
    Build XDR for path payment swap.

    Args:
        source_address: Source account
        send_asset: Asset to send
        send_amount: Amount to send
        receive_asset: Asset to receive
        receive_amount: Minimum amount to receive
        path: Optional intermediate path (auto-calculated if None)

    Returns:
        Unsigned transaction XDR
    """
    server = Server(horizon_url=config.horizon_url)
    source_account = server.load_account(source_address)

    transaction = TransactionBuilder(
        source_account=source_account,
        network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
        base_fee=config.base_fee
    )
    transaction.set_timeout(60 * 60 * 24 * 7)

    if path is None:
        path = stellar_get_receive_path(send_asset, send_amount, receive_asset)

    transaction.append_path_payment_strict_send_op(
        source_address,
        send_asset,
        send_amount,
        receive_asset,
        receive_amount,
        path
    )

    full_transaction = transaction.build()
    return full_transaction.to_xdr()


def build_cancel_offers_xdr(
    public_key: str,
    xdr: Optional[str] = None,
) -> Optional[str]:
    """
    Build XDR to cancel all offers for account.

    Args:
        public_key: Account with offers
        xdr: Optional existing XDR to append to

    Returns:
        Transaction XDR or None if no offers
    """
    from .sdk_utils import decode_xdr_envelope

    server = Server(horizon_url=config.horizon_url)

    if xdr:
        envelope = decode_xdr_envelope(xdr)
        # Get the transaction builder from existing XDR
        root_account = server.load_account(public_key)
        transaction = TransactionBuilder(
            source_account=root_account,
            network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
            base_fee=config.base_fee
        )
        transaction.set_timeout(60 * 60 * 24 * 7)
    else:
        root_account = server.load_account(public_key)
        transaction = TransactionBuilder(
            source_account=root_account,
            network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
            base_fee=config.base_fee
        )
        transaction.set_timeout(60 * 60 * 24 * 7)

    call = server.offers().for_account(public_key).limit(200).call()

    for record in call['_embedded']['records']:
        selling = record['selling']
        buying = record['buying']

        transaction.append_manage_sell_offer_op(
            selling=Asset(
                selling.get('asset_code', 'XLM'),
                selling.get('asset_issuer')
            ),
            buying=Asset(
                buying.get('asset_code', 'XLM'),
                buying.get('asset_issuer')
            ),
            amount='0',
            price=Price(record['price_r']['n'], record['price_r']['d']),
            offer_id=int(record['id']),
            source=public_key
        )

    if transaction.operations:
        built = transaction.build()
        return built.to_xdr()

    return xdr
