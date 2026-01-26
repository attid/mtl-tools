# shared/domain/dividend.py
"""Dividend domain models."""

from dataclasses import dataclass, field
from typing import Optional
from decimal import Decimal
from datetime import datetime


@dataclass(frozen=True)
class Dividend:
    """Single dividend payment to holder."""
    address: str
    amount: Decimal
    asset_code: str
    share_percent: Decimal = Decimal("0")


@dataclass
class DividendList:
    """
    Collection of dividends for distribution.

    Mutable aggregate root for dividend operations.
    """
    id: Optional[int] = None
    memo: str = ""
    pay_type: str = "EURMTL"
    created_at: Optional[datetime] = None
    dividends: list[Dividend] = field(default_factory=list)

    @property
    def total_amount(self) -> Decimal:
        """Calculate total distribution amount."""
        return sum(d.amount for d in self.dividends)

    @property
    def holder_count(self) -> int:
        """Get number of dividend recipients."""
        return len(self.dividends)

    @property
    def is_empty(self) -> bool:
        """Check if list has no dividends."""
        return len(self.dividends) == 0

    def add_dividend(self, dividend: Dividend) -> None:
        """Add dividend to list."""
        self.dividends.append(dividend)

    def remove_dividend(self, address: str) -> bool:
        """Remove dividend by address. Returns True if removed."""
        original_len = len(self.dividends)
        self.dividends = [d for d in self.dividends if d.address != address]
        return len(self.dividends) < original_len

    def filter_by_min_amount(self, min_amount: Decimal) -> "DividendList":
        """Return new list with dividends above minimum."""
        filtered = [d for d in self.dividends if d.amount >= min_amount]
        return DividendList(
            id=self.id,
            memo=self.memo,
            pay_type=self.pay_type,
            created_at=self.created_at,
            dividends=filtered,
        )

    def filter_by_asset(self, asset_code: str) -> "DividendList":
        """Return new list with only specified asset."""
        filtered = [d for d in self.dividends if d.asset_code == asset_code]
        return DividendList(
            id=self.id,
            memo=self.memo,
            pay_type=self.pay_type,
            created_at=self.created_at,
            dividends=filtered,
        )

    def get_dividend_for(self, address: str) -> Optional[Dividend]:
        """Get dividend for specific address."""
        for d in self.dividends:
            if d.address == address:
                return d
        return None
