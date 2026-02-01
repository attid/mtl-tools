"""Bot runtime state service with DI."""

from typing import Any, Optional
from datetime import datetime
from threading import Lock


class BotStateService:
    """
    Service for bot runtime state management.

    Replaces global_data attributes: sync, reboot, need_decode, last_pong_response
    """

    def __init__(self):
        self._lock = Lock()
        self._sync: dict[str, Any] = {}
        self._reboot: bool = False
        self._need_decode: list[int] = []
        self._last_pong_response: Optional[datetime] = None
        self._last_ping_sent: Optional[datetime] = None

    # Sync state methods
    def get_sync_state(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._sync.get(key, default)

    def set_sync_state(self, key: str, value: Any) -> None:
        with self._lock:
            self._sync[key] = value

    def clear_sync_state(self, key: str) -> None:
        with self._lock:
            self._sync.pop(key, None)

    # Reboot management
    def is_reboot_requested(self) -> bool:
        with self._lock:
            return self._reboot

    def request_reboot(self) -> None:
        with self._lock:
            self._reboot = True

    def clear_reboot(self) -> None:
        with self._lock:
            self._reboot = False

    # Decode tracking
    def needs_decode(self, chat_id: int) -> bool:
        with self._lock:
            return chat_id in self._need_decode

    def mark_needs_decode(self, chat_id: int) -> None:
        with self._lock:
            if chat_id not in self._need_decode:
                self._need_decode.append(chat_id)

    def clear_needs_decode(self, chat_id: int) -> None:
        with self._lock:
            if chat_id in self._need_decode:
                self._need_decode.remove(chat_id)

    def get_all_needing_decode(self) -> list[int]:
        with self._lock:
            return self._need_decode.copy()

    # Monitoring
    def get_last_pong(self) -> Optional[datetime]:
        with self._lock:
            return self._last_pong_response

    def update_last_pong(self) -> None:
        with self._lock:
            self._last_pong_response = datetime.now()

    def set_last_pong(self, dt: Optional[datetime]) -> None:
        with self._lock:
            self._last_pong_response = dt

    # Ping tracking (for health check)
    def get_last_ping_sent(self) -> Optional[datetime]:
        with self._lock:
            return self._last_ping_sent

    def update_last_ping_sent(self) -> None:
        with self._lock:
            self._last_ping_sent = datetime.now()
