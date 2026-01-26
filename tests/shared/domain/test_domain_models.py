# tests/shared/domain/test_domain_models.py
"""Tests for Payment, Dividend, and BotConfig domain models."""
import pytest
from decimal import Decimal
from datetime import datetime

from shared.domain.payment import Payment, PaymentStatus
from shared.domain.dividend import Dividend, DividendList
from shared.domain.config import BotConfig


class TestPayment:
    def test_payment_default_status(self):
        payment = Payment(id=1, user_key="GADDR", amount=Decimal("100"))
        assert payment.status == PaymentStatus.PENDING
        assert payment.is_pending is True

    def test_payment_is_completed(self):
        payment = Payment(
            id=1,
            user_key="GADDR",
            amount=Decimal("100"),
            status=PaymentStatus.CONFIRMED
        )
        assert payment.is_completed is True
        assert payment.is_pending is False

    def test_payment_with_status(self):
        payment = Payment(id=1, user_key="GADDR", amount=Decimal("100"))
        packed = payment.with_status(PaymentStatus.PACKED)

        assert payment.status == PaymentStatus.PENDING  # original unchanged
        assert packed.status == PaymentStatus.PACKED
        assert packed.id == payment.id

    def test_payment_with_list_id(self):
        payment = Payment(id=1, user_key="GADDR", amount=Decimal("100"))
        assigned = payment.with_list_id(42)

        assert payment.list_id is None  # original unchanged
        assert assigned.list_id == 42

    def test_payment_is_immutable(self):
        payment = Payment(id=1, user_key="GADDR", amount=Decimal("100"))
        with pytest.raises(Exception):
            payment.amount = Decimal("200")


class TestDividend:
    def test_dividend_creation(self):
        div = Dividend(
            address="GADDR",
            amount=Decimal("50.5"),
            asset_code="EURMTL"
        )
        assert div.address == "GADDR"
        assert div.amount == Decimal("50.5")
        assert div.share_percent == Decimal("0")

    def test_dividend_is_immutable(self):
        div = Dividend(address="GADDR", amount=Decimal("100"), asset_code="EURMTL")
        with pytest.raises(Exception):
            div.amount = Decimal("200")


class TestDividendList:
    def test_dividend_list_empty(self):
        div_list = DividendList()
        assert div_list.is_empty is True
        assert div_list.total_amount == Decimal("0")
        assert div_list.holder_count == 0

    def test_dividend_list_add(self):
        div_list = DividendList(memo="Test distribution")
        div_list.add_dividend(Dividend("GADDR1", Decimal("100"), "EURMTL"))
        div_list.add_dividend(Dividend("GADDR2", Decimal("50"), "EURMTL"))

        assert div_list.holder_count == 2
        assert div_list.total_amount == Decimal("150")
        assert div_list.is_empty is False

    def test_dividend_list_filter_by_min_amount(self):
        div_list = DividendList(dividends=[
            Dividend("GADDR1", Decimal("100"), "EURMTL"),
            Dividend("GADDR2", Decimal("50"), "EURMTL"),
            Dividend("GADDR3", Decimal("10"), "EURMTL"),
        ])

        filtered = div_list.filter_by_min_amount(Decimal("50"))

        assert filtered.holder_count == 2
        assert div_list.holder_count == 3  # original unchanged

    def test_dividend_list_get_dividend_for(self):
        div_list = DividendList(dividends=[
            Dividend("GADDR1", Decimal("100"), "EURMTL"),
            Dividend("GADDR2", Decimal("50"), "EURMTL"),
        ])

        found = div_list.get_dividend_for("GADDR1")
        not_found = div_list.get_dividend_for("GADDR3")

        assert found is not None
        assert found.amount == Decimal("100")
        assert not_found is None

    def test_dividend_list_remove(self):
        div_list = DividendList(dividends=[
            Dividend("GADDR1", Decimal("100"), "EURMTL"),
            Dividend("GADDR2", Decimal("50"), "EURMTL"),
        ])

        removed = div_list.remove_dividend("GADDR1")
        not_removed = div_list.remove_dividend("GADDR3")

        assert removed is True
        assert not_removed is False
        assert div_list.holder_count == 1


class TestBotConfig:
    def test_config_get_set(self):
        config = BotConfig(chat_id=100)
        config.set("captcha", True)

        assert config.get("captcha") is True
        assert config.get("nonexistent", "default") == "default"

    def test_config_has(self):
        config = BotConfig(chat_id=100, settings={"captcha": True})

        assert config.has("captcha") is True
        assert config.has("moderate") is False

    def test_config_remove(self):
        config = BotConfig(chat_id=100, settings={"captcha": True})

        removed = config.remove("captcha")
        not_removed = config.remove("nonexistent")

        assert removed is True
        assert not_removed is False
        assert config.has("captcha") is False

    def test_config_typed_accessors(self):
        config = BotConfig(chat_id=100, settings={
            "captcha": True,
            "moderate": False,
            "welcome_message": "Hello!",
            "entry_channel": -1001234567890,
        })

        assert config.captcha_enabled is True
        assert config.moderate_enabled is False
        assert config.welcome_message == "Hello!"
        assert config.entry_channel == -1001234567890
        assert config.no_first_link is False  # default

    def test_config_keys(self):
        config = BotConfig(chat_id=100, settings={
            "captcha": True,
            "moderate": True,
        })

        keys = config.keys()
        assert "captcha" in keys
        assert "moderate" in keys
        assert len(keys) == 2
