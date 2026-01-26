# other/stellar/sdk_utils.py
"""Low-level Stellar SDK utilities: keypair, XDR, server connections."""

from typing import Optional

from stellar_sdk import (
    Keypair,
    Network,
    Server,
    TransactionEnvelope,
    FeeBumpTransactionEnvelope,
)
from stellar_sdk.client.aiohttp_client import AiohttpClient
from stellar_sdk.server_async import ServerAsync

from other.config_reader import config


def get_server() -> Server:
    """Get synchronous Stellar Horizon server connection."""
    return Server(horizon_url=config.horizon_url)


def get_server_async() -> ServerAsync:
    """Get asynchronous Stellar Horizon server connection."""
    return ServerAsync(horizon_url=config.horizon_url, client=AiohttpClient())


def get_private_sign() -> str:
    """Get private signing key from config."""
    return config.private_sign.get_secret_value()


def stellar_sign(xdr: str, sign_key: Optional[str] = None) -> str:
    """
    Sign transaction XDR with keypair.

    Args:
        xdr: Transaction XDR string
        sign_key: Signing key (uses config.private_sign if None)

    Returns:
        Signed XDR string
    """
    if sign_key is None:
        sign_key = config.private_sign.get_secret_value()

    transaction = TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
    transaction.sign(sign_key)
    return transaction.to_xdr()


def gen_new(last_name: str = "") -> list:
    """
    Generate new Stellar keypair with optional suffix matching.

    Args:
        last_name: Optional suffix to match in public key

    Returns:
        List of [iterations, public_key, secret, mnemonic]
    """
    i = 0
    new_account = None
    while True:
        mnemonic = Keypair.generate_mnemonic_phrase()
        try:
            new_account = Keypair.from_mnemonic_phrase(mnemonic)
        except ValueError:
            continue

        if not last_name or new_account.public_key[-len(last_name):] == last_name:
            break

        i += 1

    return [i, new_account.public_key, new_account.secret, mnemonic]


def decode_xdr_envelope(xdr: str) -> TransactionEnvelope:
    """
    Decode XDR string to TransactionEnvelope.

    Args:
        xdr: Transaction XDR string

    Returns:
        TransactionEnvelope or FeeBumpTransactionEnvelope object
    """
    if FeeBumpTransactionEnvelope.is_fee_bump_transaction_envelope(xdr):
        fee_transaction = FeeBumpTransactionEnvelope.from_xdr(
            xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE
        )
        return fee_transaction.transaction.inner_transaction_envelope
    else:
        return TransactionEnvelope.from_xdr(xdr, network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE)
