# services/config_service.py
"""Configuration service with dependency injection."""

from typing import Any, Optional
from threading import Lock

from services.interfaces.repositories import IConfigRepository
from shared.domain.config import BotConfig


class ConfigService:
    """
    Service for bot configuration management.

    Replaces direct global_data.mongo_config access.
    """

    def __init__(self, config_repo: IConfigRepository):
        self._repo = config_repo
        self._cache: dict[int, BotConfig] = {}
        self._lock = Lock()

    def get_config(self, chat_id: int) -> BotConfig:
        """
        Get configuration for chat (cached).

        Returns BotConfig domain object with all settings.
        """
        with self._lock:
            if chat_id in self._cache:
                return self._cache[chat_id]

        # Load all settings for chat
        settings = {}
        for key in self._get_common_keys():
            value = self._repo.load_bot_value(chat_id, key)
            if value is not None:
                settings[key] = value

        config = BotConfig(chat_id=chat_id, settings=settings)

        with self._lock:
            self._cache[chat_id] = config

        return config

    def save_value(self, chat_id: int, key: str, value: Any) -> bool:
        """Save configuration value."""
        result = self._repo.save_bot_value(chat_id, key, value)

        # Update cache
        with self._lock:
            if chat_id in self._cache:
                self._cache[chat_id].set(key, value)

        return result

    def load_value(self, chat_id: int, key: str, default: Any = None) -> Any:
        """Load configuration value."""
        return self._repo.load_bot_value(chat_id, key, default)

    def remove_value(self, chat_id: int, key: str) -> bool:
        """Remove configuration value."""
        # Save None to effectively remove
        result = self._repo.save_bot_value(chat_id, key, None)

        # Update cache
        with self._lock:
            if chat_id in self._cache:
                self._cache[chat_id].remove(key)

        return result

    def get_chats_with_feature(self, feature_key: str) -> list[int]:
        """Get all chat IDs with specific feature enabled."""
        chat_ids = self._repo.get_chat_ids_by_key(feature_key)
        # Filter to only those with truthy values
        return [
            cid for cid in chat_ids
            if self.load_value(cid, feature_key)
        ]

    def invalidate_cache(self, chat_id: Optional[int] = None) -> None:
        """Invalidate cache for specific chat or all."""
        with self._lock:
            if chat_id is not None:
                self._cache.pop(chat_id, None)
            else:
                self._cache.clear()

    def is_feature_enabled(self, chat_id: int, feature: str) -> bool:
        """Check if feature is enabled for chat."""
        config = self.get_config(chat_id)
        return bool(config.get(feature, False))

    def get_cached_count(self) -> int:
        """Get number of cached configs (for monitoring)."""
        with self._lock:
            return len(self._cache)

    def _get_common_keys(self) -> list[str]:
        """Get list of common config keys to preload."""
        return [
            "captcha",
            "moderate",
            "welcome_message",
            "entry_channel",
            "no_first_link",
            "reply_only",
            "listen",
            "auto_all",
            "save_last_message_date",
            "join_request_captcha",
            "full_data",
        ]
