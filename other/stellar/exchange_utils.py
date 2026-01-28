# other/stellar/exchange_utils.py
"""Exchange operations: swaps, orders, spreads."""

from typing import Optional

from loguru import logger
from stellar_sdk import Asset, Network, Server, TransactionBuilder, Price
from stellar_sdk.exceptions import NotFoundError
from stellar_sdk.client.aiohttp_client import AiohttpClient
from stellar_sdk.server_async import ServerAsync

from other.config_reader import config
from .constants import BASE_FEE, EXCHANGE_BOTS, MTLAssets


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


def stellar_remove_orders(public_key: str, xdr: Optional[str] = None) -> Optional[str]:
    """
    Build XDR to remove all offers for account.

    Args:
        public_key: Account with offers to remove
        xdr: Optional existing XDR to append to

    Returns:
        Transaction XDR or None if no offers
    """
    from .xdr_utils import stellar_get_transaction_builder

    server = Server(horizon_url=config.horizon_url)

    if xdr:
        transaction = stellar_get_transaction_builder(xdr)
    else:
        root_account = server.load_account(public_key)
        transaction = TransactionBuilder(
            source_account=root_account,
            network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
            base_fee=BASE_FEE
        )
        transaction.set_timeout(60 * 60 * 24 * 7)

    call = server.offers().for_account(public_key).limit(200).call()

    for record in call['_embedded']['records']:
        transaction.append_manage_sell_offer_op(
            selling=Asset(
                record['selling'].get('asset_code', 'XLM'),
                record['selling'].get('asset_issuer')
            ),
            buying=Asset(
                record['buying'].get('asset_code', 'XLM'),
                record['buying'].get('asset_issuer')
            ),
            amount='0',
            price=Price(record['price_r']['n'], record['price_r']['d']),
            offer_id=int(record['id']),
            source=public_key
        )

    if transaction.operations:
        transaction = transaction.build()
        xdr = transaction.to_xdr()

    return xdr


def stellar_stop_all_exchange():
    """
    Cancel all open orders for all exchange bots.

    Iterates through EXCHANGE_BOTS and cancels all offers.
    """
    from .sdk_utils import stellar_sign
    from .payment_service import stellar_sync_submit

    xdr = None
    for bot in EXCHANGE_BOTS:
        xdr = stellar_remove_orders(bot, xdr)

    if xdr:
        stellar_sync_submit(stellar_sign(xdr, config.private_sign.get_secret_value()))


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

    except NotFoundError:
        return 0
    except Exception as ex:
        logger.error(f"Error getting trade cost for {asset.code}: {ex}")
        return 0
