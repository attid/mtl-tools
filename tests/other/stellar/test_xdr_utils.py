# tests/other/stellar/test_xdr_utils.py
"""Tests for MASS/SPAM filters in XDR decoding."""

from unittest.mock import AsyncMock, patch

import pytest
from stellar_sdk import Account, Asset, Keypair, Network, TransactionBuilder

from other.stellar.xdr_utils import decode_xdr


def _make_test_xdr(*, source: str, destination: str, op_count: int) -> str:
    source_account = Account(account=source, sequence=1)
    tb = TransactionBuilder(
        source_account=source_account,
        network_passphrase=Network.PUBLIC_NETWORK_PASSPHRASE,
        base_fee=100,
    )
    tb.set_timeout(0)

    for _ in range(op_count):
        tb.append_payment_op(destination=destination, amount="1", asset=Asset.native())

    return tb.build().to_xdr()


@pytest.mark.asyncio
async def test_mass_filter_skips_from_50_when_not_from_filter_account():
    src = Keypair.random().public_key
    dst = Keypair.random().public_key
    xdr = _make_test_xdr(source=src, destination=dst, op_count=50)

    with patch("other.stellar.xdr_utils.address_id_to_username", new=AsyncMock(return_value="@user")):
        # Account is involved (as destination) but is not the tx source.
        res = await decode_xdr(xdr, ignore_operation=["MASS"], filter_account=dst)

    assert res == []


@pytest.mark.asyncio
async def test_mass_filter_does_not_skip_when_from_filter_account():
    src = Keypair.random().public_key
    dst = Keypair.random().public_key
    xdr = _make_test_xdr(source=src, destination=dst, op_count=50)

    with patch("other.stellar.xdr_utils.address_id_to_username", new=AsyncMock(return_value="@user")):
        res = await decode_xdr(xdr, ignore_operation=["MASS"], filter_account=src)

    assert res != []
