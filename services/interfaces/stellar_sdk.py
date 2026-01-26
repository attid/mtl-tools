# services/interfaces/stellar_sdk.py
"""Stellar SDK interface definition."""

from typing import Protocol, Optional
from decimal import Decimal

from stellar_sdk import Asset


class IStellarSDK(Protocol):
    """Interface for Stellar SDK operations."""

    async def get_account(self, address: str) -> Optional[dict]:
        """Get account details."""
        ...

    async def get_balances(self, address: str) -> dict[str, Decimal]:
        """Get all asset balances for account."""
        ...

    async def get_holders(self, asset: Asset, limit: int = 200) -> list[dict]:
        """Get all holders of specific asset."""
        ...

    async def submit_transaction(self, xdr: str) -> dict:
        """Submit signed transaction."""
        ...

    def sign_transaction(self, xdr: str) -> str:
        """Sign transaction XDR."""
        ...
