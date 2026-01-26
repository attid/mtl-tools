# shared/domain/config.py
"""Bot configuration domain model."""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class BotConfig:
    """
    Domain entity for bot configuration.

    Encapsulates chat-level configuration with type-safe access.
    """
    chat_id: int
    settings: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        self.settings[key] = value

    def has(self, key: str) -> bool:
        """Check if configuration key exists."""
        return key in self.settings

    def remove(self, key: str) -> bool:
        """Remove configuration key. Returns True if removed."""
        if key in self.settings:
            del self.settings[key]
            return True
        return False

    def keys(self) -> list[str]:
        """Get all configuration keys."""
        return list(self.settings.keys())

    # Typed accessors for common settings
    @property
    def captcha_enabled(self) -> bool:
        """Check if captcha is enabled for chat."""
        return bool(self.get("captcha", False))

    @property
    def moderate_enabled(self) -> bool:
        """Check if moderation is enabled."""
        return bool(self.get("moderate", False))

    @property
    def welcome_message(self) -> Optional[str]:
        """Get welcome message template."""
        return self.get("welcome_message")

    @property
    def entry_channel(self) -> Optional[int]:
        """Get required entry channel ID."""
        return self.get("entry_channel")

    @property
    def no_first_link(self) -> bool:
        """Check if first link restriction is enabled."""
        return bool(self.get("no_first_link", False))

    @property
    def reply_only(self) -> bool:
        """Check if reply-only mode is enabled."""
        return bool(self.get("reply_only", False))

    @property
    def listen_enabled(self) -> bool:
        """Check if listen mode is enabled."""
        return bool(self.get("listen", False))

    @property
    def auto_all_enabled(self) -> bool:
        """Check if auto-all mentions are enabled."""
        return bool(self.get("auto_all", False))

    @property
    def save_last_message_date(self) -> bool:
        """Check if last message date saving is enabled."""
        return bool(self.get("save_last_message_date", False))

    @property
    def join_request_captcha(self) -> bool:
        """Check if join request captcha is enabled."""
        return bool(self.get("join_request_captcha", False))
