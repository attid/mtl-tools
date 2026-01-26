# services/interfaces/__init__.py
"""Service interface definitions using Protocol."""

from .stellar_sdk import IStellarSDK
from .stellar_service import IStellarService
from .repositories import (
    IFinanceRepository,
    IChatsRepository,
    IConfigRepository,
    IPaymentsRepository,
    IWalletsRepository,
    IMessageRepository,
)
from .external import IGristService, IWebService

__all__ = [
    "IStellarSDK",
    "IStellarService",
    "IFinanceRepository",
    "IChatsRepository",
    "IConfigRepository",
    "IPaymentsRepository",
    "IWalletsRepository",
    "IMessageRepository",
    "IGristService",
    "IWebService",
]
