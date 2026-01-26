# shared/domain/payment.py
"""Payment domain model."""

from enum import Enum
from dataclasses import dataclass
from typing import Optional
from decimal import Decimal
from datetime import datetime


class PaymentStatus(Enum):
    """Payment processing status."""
    PENDING = "pending"
    PACKED = "packed"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    FAILED = "failed"


@dataclass(frozen=True)
class Payment:
    """
    Domain entity representing a payment.

    Immutable value object for payment data.
    """
    id: int
    user_key: str
    amount: Decimal
    status: PaymentStatus = PaymentStatus.PENDING
    list_id: Optional[int] = None
    created_at: Optional[datetime] = None

    @property
    def is_pending(self) -> bool:
        """Check if payment is waiting to be processed."""
        return self.status == PaymentStatus.PENDING

    @property
    def is_packed(self) -> bool:
        """Check if payment was packed into transaction."""
        return self.status == PaymentStatus.PACKED

    @property
    def is_submitted(self) -> bool:
        """Check if payment was submitted to network."""
        return self.status == PaymentStatus.SUBMITTED

    @property
    def is_completed(self) -> bool:
        """Check if payment was confirmed."""
        return self.status == PaymentStatus.CONFIRMED

    @property
    def is_failed(self) -> bool:
        """Check if payment failed."""
        return self.status == PaymentStatus.FAILED

    def with_status(self, new_status: PaymentStatus) -> "Payment":
        """Return new Payment with updated status."""
        return Payment(
            id=self.id,
            user_key=self.user_key,
            amount=self.amount,
            status=new_status,
            list_id=self.list_id,
            created_at=self.created_at,
        )

    def with_list_id(self, new_list_id: int) -> "Payment":
        """Return new Payment with assigned list ID."""
        return Payment(
            id=self.id,
            user_key=self.user_key,
            amount=self.amount,
            status=self.status,
            list_id=new_list_id,
            created_at=self.created_at,
        )
