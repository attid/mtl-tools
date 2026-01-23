import asyncio
import json
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from db.session import SessionPool
from db.repositories import ConfigRepository, ChatsRepository, ChatDTO, ChatUserDTO
from other.pyro_tools import GroupMember


class DatabaseService:
    def __init__(self):
        self.session_pool = SessionPool

    # --- ConfigRepository methods ---

    async def save_bot_value(self, chat_id: int, chat_key: Union[int, Enum], chat_value: Any):
        await asyncio.to_thread(self._save_bot_value_sync, chat_id, chat_key, chat_value)

    def _save_bot_value_sync(self, chat_id, chat_key, chat_value):
        with self.session_pool() as session:
            repo = ConfigRepository(session)
            repo.save_bot_value(chat_id, chat_key, chat_value)
            session.commit()

    async def load_bot_value(self, chat_id: int, chat_key: Union[int, Enum], default_value: Any = '') -> Any:
        return await asyncio.to_thread(self._load_bot_value_sync, chat_id, chat_key, default_value)

    def _load_bot_value_sync(self, chat_id, chat_key, default_value):
        with self.session_pool() as session:
            repo = ConfigRepository(session)
            return repo.load_bot_value(chat_id, chat_key, default_value)

    async def get_chat_ids_by_key(self, chat_key: Union[int, Enum]) -> List[int]:
        return await asyncio.to_thread(self._get_chat_ids_by_key_sync, chat_key)

    def _get_chat_ids_by_key_sync(self, chat_key):
        with self.session_pool() as session:
            repo = ConfigRepository(session)
            return repo.get_chat_ids_by_key(chat_key)

    async def get_chat_dict_by_key(self, chat_key: Union[int, Enum], return_json=False) -> Dict[int, Any]:
        return await asyncio.to_thread(self._get_chat_dict_by_key_sync, chat_key, return_json)

    def _get_chat_dict_by_key_sync(self, chat_key, return_json):
        with self.session_pool() as session:
            repo = ConfigRepository(session)
            return repo.get_chat_dict_by_key(chat_key, return_json)

    async def update_dict_value(self, chat_id: int, chat_key: Union[int, Enum], dict_key: str, dict_value: Any):
        await asyncio.to_thread(self._update_dict_value_sync, chat_id, chat_key, dict_key, dict_value)

    def _update_dict_value_sync(self, chat_id, chat_key, dict_key, dict_value):
        with self.session_pool() as session:
            repo = ConfigRepository(session)
            repo.update_dict_value(chat_id, chat_key, dict_key, dict_value)
            session.commit()

    async def get_dict_value(self, chat_id: int, chat_key: Union[int, Enum], dict_key: str, default_value: Any = None) -> Any:
        return await asyncio.to_thread(self._get_dict_value_sync, chat_id, chat_key, dict_key, default_value)

    def _get_dict_value_sync(self, chat_id, chat_key, dict_key, default_value):
        with self.session_pool() as session:
            repo = ConfigRepository(session)
            return repo.get_dict_value(chat_id, chat_key, dict_key, default_value)

    async def save_kv_value(self, kv_key: str, kv_value: Any):
        await asyncio.to_thread(self._save_kv_value_sync, kv_key, kv_value)

    def _save_kv_value_sync(self, kv_key, kv_value):
        with self.session_pool() as session:
            repo = ConfigRepository(session)
            repo.save_kv_value(kv_key, kv_value)
            session.commit()

    async def load_kv_value(self, kv_key: str, default_value: Any = None) -> Any:
        return await asyncio.to_thread(self._load_kv_value_sync, kv_key, default_value)

    def _load_kv_value_sync(self, kv_key, default_value):
        with self.session_pool() as session:
            repo = ConfigRepository(session)
            return repo.load_kv_value(kv_key, default_value)

    # --- ChatsRepository methods ---

    async def update_chat_info(self, chat_id: int, members: List[GroupMember], clear_users=False):
        await asyncio.to_thread(self._update_chat_info_sync, chat_id, members, clear_users)

    def _update_chat_info_sync(self, chat_id, members, clear_users):
        with self.session_pool() as session:
            repo = ChatsRepository(session)
            repo.update_chat_info(chat_id, members, clear_users)
            session.commit()

    async def add_user_to_chat(self, chat_id: int, member: GroupMember):
        await asyncio.to_thread(self._add_user_to_chat_sync, chat_id, member)

    def _add_user_to_chat_sync(self, chat_id, member):
        with self.session_pool() as session:
            repo = ChatsRepository(session)
            repo.add_user_to_chat(chat_id, member)
            session.commit()

    async def remove_user_from_chat(self, chat_id: int, user_id: int):
        return await asyncio.to_thread(self._remove_user_from_chat_sync, chat_id, user_id)

    def _remove_user_from_chat_sync(self, chat_id, user_id):
        with self.session_pool() as session:
            repo = ChatsRepository(session)
            result = repo.remove_user_from_chat(chat_id, user_id)
            session.commit()
            return result

    async def get_users_joined_last_day(self, chat_id: int) -> List[ChatUserDTO]:
        return await asyncio.to_thread(self._get_users_joined_last_day_sync, chat_id)

    def _get_users_joined_last_day_sync(self, chat_id):
        with self.session_pool() as session:
            repo = ChatsRepository(session)
            return repo.get_users_joined_last_day(chat_id)

    async def get_users_left_last_day(self, chat_id: int) -> List[ChatUserDTO]:
        return await asyncio.to_thread(self._get_users_left_last_day_sync, chat_id)

    def _get_users_left_last_day_sync(self, chat_id):
        with self.session_pool() as session:
            repo = ChatsRepository(session)
            return repo.get_users_left_last_day(chat_id)

    async def get_all_chats(self) -> List[ChatDTO]:
        return await asyncio.to_thread(self._get_all_chats_sync)

    def _get_all_chats_sync(self):
        with self.session_pool() as session:
            repo = ChatsRepository(session)
            return repo.get_all_chats()

    async def get_all_chats_by_user(self, user_id: int) -> List[ChatDTO]:
        return await asyncio.to_thread(self._get_all_chats_by_user_sync, user_id)

    def _get_all_chats_by_user_sync(self, user_id):
        with self.session_pool() as session:
            repo = ChatsRepository(session)
            return repo.get_all_chats_by_user(user_id)

    async def update_chat_with_dict(self, chat_id: int, update_data: Dict) -> bool:
        return await asyncio.to_thread(self._update_chat_with_dict_sync, chat_id, update_data)

    def _update_chat_with_dict_sync(self, chat_id, update_data):
        with self.session_pool() as session:
            repo = ChatsRepository(session)
            result = repo.update_chat_with_dict(chat_id, update_data)
            session.commit()
            return result
