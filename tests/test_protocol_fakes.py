# tests/test_protocol_fakes.py
"""Tests for protocol-compatible fake implementations."""
import pytest
from decimal import Decimal
from stellar_sdk import Asset

from tests.fakes import (
    FakeStellarSDK,
    FakeFinanceRepositoryProtocol,
    FakeConfigRepositoryProtocol,
)


@pytest.mark.asyncio
async def test_fake_stellar_sdk_balances():
    sdk = FakeStellarSDK()
    sdk.set_balance("GTEST", "EURMTL", Decimal("100"))

    balances = await sdk.get_balances("GTEST")
    assert balances["EURMTL"] == Decimal("100")


@pytest.mark.asyncio
async def test_fake_stellar_sdk_submit_transaction():
    sdk = FakeStellarSDK()

    result = await sdk.submit_transaction("test_xdr")

    assert "hash" in result
    assert len(sdk.get_submitted_transactions()) == 1
    assert sdk.get_submitted_transactions()[0] == "test_xdr"


@pytest.mark.asyncio
async def test_fake_stellar_sdk_holders():
    sdk = FakeStellarSDK()
    # Use a valid Stellar public key format for the issuer
    asset = Asset("MTL", "GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V")
    holders = [
        {"account_id": "GADDR1", "balance": "100"},
        {"account_id": "GADDR2", "balance": "200"},
    ]
    sdk.set_holders(asset, holders)

    result = await sdk.get_holders(asset)

    assert len(result) == 2
    assert result[0]["account_id"] == "GADDR1"


def test_fake_stellar_sdk_sign():
    sdk = FakeStellarSDK()

    signed = sdk.sign_transaction("xdr_data")

    assert signed == "signed_xdr_data"


def test_fake_finance_repository():
    repo = FakeFinanceRepositoryProtocol()
    repo.save_transaction(1, "xdr_data")

    assert len(repo.transactions) == 1
    assert repo.transactions[0]["xdr"] == "xdr_data"


def test_fake_config_repository():
    repo = FakeConfigRepositoryProtocol()

    repo.save_bot_value(100, "captcha", True)
    result = repo.load_bot_value(100, "captcha")

    assert result is True


def test_fake_config_repository_default():
    repo = FakeConfigRepositoryProtocol()

    result = repo.load_bot_value(100, "nonexistent", "default")

    assert result == "default"


def test_fake_config_repository_get_chat_ids_by_key():
    repo = FakeConfigRepositoryProtocol()
    repo.save_bot_value(100, "captcha", True)
    repo.save_bot_value(200, "captcha", True)
    repo.save_bot_value(300, "moderate", True)

    chat_ids = repo.get_chat_ids_by_key("captcha")

    assert len(chat_ids) == 2
    assert 100 in chat_ids
    assert 200 in chat_ids
