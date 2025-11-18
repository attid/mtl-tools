import asyncio
import json
from datetime import datetime, timedelta, UTC
from enum import Enum
from typing import Dict, Optional, List, Any

from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.orm import Session, sessionmaker
from pydantic import BaseModel, Field

from other.config_reader import config
from other.pyro_tools import GroupMember, get_group_members, pyro_app

# Импортируем SQLAlchemy модели
from shared.infrastructure.database.models import (
    BotConfig, Chat, ChatMember, KVStore
)


class BotEntry(BaseModel):
    chat_id: int
    chat_key: int
    chat_key_name: Optional[str]
    chat_value: Optional[str]


class MongoUser(BaseModel):
    user_id: Optional[int] = None
    username: Optional[str]
    full_name: str
    is_admin: bool = False
    created_at: datetime
    left_at: Optional[datetime] = None

class MongoChat(BaseModel):
    chat_id: int
    username: Optional[str] = None
    title: Optional[str] = None
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    users: Dict[str, MongoUser] = Field(default_factory=dict)
    admins: List[int] = Field(default_factory=list)

class BotMongoConfig:
    def __init__(self, db_pool: sessionmaker = None):
        self.db_pool = db_pool  # Пул сессий SQLAlchemy

    async def save_bot_value(self, chat_id: int, chat_key: int | Enum, chat_value: Any):
        chat_key_value = chat_key if isinstance(chat_key, int) else chat_key.value
        chat_key_name = chat_key.name if isinstance(chat_key, Enum) else None

        await asyncio.to_thread(
            self._save_bot_value_sync, chat_id, chat_key_value, chat_key_name, chat_value
        )

    def _save_bot_value_sync(self, chat_id: int, chat_key_value: int, chat_key_name: str, chat_value: Any):
        def prepare_chat_value(value: Any):
            if value is None:
                return None

            if isinstance(value, str):
                stripped = value.strip()
                if stripped and stripped[0] in '{"[' or stripped.startswith('"'):
                    try:
                        parsed = json.loads(value)
                        if isinstance(parsed, str):
                            inner_stripped = parsed.strip()
                            if inner_stripped and inner_stripped[0] in '{"[' or inner_stripped.startswith('"'):
                                try:
                                    parsed = json.loads(parsed)
                                except json.JSONDecodeError:
                                    pass
                        if isinstance(parsed, dict) and set(parsed.keys()) == {"value"} and isinstance(parsed["value"], str):
                            try:
                                parsed = json.loads(parsed["value"])
                            except json.JSONDecodeError:
                                pass
                        return parsed
                    except json.JSONDecodeError:
                        pass
                return value

            return value

        with self.db_pool() as session:
            if chat_value is None:
                # Удаляем запись
                stmt = delete(BotConfig).where(
                    and_(BotConfig.chat_id == chat_id, BotConfig.chat_key == chat_key_value)
                )
                session.execute(stmt)
            else:
                prepared_value = prepare_chat_value(chat_value)

                # Обновляем или создаем запись
                # Проверяем, существует ли запись
                existing = session.execute(
                    select(BotConfig).where(
                        and_(BotConfig.chat_id == chat_id, BotConfig.chat_key == chat_key_value)
                    )
                )
                existing_record = existing.scalar_one_or_none()

                if existing_record:
                    # Обновляем существующую запись
                    existing_record.chat_key_name = chat_key_name
                    existing_record.chat_value = prepared_value
                else:
                    # Создаем новую запись
                    chat_data = prepare_chat_value(chat_value)

                    new_record = BotConfig(
                        chat_id=chat_id,
                        chat_key=chat_key_value,
                        chat_key_name=chat_key_name,
                        chat_value=chat_data
                    )
                    session.add(new_record)

            session.commit()

    async def load_bot_value(self, chat_id: int, chat_key: int | Enum, default_value: Any = ''):
        chat_key = chat_key if isinstance(chat_key, int) else chat_key.value

        return await asyncio.to_thread(
            self._load_bot_value_sync, chat_id, chat_key, default_value
        )

    def _load_bot_value_sync(self, chat_id: int, chat_key: int, default_value: Any):
        with self.db_pool() as session:
            result = session.execute(
                select(BotConfig).where(
                    and_(BotConfig.chat_id == chat_id, BotConfig.chat_key == chat_key)
                )
            )
            record = result.scalar_one_or_none()

            if record and record.chat_value:
                # Если значение - это словарь с одним ключом "value", возвращаем значение
                if isinstance(record.chat_value, dict) and "value" in record.chat_value and len(record.chat_value) == 1:
                    return record.chat_value["value"]

                if isinstance(record.chat_value, (dict, list)):
                    try:
                        return json.dumps(record.chat_value)
                    except TypeError:
                        return str(record.chat_value)

                if isinstance(record.chat_value, str):
                    stripped = record.chat_value.strip()
                    if stripped and stripped[0] in '{"[' or stripped.startswith('"'):
                        try:
                            parsed = json.loads(record.chat_value)
                            if isinstance(parsed, (dict, list)):
                                return json.dumps(parsed)
                            if isinstance(parsed, str):
                                return parsed
                        except json.JSONDecodeError:
                            pass
                return record.chat_value
            return default_value

    async def get_chat_ids_by_key(self, chat_key: int | Enum) -> List[int]:
        chat_key = chat_key if isinstance(chat_key, int) else chat_key.value

        return await asyncio.to_thread(
            self._get_chat_ids_by_key_sync, chat_key
        )

    def _get_chat_ids_by_key_sync(self, chat_key: int) -> List[int]:
        with self.db_pool() as session:
            result = session.execute(
                select(BotConfig.chat_id).where(BotConfig.chat_key == chat_key)
            )
            return [row[0] for row in result.fetchall()]

    async def get_chat_dict_by_key(self, chat_key: int | Enum, return_json=False) -> Dict[int, Any]:
        chat_key = chat_key if isinstance(chat_key, int) else chat_key.value

        return await asyncio.to_thread(
            self._get_chat_dict_by_key_sync, chat_key, return_json
        )

    def _get_chat_dict_by_key_sync(self, chat_key: int, return_json: bool) -> Dict[int, Any]:
        with self.db_pool() as session:
            result = session.execute(
                select(BotConfig).where(BotConfig.chat_key == chat_key)
            )
            records = result.scalars().all()

            result_dict = {}
            for record in records:
                if record.chat_value:
                    if return_json and isinstance(record.chat_value, str):
                        result_dict[record.chat_id] = json.loads(record.chat_value)
                    else:
                        # Если значение - это словарь с одним ключом "value", возвращаем значение
                        if isinstance(record.chat_value, dict) and "value" in record.chat_value and len(record.chat_value) == 1:
                            result_dict[record.chat_id] = record.chat_value["value"]
                        else:
                            result_dict[record.chat_id] = record.chat_value

            return result_dict

    async def update_dict_value(self, chat_id: int, chat_key: int | Enum, dict_key: str, dict_value: Any):
        chat_key_value = chat_key if isinstance(chat_key, int) else chat_key.value

        await asyncio.to_thread(
            self._update_dict_value_sync, chat_id, chat_key_value, dict_key, dict_value
        )

    def _update_dict_value_sync(self, chat_id: int, chat_key_value: int, dict_key: str, dict_value: Any):
        with self.db_pool() as session:
            # Получаем существующую запись
            result = session.execute(
                select(BotConfig).where(
                    and_(BotConfig.chat_id == chat_id, BotConfig.chat_key == chat_key_value)
                )
            )
            record = result.scalar_one_or_none()

            if record:
                # Обновляем значение в словаре
                if record.chat_value is None:
                    record.chat_value = {}
                elif isinstance(record.chat_value, str):
                    # Если это строка, конвертируем в словарь
                    try:
                        record.chat_value = json.loads(record.chat_value)
                    except:
                        record.chat_value = {"value": record.chat_value}
                elif isinstance(record.chat_value, dict) and "value" in record.chat_value and len(record.chat_value) == 1:
                    # Если это простой словарь с одним значением, преобразуем в пустой словарь
                    record.chat_value = {}

                record.chat_value[dict_key] = dict_value
            else:
                # Создаем новую запись
                new_record = BotConfig(
                    chat_id=chat_id,
                    chat_key=chat_key_value,
                    chat_value={dict_key: dict_value}
                )
                session.add(new_record)

            session.commit()

    async def get_dict_value(self, chat_id: int, chat_key: int | Enum, dict_key: str,
                             default_value: Any = None) -> Any:
        chat_key_value = chat_key if isinstance(chat_key, int) else chat_key.value

        return await asyncio.to_thread(
            self._get_dict_value_sync, chat_id, chat_key_value, dict_key, default_value
        )

    def _get_dict_value_sync(self, chat_id: int, chat_key_value: int, dict_key: str, default_value: Any) -> Any:
        with self.db_pool() as session:
            result = session.execute(
                select(BotConfig).where(
                    and_(BotConfig.chat_id == chat_id, BotConfig.chat_key == chat_key_value)
                )
            )
            record = result.scalar_one_or_none()

            if record and record.chat_value:
                # Если это строка, пытаемся распарсить как JSON
                if isinstance(record.chat_value, str):
                    try:
                        chat_data = json.loads(record.chat_value)
                    except:
                        chat_data = {"value": record.chat_value}
                else:
                    chat_data = record.chat_value

                # Если это простой словарь с одним ключом "value", а нам нужен другой ключ
                if isinstance(chat_data, dict) and "value" in chat_data and len(chat_data) == 1 and dict_key != "value":
                    return default_value

                return chat_data.get(dict_key, default_value)

            return default_value

    async def update_chat_info(self, chat_id: int, members: List[GroupMember], clear_users=False):
        now = datetime.now(UTC)

        await asyncio.to_thread(
            self._update_chat_info_sync, chat_id, members, clear_users, now
        )

    def _update_chat_info_sync(self, chat_id: int, members: List[GroupMember], clear_users: bool, now: datetime):
        with self.db_pool() as session:
            # Получаем текущую информацию о чате
            result = session.execute(
                select(Chat).where(Chat.chat_id == chat_id)
            )
            chat = result.scalar_one_or_none()

            if not chat:
                # Создаем новый чат
                chat = Chat(
                    chat_id=chat_id,
                    created_at=now,
                    last_updated=now,
                    admins=[],
                    metadata_={}
                )
                session.add(chat)
                session.flush()  # Получаем ID нового чата

            # Если clear_users=True, удаляем всех участников
            if clear_users:
                session.execute(
                    delete(ChatMember).where(ChatMember.chat_id == chat_id)
                )
                chat.admins = []

            # Обновляем информацию о чате
            chat.last_updated = now

            # Добавляем или обновляем участников
            admin_ids = set(chat.admins) if chat.admins else set()

            # Импортируем модель BotUsers
            from shared.infrastructure.database.models import BotUsers

            for member in members:
                # Проверяем, существует ли пользователь в bot_users
                user_result = session.execute(
                    select(BotUsers).where(BotUsers.user_id == member.user_id)
                )
                user_record = user_result.scalar_one_or_none()

                if not user_record:
                    # Создаем пользователя в bot_users
                    new_user = BotUsers(
                        user_id=member.user_id,
                        user_name=member.username,
                        user_type=0  # дефолтный тип
                    )
                    session.add(new_user)
                    session.flush()  # Гарантируем, что пользователь создан

                # Проверяем, существует ли участник
                existing_member = session.execute(
                    select(ChatMember).where(
                        and_(ChatMember.chat_id == chat_id, ChatMember.user_id == member.user_id)
                    )
                )
                member_record = existing_member.scalar_one_or_none()

                member_metadata = {
                    "username": member.username,
                    "full_name": member.full_name,
                    "is_admin": member.is_admin
                }

                if member_record:
                    # Обновляем существующего участника
                    member_record.metadata_ = member_metadata
                    if member_record.left_at:  # Если пользователь вернулся
                        member_record.left_at = None
                else:
                    # Создаем нового участника
                    new_member = ChatMember(
                        chat_id=chat_id,
                        user_id=member.user_id,
                        created_at=now,
                        metadata_=member_metadata
                    )
                    session.add(new_member)

                # Обновляем список админов
                if member.is_admin:
                    admin_ids.add(member.user_id)
                else:
                    admin_ids.discard(member.user_id)

            # Обновляем список админов в чате
            chat.admins = list(admin_ids)

            session.commit()
            return True

    ####################################################################################################################
    async def load_kv_value(self, kv_key: str, default_value: Any = None):
        return await asyncio.to_thread(
            self._load_kv_value_sync, kv_key, default_value
        )

    def _load_kv_value_sync(self, kv_key: str, default_value: Any):
        with self.db_pool() as session:
            result = session.execute(
                select(KVStore).where(KVStore.kv_key == kv_key)
            )
            record = result.scalar_one_or_none()
            return record.kv_value if record else default_value

    async def save_kv_value(self, kv_key: str, kv_value: Any):
        await asyncio.to_thread(
            self._save_kv_value_sync, kv_key, kv_value
        )

    def _save_kv_value_sync(self, kv_key: str, kv_value: Any):
        with self.db_pool() as session:
            # Проверяем, существует ли запись
            result = session.execute(
                select(KVStore).where(KVStore.kv_key == kv_key)
            )
            record = result.scalar_one_or_none()

            if record:
                record.kv_value = kv_value
            else:
                new_record = KVStore(kv_key=kv_key, kv_value=kv_value)
                session.add(new_record)

            session.commit()

    ####################################################################################################################

    async def add_user_to_chat(self, chat_id: int, member: GroupMember):
        now = datetime.now(UTC)

        await asyncio.to_thread(
            self._add_user_to_chat_sync, chat_id, member, now
        )

    def _add_user_to_chat_sync(self, chat_id: int, member: GroupMember, now: datetime):
        with self.db_pool() as session:
            # Получаем или создаем чат
            result = session.execute(
                select(Chat).where(Chat.chat_id == chat_id)
            )
            chat = result.scalar_one_or_none()

            if not chat:
                chat = Chat(
                    chat_id=chat_id,
                    created_at=now,
                    last_updated=now,
                    admins=[],
                    metadata_={}
                )
                session.add(chat)
                session.flush()

            # Обновляем время последнего обновления чата
            chat.last_updated = now

            # Проверяем, существует ли пользователь в bot_users
            from shared.infrastructure.database.models import BotUsers
            user_result = session.execute(
                select(BotUsers).where(BotUsers.user_id == member.user_id)
            )
            user_record = user_result.scalar_one_or_none()

            if not user_record:
                # Создаем пользователя в bot_users
                new_user = BotUsers(
                    user_id=member.user_id,
                    user_name=member.username,
                    user_type=0  # дефолтный тип
                )
                session.add(new_user)
                session.flush()  # Гарантируем, что пользователь создан

            # Проверяем, существует ли участник чата
            existing_member = session.execute(
                select(ChatMember).where(
                    and_(ChatMember.chat_id == chat_id, ChatMember.user_id == member.user_id)
                )
            )
            member_record = existing_member.scalar_one_or_none()

            member_metadata = {
                "username": member.username,
                "full_name": member.full_name,
                "is_admin": member.is_admin
            }

            if member_record:
                # Обновляем существующего участника
                member_record.metadata_ = member_metadata
                if member_record.left_at:  # Если пользователь вернулся
                    member_record.left_at = None
            else:
                # Создаем нового участника
                new_member = ChatMember(
                    chat_id=chat_id,
                    user_id=member.user_id,
                    created_at=now,
                    metadata_=member_metadata
                )
                session.add(new_member)

            # Обновляем список админов
            if member.is_admin and member.user_id not in (chat.admins or []):
                if not chat.admins:
                    chat.admins = []
                chat.admins.append(member.user_id)

            session.commit()
            return True

    async def remove_user_from_chat(self, chat_id: int, user_id: int):
        return await asyncio.to_thread(
            self._remove_user_from_chat_sync, chat_id, user_id
        )

    def _remove_user_from_chat_sync(self, chat_id: int, user_id: int):
        with self.db_pool() as session:
            # Проверяем, существует ли чат
            result = session.execute(
                select(Chat).where(Chat.chat_id == chat_id)
            )
            chat = result.scalar_one_or_none()
            if not chat:
                return False  # Чат не существует

            now = datetime.now(UTC)

            # Проверяем, существует ли участник
            result = session.execute(
                select(ChatMember).where(
                    and_(ChatMember.chat_id == chat_id, ChatMember.user_id == user_id)
                )
            )
            member_record = result.scalar_one_or_none()

            if member_record and not member_record.left_at:
                # Обновляем участника, отмечаем, что он вышел
                member_record.left_at = now
                # Обновляем metadata
                if member_record.metadata_:
                    member_record.metadata_["left_at"] = now

            # Удаляем пользователя из списка админов
            if chat.admins and user_id in chat.admins:
                chat.admins.remove(user_id)

            # Обновляем время последнего обновления чата
            chat.last_updated = now

            session.commit()
            return member_record is not None

    async def get_users_joined_last_day(self, chat_id: int) -> List[MongoUser]:
        one_day_ago = datetime.now() - timedelta(days=1)

        return await asyncio.to_thread(
            self._get_users_joined_last_day_sync, chat_id, one_day_ago
        )

    def _get_users_joined_last_day_sync(self, chat_id: int, one_day_ago: datetime) -> List[MongoUser]:
        with self.db_pool() as session:
            result = session.execute(
                select(ChatMember).where(
                    and_(
                        ChatMember.chat_id == chat_id,
                        ChatMember.created_at > one_day_ago
                    )
                )
            )
            members = result.scalars().all()

            mongo_users = []
            for member in members:
                metadata = member.metadata_ or {}
                mongo_user = MongoUser(
                    user_id=member.user_id,
                    username=metadata.get("username"),
                    full_name=metadata.get("full_name", ""),
                    is_admin=metadata.get("is_admin", False),
                    created_at=member.created_at,
                    left_at=member.left_at
                )
                mongo_users.append(mongo_user)

            return mongo_users

    async def get_users_left_last_day(self, chat_id: int) -> List[MongoUser]:
        one_day_ago = datetime.now() - timedelta(days=1)

        return await asyncio.to_thread(
            self._get_users_left_last_day_sync, chat_id, one_day_ago
        )

    def _get_users_left_last_day_sync(self, chat_id: int, one_day_ago: datetime) -> List[MongoUser]:
        with self.db_pool() as session:
            result = session.execute(
                select(ChatMember).where(
                    and_(
                        ChatMember.chat_id == chat_id,
                        ChatMember.left_at > one_day_ago
                    )
                )
            )
            members = result.scalars().all()

            mongo_users = []
            for member in members:
                metadata = member.metadata_ or {}
                mongo_user = MongoUser(
                    user_id=member.user_id,
                    username=metadata.get("username"),
                    full_name=metadata.get("full_name", ""),
                    is_admin=metadata.get("is_admin", False),
                    created_at=member.created_at,
                    left_at=member.left_at
                )
                mongo_users.append(mongo_user)

            return mongo_users

    async def get_all_chats(self) -> List[MongoChat]:
        return await asyncio.to_thread(
            self._get_all_chats_sync
        )

    def _get_all_chats_sync(self) -> List[MongoChat]:
        with self.db_pool() as session:
            result = session.execute(select(Chat))
            chats = result.scalars().all()

            mongo_chats = []
            for chat in chats:
                # Получаем всех участников чата
                members_result = session.execute(
                    select(ChatMember).where(ChatMember.chat_id == chat.chat_id)
                )
                members = members_result.scalars().all()

                # Конвертируем участников в формат MongoDB
                users_dict = {}
                for member in members:
                    metadata = member.metadata_ or {}
                    users_dict[str(member.user_id)] = {
                        "username": metadata.get("username"),
                        "full_name": metadata.get("full_name"),
                        "is_admin": metadata.get("is_admin", False),
                        "created_at": member.created_at,
                        "left_at": member.left_at
                    }

                mongo_chat = MongoChat(
                    chat_id=chat.chat_id,
                    username=chat.username,
                    title=chat.title,
                    created_at=chat.created_at,
                    last_updated=chat.last_updated,
                    users=users_dict,
                    admins=chat.admins or []
                )
                mongo_chats.append(mongo_chat)

            return mongo_chats

    async def get_all_chats_by_user(self, user_id: int) -> List[MongoChat]:
        return await asyncio.to_thread(
            self._get_all_chats_by_user_sync, user_id
        )

    def _get_all_chats_by_user_sync(self, user_id: int) -> List[MongoChat]:
        with self.db_pool() as session:
            # Ищем все чаты, где есть участник с указанным user_id
            result = session.execute(
                select(ChatMember).where(ChatMember.user_id == user_id)
            )
            memberships = result.scalars().all()

            mongo_chats = []
            for membership in memberships:
                # Получаем информацию о чате
                chat_result = session.execute(
                    select(Chat).where(Chat.chat_id == membership.chat_id)
                )
                chat = chat_result.scalar_one_or_none()

                if chat:
                    metadata = membership.metadata_ or {}
                    users_dict = {
                        str(membership.user_id): {
                            "username": metadata.get("username"),
                            "full_name": metadata.get("full_name"),
                            "is_admin": metadata.get("is_admin", False),
                            "created_at": membership.created_at,
                            "left_at": membership.left_at
                        }
                    }

                    mongo_chat = MongoChat(
                        chat_id=chat.chat_id,
                        username=chat.username,
                        title=chat.title,
                        created_at=chat.created_at,
                        last_updated=chat.last_updated,
                        users=users_dict,
                        admins=chat.admins or []
                    )
                    mongo_chats.append(mongo_chat)

            return mongo_chats

    async def update_chat_with_dict(self, chat_id: int, update_data: Dict) -> bool:
        return await asyncio.to_thread(
            self._update_chat_with_dict_sync, chat_id, update_data
        )

    def _update_chat_with_dict_sync(self, chat_id: int, update_data: Dict) -> bool:
        with self.db_pool() as session:
            result = session.execute(
                select(Chat).where(Chat.chat_id == chat_id)
            )
            chat = result.scalar_one_or_none()

            if not chat:
                return False

            # Обновляем поля чата
            for key, value in update_data.items():
                if hasattr(chat, key):
                    setattr(chat, key, value)
                else:
                    # Если поля нет в модели, добавляем в metadata
                    if not chat.metadata_:
                        chat.metadata_ = {}
                    chat.metadata_[key] = value

            # Обновляем last_updated
            chat.last_updated = datetime.now(UTC)

            session.commit()
            return True


async def update_users():
    # обновить список пользователей в чате
    await pyro_app.start()

    # Получаем пул сессий из global_data или создаем новый
    from db.quik_pool import quik_pool

    await BotMongoConfig(quik_pool).update_chat_info(-1001239694752, await get_group_members(-1001239694752))
    await pyro_app.stop()


async def local_test():
    from db.quik_pool import quik_pool
    mongo_config = BotMongoConfig(quik_pool)
    from other.global_data import BotValueTypes
    print(BotValueTypes.Votes.value)
    a = await mongo_config.load_bot_value(0, BotValueTypes.Votes, '{}')
    print(a)
    #global_data.votes = json.loads(await mongo_config.load_bot_value(0, BotValueTypes.Votes, '{}'))


if __name__ == "__main__":
    # _ = asyncio.run(update_users(''))
    #from db.quik_pool import quik_pool
    #_ = asyncio.run(BotMongoConfig(quik_pool).get_all_chats_by_user(6227392660))
    #print(_)
    asyncio.run(local_test())