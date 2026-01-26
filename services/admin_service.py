"""Admin management service with DI."""

from typing import Optional
from threading import Lock


class AdminManagementService:
    """
    Service for admin management across chats and topics.

    Replaces global_data attributes: admins, topic_admins, topic_mute, skynet_admins
    """

    def __init__(self):
        self._lock = Lock()
        self._admins: dict[int, list[int]] = {}  # chat_id -> [user_ids]
        self._topic_admins: dict[str, list[int]] = {}  # "chat_id-thread_id" -> [user_ids]
        self._topic_mute: dict[str, bool] = {}  # "chat_id-thread_id" -> muted
        self._skynet_admins: list[str] = []  # usernames with @

    # Chat admin methods
    def is_chat_admin(self, chat_id: int, user_id: int) -> bool:
        with self._lock:
            return user_id in self._admins.get(chat_id, [])

    def get_chat_admins(self, chat_id: int) -> list[int]:
        with self._lock:
            return self._admins.get(chat_id, []).copy()

    def set_chat_admins(self, chat_id: int, admin_ids: list[int]) -> None:
        with self._lock:
            self._admins[chat_id] = admin_ids.copy()

    def add_chat_admin(self, chat_id: int, user_id: int) -> None:
        with self._lock:
            if chat_id not in self._admins:
                self._admins[chat_id] = []
            if user_id not in self._admins[chat_id]:
                self._admins[chat_id].append(user_id)

    def remove_chat_admin(self, chat_id: int, user_id: int) -> None:
        with self._lock:
            if chat_id in self._admins and user_id in self._admins[chat_id]:
                self._admins[chat_id].remove(user_id)

    # Topic admin methods
    def _topic_key(self, chat_id: int, thread_id: int) -> str:
        return f"{chat_id}-{thread_id}"

    def is_topic_admin(self, chat_id: int, thread_id: int, user_id: int) -> bool:
        with self._lock:
            key = self._topic_key(chat_id, thread_id)
            return user_id in self._topic_admins.get(key, [])

    def get_topic_admins(self, chat_id: int, thread_id: int) -> list[int]:
        with self._lock:
            key = self._topic_key(chat_id, thread_id)
            return self._topic_admins.get(key, []).copy()

    def set_topic_admins(self, chat_id: int, thread_id: int, admin_ids: list[int]) -> None:
        with self._lock:
            key = self._topic_key(chat_id, thread_id)
            self._topic_admins[key] = admin_ids.copy()

    def add_topic_admin(self, chat_id: int, thread_id: int, user_id: int) -> None:
        with self._lock:
            key = self._topic_key(chat_id, thread_id)
            if key not in self._topic_admins:
                self._topic_admins[key] = []
            if user_id not in self._topic_admins[key]:
                self._topic_admins[key].append(user_id)

    # Topic mute methods
    def is_topic_muted(self, chat_id: int, thread_id: int) -> bool:
        with self._lock:
            key = self._topic_key(chat_id, thread_id)
            return self._topic_mute.get(key, False)

    def set_topic_mute(self, chat_id: int, thread_id: int, muted: bool) -> None:
        with self._lock:
            key = self._topic_key(chat_id, thread_id)
            self._topic_mute[key] = muted

    # Skynet admin methods (bot-level admins by username)
    def is_skynet_admin(self, username: str) -> bool:
        if not username:
            return False
        with self._lock:
            # Normalize: ensure @ prefix for comparison
            normalized = username if username.startswith('@') else f'@{username}'
            return normalized in self._skynet_admins

    def get_skynet_admins(self) -> list[str]:
        with self._lock:
            return self._skynet_admins.copy()

    def set_skynet_admins(self, usernames: list[str]) -> None:
        with self._lock:
            self._skynet_admins = usernames.copy()

    def add_skynet_admin(self, username: str) -> None:
        normalized = username if username.startswith('@') else f'@{username}'
        with self._lock:
            if normalized not in self._skynet_admins:
                self._skynet_admins.append(normalized)

    # Bulk loading for initialization
    def load_admins(self, admins_data: dict[int, list[int]]) -> None:
        with self._lock:
            self._admins = {k: v.copy() for k, v in admins_data.items()}

    def load_topic_admins(self, topic_admins_data: dict[str, list[int]]) -> None:
        with self._lock:
            self._topic_admins = {k: v.copy() for k, v in topic_admins_data.items()}
