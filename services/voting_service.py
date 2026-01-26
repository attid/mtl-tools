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
