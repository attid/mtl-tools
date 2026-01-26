# services/interfaces/__init__.py
"""Service interface definitions using Protocol."""

from .stellar_sdk import IStellarSDK
from .repositories import IFinanceRepository, IChatsRepository, IConfigRepository
from .external import IGristService, IWebService

__all__ = [
    "IStellarSDK",
    "IFinanceRepository",
    "IChatsRepository",
    "IConfigRepository",
    "IGristService",
    "IWebService",
]
