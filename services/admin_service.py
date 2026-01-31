"""Admin management service with DI."""

from typing import Optional
from threading import Lock


class AdminManagementService:
    """
    Service for admin management across chats and topics.

    Replaces global_data attributes: admins, topic_admins, topic_mute, skynet_admins, skynet_img
    """

    def __init__(self):
        self._lock = Lock()
        self._admins: dict[int, list[int]] = {}  # chat_id -> [user_ids]
        self._topic_admins: dict[str, list[str]] = {}  # "chat_id-thread_id" -> [usernames with @]
        self._topic_mute: dict[str, dict[int, dict[str, str]]] = {}  # "chat_id-thread_id" -> {user_id: {"end_time": str, "user": str}}
        self._skynet_admins: list[str] = []  # usernames with @
        self._skynet_img: list[str] = []  # usernames with @ allowed to use /img

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

    def has_topic_admins(self, chat_id: int, thread_id: int) -> bool:
        """Check if topic has any admins configured."""
        with self._lock:
            key = self._topic_key(chat_id, thread_id)
            return key in self._topic_admins

    def has_topic_admins_by_key(self, topic_key: str) -> bool:
        """Check if topic has any admins configured by key string."""
        with self._lock:
            return topic_key in self._topic_admins

    def is_topic_admin(self, chat_id: int, thread_id: int, username: str) -> bool:
        """Check if username is topic admin. Username should be lowercase with @ prefix."""
        if not username:
            return False
        with self._lock:
            key = self._topic_key(chat_id, thread_id)
            normalized = username.lower() if username.startswith('@') else f'@{username.lower()}'
            return normalized in self._topic_admins.get(key, [])

    def is_topic_admin_by_key(self, topic_key: str, username: str) -> bool:
        """Check if username is topic admin using pre-computed key."""
        if not username:
            return False
        with self._lock:
            normalized = username.lower() if username.startswith('@') else f'@{username.lower()}'
            return normalized in self._topic_admins.get(topic_key, [])

    def get_topic_admins(self, chat_id: int, thread_id: int) -> list[str]:
        """Get list of topic admin usernames."""
        with self._lock:
            key = self._topic_key(chat_id, thread_id)
            return self._topic_admins.get(key, []).copy()

    def set_topic_admins(self, chat_id: int, thread_id: int, admin_usernames: list[str]) -> None:
        """Set topic admins by usernames."""
        with self._lock:
            key = self._topic_key(chat_id, thread_id)
            self._topic_admins[key] = admin_usernames.copy()

    def add_topic_admin(self, chat_id: int, thread_id: int, username: str) -> None:
        """Add a topic admin by username."""
        normalized = username.lower() if username.startswith('@') else f'@{username.lower()}'
        with self._lock:
            key = self._topic_key(chat_id, thread_id)
            if key not in self._topic_admins:
                self._topic_admins[key] = []
            if normalized not in self._topic_admins[key]:
                self._topic_admins[key].append(normalized)

    def get_all_topic_admins(self) -> dict[str, list[str]]:
        """Get all topic admins data for persistence/display."""
        with self._lock:
            return {k: v.copy() for k, v in self._topic_admins.items()}

    # Topic mute methods (per-user mutes within a topic)
    def get_topic_mutes(self, chat_id: int, thread_id: int) -> dict[int, dict[str, str]]:
        """Get all mutes for a topic. Returns {user_id: {"end_time": str, "user": str}}."""
        with self._lock:
            key = self._topic_key(chat_id, thread_id)
            mutes = self._topic_mute.get(key, {})
            return {k: v.copy() for k, v in mutes.items()}

    def get_topic_mutes_by_key(self, topic_key: str) -> dict[int, dict[str, str]]:
        """Get all mutes for a topic by key. Returns {user_id: {"end_time": str, "user": str}}."""
        with self._lock:
            mutes = self._topic_mute.get(topic_key, {})
            return {k: v.copy() for k, v in mutes.items()}

    def has_topic_mutes(self, chat_id: int, thread_id: int) -> bool:
        """Check if topic has any mutes."""
        with self._lock:
            key = self._topic_key(chat_id, thread_id)
            return bool(self._topic_mute.get(key))

    def has_topic_mutes_by_key(self, topic_key: str) -> bool:
        """Check if topic has any mutes by key."""
        with self._lock:
            return bool(self._topic_mute.get(topic_key))

    def get_user_mute(self, chat_id: int, thread_id: int, user_id: int) -> Optional[dict[str, str]]:
        """Get mute info for a specific user in a topic."""
        with self._lock:
            key = self._topic_key(chat_id, thread_id)
            mute_info = self._topic_mute.get(key, {}).get(user_id)
            return mute_info.copy() if mute_info else None

    def is_user_muted(self, chat_id: int, thread_id: int, user_id: int) -> bool:
        """Check if user is muted in topic."""
        with self._lock:
            key = self._topic_key(chat_id, thread_id)
            return user_id in self._topic_mute.get(key, {})

    def set_user_mute(self, chat_id: int, thread_id: int, user_id: int, end_time: str, user_display: str) -> None:
        """Set mute for a user in a topic."""
        with self._lock:
            key = self._topic_key(chat_id, thread_id)
            if key not in self._topic_mute:
                self._topic_mute[key] = {}
            self._topic_mute[key][user_id] = {"end_time": end_time, "user": user_display}

    def set_user_mute_by_key(self, topic_key: str, user_id: int, end_time: str, user_display: str) -> None:
        """Set mute for a user in a topic by key."""
        with self._lock:
            if topic_key not in self._topic_mute:
                self._topic_mute[topic_key] = {}
            self._topic_mute[topic_key][user_id] = {"end_time": end_time, "user": user_display}

    def remove_user_mute(self, chat_id: int, thread_id: int, user_id: int) -> None:
        """Remove mute for a user in a topic."""
        with self._lock:
            key = self._topic_key(chat_id, thread_id)
            if key in self._topic_mute and user_id in self._topic_mute[key]:
                del self._topic_mute[key][user_id]

    def remove_user_mute_by_key(self, topic_key: str, user_id: int) -> None:
        """Remove mute for a user in a topic by key."""
        with self._lock:
            if topic_key in self._topic_mute and user_id in self._topic_mute[topic_key]:
                del self._topic_mute[topic_key][user_id]

    def get_all_topic_mutes(self) -> dict[str, dict[int, dict[str, str]]]:
        """Get all topic mutes data for persistence."""
        with self._lock:
            return {k: {uk: uv.copy() for uk, uv in v.items()} for k, v in self._topic_mute.items()}

    def load_topic_mutes(self, data: dict[str, dict]) -> None:
        """Load topic mutes from persistence."""
        with self._lock:
            self._topic_mute = {}
            for key, mutes in data.items():
                self._topic_mute[key] = {}
                for user_id, mute_info in mutes.items():
                    # user_id may come as string from JSON, convert to int
                    uid = int(user_id) if isinstance(user_id, str) else user_id
                    self._topic_mute[key][uid] = mute_info.copy()

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

    # Skynet img methods (users allowed to use /img command)
    def is_skynet_img_user(self, username: str) -> bool:
        if not username:
            return False
        with self._lock:
            # Normalize: ensure @ prefix for comparison
            normalized = username if username.startswith('@') else f'@{username}'
            return normalized.lower() in [u.lower() for u in self._skynet_img]

    def get_skynet_img_users(self) -> list[str]:
        with self._lock:
            return self._skynet_img.copy()

    def set_skynet_img_users(self, usernames: list[str]) -> None:
        with self._lock:
            self._skynet_img = usernames.copy()

    def add_skynet_img_user(self, username: str) -> None:
        normalized = username if username.startswith('@') else f'@{username}'
        with self._lock:
            if normalized not in self._skynet_img:
                self._skynet_img.append(normalized)

    # Bulk loading for initialization
    def load_admins(self, admins_data: dict[int, list[int]]) -> None:
        with self._lock:
            self._admins = {k: (v.copy() if isinstance(v, (list, dict)) else v)
                           for k, v in admins_data.items()}

    def load_topic_admins(self, topic_admins_data: dict[str, list]) -> None:  # type: ignore[type-arg]
        with self._lock:
            self._topic_admins = {k: (v.copy() if isinstance(v, (list, dict)) else v)
                                 for k, v in topic_admins_data.items()}
