# tests/other/stellar/test_dividend_calc.py
import pytest
from decimal import Decimal
from stellar_sdk import Asset

from other.stellar.dividend_calc import DividendPayment, DividendCalculation


def test_dividend_payment_dataclass():
    payment = DividendPayment(
        address="GTEST1234567890123456789012345678901234567890123456",
        amount=Decimal("100.5"),
        asset=Asset.native(),
    )
    assert payment.address == "GTEST1234567890123456789012345678901234567890123456"
    assert payment.amount == Decimal("100.5")


def test_dividend_calculation_dataclass():
    calc = DividendCalculation(
        payments=[],
        total_amount=Decimal("0"),
        holder_count=0,
        asset=Asset.native(),
    )
    assert calc.holder_count == 0
    assert calc.total_amount == Decimal("0")


def test_dividend_calculation_with_payments():
    payments = [
        DividendPayment(
            address="GADDR1",
            amount=Decimal("50.0"),
            asset=Asset.native(),
        ),
        DividendPayment(
            address="GADDR2",
            amount=Decimal("30.0"),
            asset=Asset.native(),
        ),
    ]
    calc = DividendCalculation(
        payments=payments,
        total_amount=Decimal("80.0"),
        holder_count=2,
        asset=Asset.native(),
    )
    assert calc.holder_count == 2
    assert calc.total_amount == Decimal("80.0")
    assert len(calc.payments) == 2
