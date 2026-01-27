"""Voting and poll service with DI."""

from typing import Any, Optional
from threading import Lock


class VotingService:
    """
    Service for poll voting and first-vote tracking.

    Replaces global_data attributes: votes, first_vote, first_vote_data
    """

    def __init__(self):
        self._lock = Lock()
        self._votes: dict[int, dict] = {}  # chat_id -> {msg_id: vote_data}
        self._first_vote: list[int] = []  # chat_ids with first-vote enabled
        self._first_vote_data: dict[int, dict] = {}  # chat_id -> vote_state
        self._vote_weights: dict[str, dict] = {}  # address -> {user: weight, "NEED": {50: X, 75: Y, 100: Z}}

    # Poll votes methods
    def get_poll_votes(self, chat_id: int, msg_id: Optional[int] = None) -> dict:
        with self._lock:
            if msg_id is None:
                return self._votes.get(chat_id, {}).copy()
            return self._votes.get(chat_id, {}).get(msg_id, {}).copy()

    def save_poll_votes(self, chat_id: int, msg_id: int, votes: dict) -> None:
        with self._lock:
            if chat_id not in self._votes:
                self._votes[chat_id] = {}
            self._votes[chat_id][msg_id] = votes.copy()

    def clear_poll_votes(self, chat_id: int, msg_id: Optional[int] = None) -> None:
        with self._lock:
            if msg_id is None:
                self._votes.pop(chat_id, None)
            elif chat_id in self._votes:
                self._votes[chat_id].pop(msg_id, None)

    def get_all_votes(self) -> dict:
        with self._lock:
            return {k: v.copy() for k, v in self._votes.items()}

    # First vote feature methods
    def is_first_vote_enabled(self, chat_id: int) -> bool:
        with self._lock:
            return chat_id in self._first_vote

    def enable_first_vote(self, chat_id: int) -> None:
        with self._lock:
            if chat_id not in self._first_vote:
                self._first_vote.append(chat_id)

    def disable_first_vote(self, chat_id: int) -> None:
        with self._lock:
            if chat_id in self._first_vote:
                self._first_vote.remove(chat_id)

    def get_first_vote_chats(self) -> list[int]:
        with self._lock:
            return self._first_vote.copy()

    # First vote data methods
    def get_first_vote_data(self, chat_id: int) -> dict:
        with self._lock:
            return self._first_vote_data.get(chat_id, {}).copy()

    def set_first_vote_data(self, chat_id: int, data: dict) -> None:
        with self._lock:
            self._first_vote_data[chat_id] = data.copy()

    def record_first_vote(self, chat_id: int, user_id: int, choice: Any) -> None:
        with self._lock:
            if chat_id not in self._first_vote_data:
                self._first_vote_data[chat_id] = {}
            self._first_vote_data[chat_id][user_id] = choice

    def has_user_voted(self, chat_id: int, user_id: int) -> bool:
        with self._lock:
            return user_id in self._first_vote_data.get(chat_id, {})

    def clear_first_vote_data(self, chat_id: int) -> None:
        with self._lock:
            self._first_vote_data.pop(chat_id, None)

    # Key-based first vote data methods (for message-specific voting)
    def get_first_vote_data_by_key(self, key: str, default: Optional[dict] = None) -> dict:
        """Get first vote data by string key (e.g., '{message_id}{chat_id}')."""
        with self._lock:
            data = self._first_vote_data.get(key)
            if data is not None:
                return data.copy()
            return default.copy() if default else {}

    def set_first_vote_data_by_key(self, key: str, data: dict) -> None:
        """Set first vote data by string key."""
        with self._lock:
            self._first_vote_data[key] = data.copy()

    # Bulk loading
    def load_votes(self, votes_data: dict) -> None:
        with self._lock:
            self._votes = {k: v.copy() if isinstance(v, dict) else v for k, v in votes_data.items()}

    def load_first_vote(self, chat_ids: list[int]) -> None:
        with self._lock:
            self._first_vote = chat_ids.copy()

    def load_first_vote_data(self, data: dict) -> None:
        with self._lock:
            self._first_vote_data = {k: v.copy() if isinstance(v, dict) else v for k, v in data.items()}

    # Vote weights by address (for weighted polls)
    def get_vote_weights(self, address: str) -> Optional[dict]:
        """Get vote weights for a Stellar address."""
        with self._lock:
            data = self._vote_weights.get(address)
            return data.copy() if data else None

    def get_all_vote_weights(self) -> dict:
        """Get all vote weights."""
        with self._lock:
            return {k: v.copy() for k, v in self._vote_weights.items()}

    def set_vote_weights(self, address: str, weights: dict) -> None:
        """Set vote weights for a Stellar address."""
        with self._lock:
            self._vote_weights[address] = weights.copy()

    def set_all_vote_weights(self, vote_weights: dict) -> None:
        """Set all vote weights (replaces entire structure)."""
        with self._lock:
            self._vote_weights = {k: v.copy() if isinstance(v, dict) else v for k, v in vote_weights.items()}

    def get_user_vote_weight(self, address: str, user: str) -> Optional[int]:
        """Get vote weight for a specific user at an address."""
        with self._lock:
            weights = self._vote_weights.get(address, {})
            return weights.get(user) or weights.get(str(user))
