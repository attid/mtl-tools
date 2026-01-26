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
        self._alert_me: dict[int, Any] = {}  # user_id -> config

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

    # Alert me methods (personal alerts for users)
    def get_alert_config(self, user_id: int) -> Any:
        with self._lock:
            return self._alert_me.get(user_id)

    def set_alert_config(self, user_id: int, config: Any) -> None:
        with self._lock:
            self._alert_me[user_id] = config

    def remove_alert(self, user_id: int) -> None:
        with self._lock:
            self._alert_me.pop(user_id, None)

    def has_alert(self, user_id: int) -> bool:
        with self._lock:
            return user_id in self._alert_me

    def get_all_alerts(self) -> dict[int, Any]:
        with self._lock:
            return self._alert_me.copy()

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
