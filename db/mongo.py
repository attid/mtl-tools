import json
import os
from enum import Enum
from typing import Dict, Optional, List, Any
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from pydantic import BaseModel

from config_reader import config

client = AsyncIOMotorClient(config.mongo_uri)
db = client['skynet']
bot_config_collection = db['bot_config']


class BotEntry(BaseModel):
    chat_id: int
    chat_key: int
    chat_key_name: Optional[str]
    chat_value: Optional[str]


class BotMongoConfig:
    def __init__(self):
        self.collection: AsyncIOMotorCollection = bot_config_collection

    async def save_bot_value(self, chat_id: int, chat_key: Enum, chat_value: Any):
        chat_key_name = chat_key.name
        chat_key_value = chat_key.value

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
