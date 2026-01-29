# shared/domain/__init__.py
"""Domain models - pure business entities."""

from .user import User, AdminStatus, SpamStatus
from .payment import Payment, PaymentStatus
from .dividend import Dividend, DividendList
from .config import BotConfig

__all__ = [
    "User",
    "AdminStatus",
    "SpamStatus",
    "Payment",
    "PaymentStatus",
    "Dividend",
    "DividendList",
    "BotConfig",
]
