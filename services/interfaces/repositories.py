# services/interfaces/repositories.py
"""Repository interface definitions."""

from typing import Protocol, Optional, Any
from datetime import datetime


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
        """Save user type/permission level."""
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
