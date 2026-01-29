# shared/domain/user.py
"""User domain model."""

from enum import IntEnum
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


class SpamStatus(IntEnum):
    """Spam status values stored in BotUsers.user_type."""
    NEW = 0
    GOOD = 1
    BAD = 2


class AdminStatus(IntEnum):
    """Admin status for domain logic (not tied to DB)."""
    REGULAR = 0
    ADMIN = 1
    SUPERADMIN = 2


@dataclass(frozen=True)
class User:
    """
    Domain entity representing a bot user.

    Immutable value object with business logic.
    """
    user_id: int
    username: Optional[str] = None
    spam_status: SpamStatus = SpamStatus.NEW
    admin_status: AdminStatus = AdminStatus.REGULAR
    created_at: Optional[datetime] = None

    @property
    def is_admin(self) -> bool:
        """Check if user has admin privileges."""
        return self.admin_status >= AdminStatus.ADMIN

    @property
    def is_superadmin(self) -> bool:
        """Check if user is superadmin."""
        return self.admin_status == AdminStatus.SUPERADMIN

    @property
    def is_good(self) -> bool:
        """Check if user is good."""
        return self.spam_status == SpamStatus.GOOD

    @property
    def is_bad(self) -> bool:
        """Check if user is bad."""
        return self.spam_status == SpamStatus.BAD

    @property
    def is_new(self) -> bool:
        """Check if user is new."""
        return self.spam_status == SpamStatus.NEW

    def with_spam_status(self, new_status: SpamStatus) -> "User":
        """Return new User with updated spam status."""
        return User(
            user_id=self.user_id,
            username=self.username,
            spam_status=new_status,
            admin_status=self.admin_status,
            created_at=self.created_at,
        )

    def with_admin_status(self, new_status: AdminStatus) -> "User":
        """Return new User with updated admin status."""
        return User(
            user_id=self.user_id,
            username=self.username,
            spam_status=self.spam_status,
            admin_status=new_status,
            created_at=self.created_at,
        )

    def with_username(self, new_username: str) -> "User":
        """Return new User with updated username."""
        return User(
            user_id=self.user_id,
            username=new_username,
            spam_status=self.spam_status,
            admin_status=self.admin_status,
            created_at=self.created_at,
        )
