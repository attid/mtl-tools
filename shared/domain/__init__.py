# shared/domain/__init__.py
"""Domain models - pure business entities."""

from .user import User, UserType
from .payment import Payment, PaymentStatus
from .dividend import Dividend, DividendList
from .config import BotConfig

__all__ = [
    "User",
    "UserType",
    "Payment",
    "PaymentStatus",
    "Dividend",
    "DividendList",
    "BotConfig",
]
