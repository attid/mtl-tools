# services/interfaces/stellar_service.py
"""High-level Stellar service interface."""

from typing import Protocol, Optional
from decimal import Decimal


class IStellarService(Protocol):
    """Interface for Stellar business operations."""

    async def get_balance(self, address: str, asset_code: str) -> Decimal:
        """Get balance of specific asset for address."""
        ...

    async def calculate_dividends(
        self,
        total_amount: Decimal,
        asset_code: str,
    ) -> list[dict]:
        """Calculate dividend distribution."""
        ...

    async def submit_payment(
        self,
        destination: str,
        amount: Decimal,
        asset_code: str,
        memo: Optional[str] = None,
    ) -> str:
        """Submit payment transaction. Returns transaction hash."""
        ...

    async def get_holders_count(self, asset_code: str) -> int:
        """Get number of holders for asset."""
        ...

    async def decode_xdr(
        self,
        xdr: str,
        filter_sum: int = -1,
        full_data: bool = False,
    ) -> list[str]:
        """Decode XDR transaction and return human-readable operations."""
        ...

    def sign_transaction(self, xdr: str, sign_key: Optional[str] = None) -> str:
        """Sign transaction XDR."""
        ...

    async def get_account_info(self, address: str) -> Optional[dict]:
        """Get account information including balances and signers."""
        ...

    def find_public_key(self, text: str) -> Optional[str]:
        """Find Stellar public key in text."""
        ...

    async def address_to_username(self, address: str, full_data: bool = False) -> str:
        """Convert Stellar address to human-readable username."""
        ...
