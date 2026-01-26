# shared/domain/user.py
"""User domain model."""

from enum import IntEnum
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


class UserType(IntEnum):
    """User permission levels."""
    BANNED = -1
    REGULAR = 0
    TRUSTED = 1
    ADMIN = 2
    SUPERADMIN = 3


@dataclass(frozen=True)
class User:
    """
    Domain entity representing a bot user.

    Immutable value object with business logic.
    """
    user_id: int
    username: Optional[str] = None
    user_type: UserType = UserType.REGULAR
    created_at: Optional[datetime] = None

    @property
    def is_admin(self) -> bool:
        """Check if user has admin privileges."""
        return self.user_type >= UserType.ADMIN

    @property
    def is_trusted(self) -> bool:
        """Check if user is trusted or higher."""
        return self.user_type >= UserType.TRUSTED

    @property
    def is_banned(self) -> bool:
        """Check if user is banned."""
        return self.user_type == UserType.BANNED

    @property
    def is_superadmin(self) -> bool:
        """Check if user is superadmin."""
        return self.user_type == UserType.SUPERADMIN

    def with_type(self, new_type: UserType) -> "User":
        """Return new User with updated type."""
        return User(
            user_id=self.user_id,
            username=self.username,
            user_type=new_type,
            created_at=self.created_at,
        )

    def with_username(self, new_username: str) -> "User":
        """Return new User with updated username."""
        return User(
            user_id=self.user_id,
            username=new_username,
            user_type=self.user_type,
            created_at=self.created_at,
        )
