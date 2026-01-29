# services/interfaces/repositories.py
"""Repository interface definitions."""

from typing import Protocol, Optional, Any, List
from datetime import datetime
from decimal import Decimal


class IFinanceRepository(Protocol):
    """Interface for finance data access."""

    def get_div_list(self, list_id: int) -> Optional[Any]:
        """Get dividend list by ID."""
        ...

    def get_payments(self, list_id: int, pack_count: int) -> list[Any]:
        """Get unpacked payments for list."""
        ...

    def count_unpacked_payments(self, list_id: int) -> int:
        """Count unpacked payments."""
        ...

    def save_transaction(self, list_id: int, xdr: str) -> bool:
        """Save transaction XDR."""
        ...

    def get_watch_list(self) -> list[str]:
        """Get monitored account addresses."""
        ...


class IChatsRepository(Protocol):
    """Interface for chat data access."""

    def get_all_chats(self) -> list[Any]:
        """Get all chats."""
        ...

    def add_user_to_chat(self, chat_id: int, member: Any) -> bool:
        """Add user to chat."""
        ...

    def remove_user_from_chat(self, chat_id: int, user_id: int) -> bool:
        """Remove user from chat."""
        ...

    def get_user_id(self, username: str) -> Optional[int]:
        """Get user ID by username."""
        ...

    def get_user_by_id(self, user_id: int) -> Optional[Any]:
        """Get user record by ID."""
        ...

    def save_user_type(self, user_id: int, user_type: int) -> bool:
        """Save spam status (stored in user_type)."""
        ...


class IConfigRepository(Protocol):
    """Interface for configuration data access."""

    def save_bot_value(self, chat_id: int, chat_key: str, chat_value: Any) -> bool:
        """Save configuration value."""
        ...

    def load_bot_value(self, chat_id: int, chat_key: str, default_value: Any = None) -> Any:
        """Load configuration value."""
        ...

    def get_chat_ids_by_key(self, chat_key: str) -> list[int]:
        """Get all chat IDs with specific config key."""
        ...


class IPaymentsRepository(Protocol):
    """Interface for payment data access."""

    def get_payment_by_id(self, payment_id: int) -> Optional[Any]:
        """Get payment by ID as domain model."""
        ...

    def get_payments_by_list(
        self,
        list_id: int,
        status: Optional[Any] = None,
        limit: int = 100,
    ) -> list[Any]:
        """Get payments for dividend list."""
        ...

    def get_unpacked_payments(self, list_id: int, limit: int = 70) -> list[Any]:
        """Get unpacked payments for list (for packing into transactions)."""
        ...

    def count_unpacked_payments(self, list_id: int) -> int:
        """Count unpacked payments for list."""
        ...

    def mark_as_packed(self, payment_ids: list[int]) -> int:
        """Mark payments as packed. Returns count updated."""
        ...

    def get_total_for_user(self, user_key: str) -> Decimal:
        """Get total dividend amount for user across all lists."""
        ...

    def get_total_for_list(self, list_id: int) -> Decimal:
        """Get total dividend amount for list."""
        ...

    def create_payment(
        self,
        user_key: str,
        amount: Decimal,
        list_id: int,
        mtl_sum: Optional[float] = None,
        user_calc: Optional[float] = None,
    ) -> Any:
        """Create new payment record."""
        ...


class IWalletsRepository(Protocol):
    """Interface for wallet data access."""

    def get_wallet_by_id(self, wallet_id: int) -> Optional[Any]:
        """Get wallet by ID."""
        ...

    def get_wallet_by_public_key(self, public_key: str) -> Optional[Any]:
        """Get wallet by public key."""
        ...

    def get_wallets_by_user(self, user_id: int) -> list[Any]:
        """Get all wallets for user."""
        ...

    def get_default_wallet(self, user_id: int) -> Optional[Any]:
        """Get user's default wallet."""
        ...

    def set_default_wallet(self, user_id: int, wallet_id: int) -> bool:
        """Set wallet as default for user."""
        ...

    def update_balances(self, public_key: str, balances: dict) -> bool:
        """Update cached balances for wallet."""
        ...

    def mark_for_deletion(self, wallet_id: int) -> bool:
        """Mark wallet for deletion (soft delete)."""
        ...

    def count_user_wallets(self, user_id: int) -> int:
        """Count active wallets for user."""
        ...


class IMessageRepository(Protocol):
    """Interface for message data access."""

    def add_message(
        self,
        user_id: int,
        text: str,
        use_alarm: int = 0,
        update_id: int = None,
        button_json: str = None,
        topic_id: int = 0,
    ) -> None:
        """Add a new message to the queue."""
        ...

    def load_new_messages(self, limit: int = 10) -> List[Any]:
        """Load unsent messages from queue."""
        ...

    def save_message(
        self,
        user_id: int,
        username: str,
        chat_id: int,
        thread_id: int,
        text: str,
        summary_id: int = None,
    ) -> None:
        """Save a message for summarization."""
        ...

    def get_messages_without_summary(
        self,
        chat_id: int,
        thread_id: int,
        dt: datetime = None,
    ) -> List[Any]:
        """Get messages that haven't been summarized yet."""
        ...

    def add_summary(self, text: str, summary_id: int = None) -> Any:
        """Add a summary record."""
        ...

    def get_summary(
        self,
        chat_id: int,
        thread_id: int,
        dt: datetime = None,
    ) -> List[Any]:
        """Get summaries for chat thread on date."""
        ...

    def send_admin_message(self, msg: str) -> None:
        """Send a message to admin."""
        ...
