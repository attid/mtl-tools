import asyncio
import json
from datetime import datetime, timedelta, UTC
from enum import Enum
from typing import Dict, Optional, List, Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from pydantic import BaseModel, Field

from other.config_reader import config
from other.pyro_tools import GroupMember, get_group_members, pyro_app

client = AsyncIOMotorClient(config.mongodb_url)
db = client['mtl_tables']
bot_config_collection = db['bot_config']
chats_collection = db['chats']
bot_kv_collection = db['bot_kv']


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
    last_updated: Optional[datetime]
    users: Dict[int, MongoUser] = Field(default_factory=dict)
    admins: List[int] = []


class BotMongoConfig:
    def __init__(self):
        self.bot_config_collection: AsyncIOMotorCollection = bot_config_collection
        self.chats_collection: AsyncIOMotorCollection = chats_collection
        self.bot_kv_collection: AsyncIOMotorCollection = bot_kv_collection

    async def save_bot_value(self, chat_id: int, chat_key: int | Enum, chat_value: Any):
        chat_key_value = chat_key if isinstance(chat_key, int) else chat_key.value
        chat_key_name = chat_key.name if isinstance(chat_key, Enum) else None

        if chat_value is None:
            await self.bot_config_collection.delete_one({"chat_id": chat_id, "chat_key": chat_key_value})
        else:
            await self.bot_config_collection.update_one(
                {"chat_id": chat_id, "chat_key": chat_key_value},
                {"$set": {
                    "chat_key_name": chat_key_name,
                    "chat_value": str(chat_value)
                }},
                upsert=True
            )

    async def load_bot_value(self, chat_id: int, chat_key: int | Enum, default_value: Any = ''):
        chat_key = chat_key if isinstance(chat_key, int) else chat_key.value
        result = await self.bot_config_collection.find_one({"chat_id": chat_id, "chat_key": chat_key})
        return result['chat_value'] if result else default_value

    async def get_chat_ids_by_key(self, chat_key: int | Enum) -> List[int]:
        chat_key = chat_key if isinstance(chat_key, int) else chat_key.value
        cursor = self.bot_config_collection.find({"chat_key": chat_key})
        results = await cursor.to_list(length=None)
        return [result['chat_id'] for result in results]

    async def get_chat_dict_by_key(self, chat_key: int | Enum, return_json=False) -> Dict[int, Any]:
        chat_key = chat_key if isinstance(chat_key, int) else chat_key.value
        cursor = self.bot_config_collection.find({"chat_key": chat_key})
        results = await cursor.to_list(length=None)
        if return_json:
            return {result['chat_id']: json.loads(result['chat_value']) for result in results}
        else:
            return {result['chat_id']: result['chat_value'] for result in results}

    async def update_dict_value(self, chat_id: int, chat_key: int | Enum, dict_key: str, dict_value: Any):
        chat_key_value = chat_key if isinstance(chat_key, int) else chat_key.value
        await self.bot_config_collection.update_one(
            {"chat_id": chat_id, "chat_key": chat_key_value},
            {"$set": {f"chat_value.{dict_key}": dict_value}},
            upsert=True
        )

    async def get_dict_value(self, chat_id: int, chat_key: int | Enum, dict_key: str,
                             default_value: Any = None) -> Any:
        chat_key_value = chat_key if isinstance(chat_key, int) else chat_key.value
        result = await self.bot_config_collection.find_one(
            {"chat_id": chat_id, "chat_key": chat_key_value},
            {f"chat_value.{dict_key}": 1}
        )
        return result['chat_value'].get(dict_key, default_value) if result else default_value

    async def update_chat_info(self, chat_id: int, members: List[GroupMember], clear_users=False):
        now = datetime.now(UTC)

        # Получаем текущую информацию о чате
        current_chat_info = await self.chats_collection.find_one({"chat_id": chat_id})

        # Если чат не существует, создаем его начальную структуру
        if current_chat_info is None:
            current_chat_info = {"users": {}, "admins": []}

        # Если clear_users=True, очищаем данные, иначе используем текущие
        users_data = {} if clear_users else current_chat_info.get("users", {})
        admin_ids = [] if clear_users else current_chat_info.get("admins", [])

        for member in members:
            user_id_str = str(member.user_id)

            # Сохраняем дату создания, если пользователь уже существует
            created_at = users_data.get(user_id_str, {}).get("created_at", now)

            # Обновляем или добавляем пользователя
            users_data[user_id_str] = {
                "username": member.username,
                "full_name": member.full_name,
                "is_admin": member.is_admin,
                "created_at": created_at
            }

            if member.is_admin:
                admin_ids.append(member.user_id)

        # Обновляем информацию о чате
        update_data = {
            "users": users_data,
            "last_updated": now,
            "admins": admin_ids,
        }

        await self.chats_collection.update_one(
            {"chat_id": chat_id},
            {"$set": update_data},
            upsert=True  # upsert=True гарантирует создание документа, если его нет
        )

        return True

    ####################################################################################################################
    async def load_kv_value(self, kv_key: str, default_value: Any = None):
        result = await self.bot_kv_collection.find_one({"kv_key": kv_key})
        return result['kv_value'] if result else default_value

    async def save_kv_value(self, kv_key: str, kv_value: Any):
        await self.bot_kv_collection.update_one(
            {"kv_key": kv_key},
            {"$set": {"kv_value": kv_value}},
            upsert=True
        )

    ####################################################################################################################

    async def add_user_to_chat(self, chat_id: int, member: GroupMember):
        now = datetime.now(UTC)
        user_data = {
            "username": member.username,
            "full_name": member.full_name,
            "is_admin": member.is_admin,
            "created_at": now
        }

        # Обновляем информацию о чате, создаем если не существует
        update_result = await self.chats_collection.update_one(
            {"chat_id": chat_id},
            {
                "$set": {
                    "last_updated": now,
                    f"users.{member.user_id}": user_data
                },
                "$setOnInsert": {"created_at": now}
            },
            upsert=True
        )

        # Если пользователь админ, добавляем его ID в список админов
        if member.is_admin:
            await self.chats_collection.update_one(
                {"chat_id": chat_id},
                {"$addToSet": {"admins": member.user_id}}
            )

        return update_result.modified_count > 0 or update_result.upserted_id is not None

    async def remove_user_from_chat(self, chat_id: int, user_id: int):
        # Проверяем, существует ли чат
        chat = await self.chats_collection.find_one({"chat_id": chat_id})
        if not chat:
            return False  # Чат не существует

        now = datetime.now(UTC)
        # Обновляем информацию о пользователе, который вышел
        update_result = await self.chats_collection.update_one(
            {"chat_id": chat_id, f"users.{user_id}": {"$exists": True}},
            {
                "$set": {
                    f"users.{user_id}.left_at": now,  # Добавляем метку времени, когда пользователь вышел
                    f"users.{user_id}.is_active": False,  # Отмечаем, что пользователь больше не активен
                    "last_updated": now
                },
                "$pull": {"admins": user_id}  # Удаляем пользователя из списка админов
            }
        )

        return update_result.modified_count > 0

    async def get_users_joined_last_day(self, chat_id: int) -> List[MongoUser]:
        one_day_ago = datetime.now() - timedelta(days=1)

        chat = await self.chats_collection.find_one({"chat_id": chat_id})
        if not chat or "users" not in chat:
            return []

        joined_users = [
            MongoUser(**user_info, user_id=user_id) for user_id, user_info in chat["users"].items()
            if user_info.get("created_at") and user_info["created_at"] > one_day_ago
        ]

        return joined_users

    async def get_users_left_last_day(self, chat_id: int) -> List[MongoUser]:
        one_day_ago = datetime.now() - timedelta(days=1)

        chat = await self.chats_collection.find_one({"chat_id": chat_id})
        if not chat or "users" not in chat:
            return []

        left_users = [
            MongoUser(**user_info, user_id=user_id) for user_id, user_info in chat["users"].items()
            if user_info.get("left_at") and user_info["left_at"] > one_day_ago
        ]

        return left_users

    async def get_all_chats(self) -> List[MongoChat]:
        chats_cursor = self.chats_collection.find({})
        chats_list = await chats_cursor.to_list(length=None)
        result = []
        for chat in chats_list:
            result.append(MongoChat(**chat))

        return result

    async def update_chat_with_dict(self, chat_id: int, update_data: Dict) -> bool:
        # Обновляем запись в базе данных для указанного chat_id
        result = await self.chats_collection.update_one(
            {"chat_id": chat_id},
            {"$set": update_data}
        )
        # Возвращаем True, если хотя бы одна запись была обновлена
        return result.modified_count > 0

async def update_users():
    # обновить список пользователей в чате
    await pyro_app.start()
    await BotMongoConfig().update_chat_info(-1001239694752, await get_group_members(-1001239694752))
    await pyro_app.stop()



if __name__ == "__main__":
    _ = asyncio.run(update_users())
    #_ = asyncio.run(BotMongoConfig().get_all_chats())
    print(_)
