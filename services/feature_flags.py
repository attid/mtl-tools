# services/feature_flags.py
"""Feature flags service replacing global_data feature lists."""

from typing import Optional
from dataclasses import dataclass
from threading import Lock

from services.config_service import ConfigService


@dataclass
class ChatFeatures:
    """Feature flags for a specific chat."""
    chat_id: int
    captcha: bool = False
    moderate: bool = False
    no_first_link: bool = False
    reply_only: bool = False
    listen: bool = False
    auto_all: bool = False
    save_last_message_date: bool = False
    join_request_captcha: bool = False
    full_data: bool = False


class FeatureFlagsService:
    """
    Service for chat feature flags.

    Replaces global_data lists like captcha, moderate, no_first_link, etc.
    Provides a clean interface for checking and toggling features.
    """

    FEATURE_KEYS = [
        "captcha",
        "moderate",
        "no_first_link",
        "reply_only",
        "listen",
        "auto_all",
        "save_last_message_date",
        "join_request_captcha",
        "full_data",
    ]

    def __init__(self, config_service: ConfigService):
        self._config = config_service
        self._cache: dict[int, ChatFeatures] = {}
        self._lock = Lock()

    def get_features(self, chat_id: int) -> ChatFeatures:
        """Get all feature flags for chat."""
        with self._lock:
            if chat_id in self._cache:
                return self._cache[chat_id]

        features = ChatFeatures(chat_id=chat_id)

        for key in self.FEATURE_KEYS:
            value = self._config.load_value(chat_id, key, False)
            setattr(features, key, bool(value))

        with self._lock:
            self._cache[chat_id] = features

        return features

    def is_enabled(self, chat_id: int, feature: str) -> bool:
        """Check if specific feature is enabled for chat."""
        if feature not in self.FEATURE_KEYS:
            return False
        features = self.get_features(chat_id)
        return getattr(features, feature, False)

    def enable(self, chat_id: int, feature: str) -> bool:
        """Enable feature for chat."""
        return self.set_feature(chat_id, feature, True)

    def disable(self, chat_id: int, feature: str) -> bool:
        """Disable feature for chat."""
        return self.set_feature(chat_id, feature, False)

    def set_feature(self, chat_id: int, feature: str, enabled: bool) -> bool:
        """Enable or disable feature for chat."""
        if feature not in self.FEATURE_KEYS:
            return False

        self._config.save_value(chat_id, feature, enabled)

        # Update cache
        with self._lock:
            if chat_id in self._cache:
                setattr(self._cache[chat_id], feature, enabled)

        return True

    def toggle(self, chat_id: int, feature: str) -> bool:
        """Toggle feature state. Returns new state."""
        current = self.is_enabled(chat_id, feature)
        self.set_feature(chat_id, feature, not current)
        return not current

    def get_chats_with_feature(self, feature: str) -> list[int]:
        """Get all chat IDs with feature enabled."""
        if feature not in self.FEATURE_KEYS:
            return []
        return self._config.get_chats_with_feature(feature)

    def invalidate_cache(self, chat_id: Optional[int] = None) -> None:
        """Invalidate cache."""
        with self._lock:
            if chat_id is not None:
                self._cache.pop(chat_id, None)
            else:
                self._cache.clear()

    # Convenience methods for common features
    def is_captcha_enabled(self, chat_id: int) -> bool:
        """Check if captcha is enabled."""
        return self.is_enabled(chat_id, "captcha")

    def is_moderation_enabled(self, chat_id: int) -> bool:
        """Check if moderation is enabled."""
        return self.is_enabled(chat_id, "moderate")

    def is_no_first_link(self, chat_id: int) -> bool:
        """Check if first link restriction is enabled."""
        return self.is_enabled(chat_id, "no_first_link")

    def is_reply_only(self, chat_id: int) -> bool:
        """Check if reply-only mode is enabled."""
        return self.is_enabled(chat_id, "reply_only")

    def is_listening(self, chat_id: int) -> bool:
        """Check if bot is listening in chat."""
        return self.is_enabled(chat_id, "listen")

    def is_full_data(self, chat_id: int) -> bool:
        """Check if full data mode is enabled."""
        return self.is_enabled(chat_id, "full_data")

    def get_cached_count(self) -> int:
        """Get number of cached feature sets (for monitoring)."""
        with self._lock:
            return len(self._cache)
