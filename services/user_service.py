# services/user_service.py
"""User service with dependency injection."""

from typing import Optional
from threading import Lock

from shared.domain.user import User, UserType
from services.interfaces.repositories import IChatsRepository


class UserService:
    """
    Service for user management with thread-safe caching.

    Replaces global_data.users_list and check_user() function.
    """

    def __init__(self, chats_repo: IChatsRepository):
        self._repo = chats_repo
        self._cache: dict[int, UserType] = {}
        self._lock = Lock()

    def get_user_type(self, user_id: int) -> UserType:
        """
        Get user type with caching.

        Thread-safe lookup with fallback to database.
        """
        with self._lock:
            if user_id in self._cache:
                return self._cache[user_id]

        # Load from database
        user_record = self._repo.get_user_by_id(user_id)
        if user_record:
            user_type = UserType(getattr(user_record, 'user_type', 0))
        else:
            user_type = UserType.REGULAR

        with self._lock:
            self._cache[user_id] = user_type

        return user_type

    def get_user(self, user_id: int) -> User:
        """Get User domain object."""
        user_type = self.get_user_type(user_id)
        return User(user_id=user_id, user_type=user_type)

    def set_user_type(self, user_id: int, user_type: UserType) -> None:
        """Update user type in cache and database."""
        with self._lock:
            self._cache[user_id] = user_type

        # Persist to database
        self._repo.save_user_type(user_id, user_type.value)

    def is_admin(self, user_id: int) -> bool:
        """Check if user has admin privileges."""
        return self.get_user_type(user_id) >= UserType.ADMIN

    def is_superadmin(self, user_id: int) -> bool:
        """Check if user is superadmin."""
        return self.get_user_type(user_id) == UserType.SUPERADMIN

    def is_trusted(self, user_id: int) -> bool:
        """Check if user is trusted or higher."""
        return self.get_user_type(user_id) >= UserType.TRUSTED

    def is_banned(self, user_id: int) -> bool:
        """Check if user is banned."""
        return self.get_user_type(user_id) == UserType.BANNED

    def ban_user(self, user_id: int) -> None:
        """Ban a user."""
        self.set_user_type(user_id, UserType.BANNED)

    def unban_user(self, user_id: int) -> None:
        """Unban a user (set to regular)."""
        self.set_user_type(user_id, UserType.REGULAR)

    def promote_to_admin(self, user_id: int) -> None:
        """Promote user to admin."""
        self.set_user_type(user_id, UserType.ADMIN)

    def promote_to_trusted(self, user_id: int) -> None:
        """Promote user to trusted."""
        self.set_user_type(user_id, UserType.TRUSTED)

    def clear_cache(self) -> None:
        """Clear user cache (for testing or reload)."""
        with self._lock:
            self._cache.clear()

    def invalidate_user(self, user_id: int) -> None:
        """Remove specific user from cache."""
        with self._lock:
            self._cache.pop(user_id, None)

    def preload_users(self, users: dict[int, int]) -> None:
        """
        Bulk load users into cache.

        Args:
            users: Dict of {user_id: user_type_value}
        """
        with self._lock:
            for user_id, user_type in users.items():
                self._cache[user_id] = UserType(user_type)

    def get_cached_count(self) -> int:
        """Get number of cached users (for monitoring)."""
        with self._lock:
            return len(self._cache)
