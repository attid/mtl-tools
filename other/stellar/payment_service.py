# other/stellar/payment_service.py
"""Payment operations: send payments, submit transactions."""

from typing import Optional

from stellar_sdk import (
    Asset,
    Network,
    TransactionBuilder,
    TransactionEnvelope,
)
from stellar_sdk.client.aiohttp_client import AiohttpClient
from stellar_sdk.server_async import ServerAsync

from other.config_reader import config
from .sdk_utils import get_private_sign


async def send_payment_async(
    source_address: str,
    destination: str,
    asset: Asset,
    amount: str,
    memo_text: Optional[str] = None
) -> dict:
    """
    Builds, signs and submits a payment transaction.

    Args:
        source_address: Source account public key
        destination: Destination public key
        asset: Asset to send
        amount: Amount to send
        memo_text: Optional text memo (max 28 chars)

    Returns:
        Transaction response dict
    """
    async with ServerAsync(
        horizon_url=config.horizon_url, client=AiohttpClient()
    ) as async_server:
        source_account = await async_server.load_account(source_address)

    builder = TransactionBuilder(
        source_account=source_account,
        network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
        base_fee=config.base_fee,
    )
    builder.set_timeout(60)
    if memo_text:
        builder.add_text_memo(memo_text[:28])
    builder.append_payment_op(
        destination=destination,
        asset=asset,
        amount=str(amount),
    )
    transaction = builder.build()
    transaction.sign(get_private_sign())
    return await stellar_async_submit(transaction.to_xdr())


async def stellar_async_submit(xdr: str) -> dict:
    """
    Submit signed XDR transaction to Stellar network asynchronously.

    Args:
        xdr: Signed transaction XDR

    Returns:
        Submission response dict
    """
    async with ServerAsync(
        horizon_url=config.horizon_url, client=AiohttpClient()
    ) as server:
        transaction = TransactionEnvelope.from_xdr(
            xdr,
            network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE
        )
        return await server.submit_transaction(transaction)


async def stellar_sync_submit(xdr: str) -> dict:
    """
    Submit signed XDR transaction synchronously.

    Args:
        xdr: Signed transaction XDR

    Returns:
        Submission response dict
    """
    async with ServerAsync(
        horizon_url=config.horizon_url, client=AiohttpClient()
    ) as server:
        transaction = TransactionEnvelope.from_xdr(
            xdr,
            network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE
        )
        return await server.submit_transaction(transaction)


async def build_batch_payment_xdr(
    source_address: str,
    payments: list[dict],
    memo: Optional[str] = None,
) -> str:
    """
    Build XDR for batch payments.

    Args:
        source_address: Source account public key
        payments: List of {destination, asset, amount} dicts
        memo: Optional text memo

    Returns:
        Unsigned transaction XDR
    """
    async with ServerAsync(
        horizon_url=config.horizon_url, client=AiohttpClient()
    ) as server:
        source_account = await server.load_account(source_address)

    builder = TransactionBuilder(
        source_account=source_account,
        network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
        base_fee=config.base_fee,
    )

    for payment in payments:
        builder.append_payment_op(
            destination=payment["destination"],
            asset=payment["asset"],
            amount=str(payment["amount"]),
        )

    if memo:
        builder.add_text_memo(memo[:28])

    transaction = builder.set_timeout(3600).build()
    return transaction.to_xdr()
