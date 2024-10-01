import json
from datetime import datetime
from enum import Enum
from typing import Dict, Optional, List, Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from pydantic import BaseModel

from utils.config_reader import config
from utils.pyro_tools import GroupMember

client = AsyncIOMotorClient(config.mongodb_url)
db = client['mtl_tables']
bot_config_collection = db['bot_config']
chats_collection = db['chats']


class BotEntry(BaseModel):
    chat_id: int
    chat_key: int
    chat_key_name: Optional[str]
    chat_value: Optional[str]


class BotMongoConfig:
    def __init__(self):
        self.collection: AsyncIOMotorCollection = bot_config_collection
        self.chats_collection: AsyncIOMotorCollection = chats_collection

    async def save_bot_value(self, chat_id: int, chat_key: int | Enum, chat_value: Any):
        chat_key_value = chat_key if isinstance(chat_key, int) else chat_key.value
        chat_key_name = chat_key.name if isinstance(chat_key, Enum) else None

        if chat_value is None:
            await self.collection.delete_one({"chat_id": chat_id, "chat_key": chat_key_value})
        else:
            await self.collection.update_one(
                {"chat_id": chat_id, "chat_key": chat_key_value},
                {"$set": {
                    "chat_key_name": chat_key_name,
                    "chat_value": str(chat_value)
                }},
                upsert=True
            )

    async def load_bot_value(self, chat_id: int, chat_key: int | Enum, default_value: Any = ''):
        chat_key = chat_key if isinstance(chat_key, int) else chat_key.value
        result = await self.collection.find_one({"chat_id": chat_id, "chat_key": chat_key})
        return result['chat_value'] if result else default_value

    async def get_chat_ids_by_key(self, chat_key: int | Enum) -> List[int]:
        chat_key = chat_key if isinstance(chat_key, int) else chat_key.value
        cursor = self.collection.find({"chat_key": chat_key})
        results = await cursor.to_list(length=None)
        return [result['chat_id'] for result in results]

    async def get_chat_dict_by_key(self, chat_key: int | Enum, return_json=False) -> Dict[int, Any]:
        chat_key = chat_key if isinstance(chat_key, int) else chat_key.value
        cursor = self.collection.find({"chat_key": chat_key})
        results = await cursor.to_list(length=None)
        if return_json:
            return {result['chat_id']: json.loads(result['chat_value']) for result in results}
        else:
            return {result['chat_id']: result['chat_value'] for result in results}

    async def update_chat_info(self, chat_id: int, members: List[GroupMember], clear_users=False):
        now = datetime.utcnow()

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

    async def add_user_to_chat(self, chat_id: int, member: GroupMember):
        now = datetime.utcnow()
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

        now = datetime.utcnow()
        update_result = await self.chats_collection.update_one(
            {"chat_id": chat_id},
            {
                "$unset": {f"users.{user_id}": ""},
                "$pull": {"admins": user_id},
                "$set": {"last_updated": now}
            }
        )

        return update_result.modified_count > 0
