"""Notification settings service with DI."""

from typing import Any, Optional
from threading import Lock


class NotificationService:
    """
    Service for notification settings management.

    Replaces global_data attributes: notify_join, notify_message, alert_me
    """

    def __init__(self):
        self._lock = Lock()
        self._notify_join: dict[int, Any] = {}  # chat_id -> config
        self._notify_message: dict[int, Any] = {}  # chat_id -> config
        self._alert_me: dict[int, list[int]] = {}  # chat_id -> [user_ids]

    # Join notification methods
    def is_join_notify_enabled(self, chat_id: int) -> bool:
        with self._lock:
            return bool(self._notify_join.get(chat_id))

    def get_join_notify_config(self, chat_id: int) -> Any:
        with self._lock:
            return self._notify_join.get(chat_id)

    def set_join_notify(self, chat_id: int, config: Any) -> None:
        with self._lock:
            self._notify_join[chat_id] = config

    def disable_join_notify(self, chat_id: int) -> None:
        with self._lock:
            self._notify_join.pop(chat_id, None)

    def get_all_join_notify(self) -> dict[int, Any]:
        with self._lock:
            return self._notify_join.copy()

    # Message notification methods
    def is_message_notify_enabled(self, chat_id: int) -> bool:
        with self._lock:
            return bool(self._notify_message.get(chat_id))

    def get_message_notify_config(self, chat_id: int) -> Any:
        with self._lock:
            return self._notify_message.get(chat_id)

    def set_message_notify(self, chat_id: int, config: Any) -> None:
        with self._lock:
            self._notify_message[chat_id] = config

    def disable_message_notify(self, chat_id: int) -> None:
        with self._lock:
            self._notify_message.pop(chat_id, None)

    def get_all_message_notify(self) -> dict[int, Any]:
        with self._lock:
            return self._notify_message.copy()

    # Alert me methods (per-chat user alert subscriptions)
    def get_alert_users(self, chat_id: int) -> list[int]:
        """Get list of user_ids subscribed to alerts in this chat."""
        with self._lock:
            return self._alert_me.get(chat_id, []).copy()

    def is_user_subscribed(self, chat_id: int, user_id: int) -> bool:
        """Check if user is subscribed to alerts in this chat."""
        with self._lock:
            return user_id in self._alert_me.get(chat_id, [])

    def add_alert_user(self, chat_id: int, user_id: int) -> None:
        """Subscribe user to alerts in this chat."""
        with self._lock:
            if chat_id not in self._alert_me:
                self._alert_me[chat_id] = []
            if user_id not in self._alert_me[chat_id]:
                self._alert_me[chat_id].append(user_id)

    def remove_alert_user(self, chat_id: int, user_id: int) -> None:
        """Unsubscribe user from alerts in this chat."""
        with self._lock:
            if chat_id in self._alert_me and user_id in self._alert_me[chat_id]:
                self._alert_me[chat_id].remove(user_id)

    def toggle_alert_user(self, chat_id: int, user_id: int) -> bool:
        """Toggle user's alert subscription. Returns True if now subscribed, False if unsubscribed."""
        with self._lock:
            if chat_id not in self._alert_me:
                self._alert_me[chat_id] = []
            if user_id in self._alert_me[chat_id]:
                self._alert_me[chat_id].remove(user_id)
                return False
            else:
                self._alert_me[chat_id].append(user_id)
                return True

    def get_all_alerts(self) -> dict[int, list[int]]:
        """Get all alert subscriptions for persistence."""
        with self._lock:
            return {k: v.copy() for k, v in self._alert_me.items()}

    # Bulk loading for initialization
    def load_notify_join(self, data: dict[int, Any]) -> None:
        with self._lock:
            self._notify_join = data.copy()

    def load_notify_message(self, data: dict[int, Any]) -> None:
        with self._lock:
            self._notify_message = data.copy()

    def load_alert_me(self, data: dict[int, Any]) -> None:
        with self._lock:
            self._alert_me = data.copy()
