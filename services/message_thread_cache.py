import json
from typing import Any


class RedisMessageThreadCacheService:
    def __init__(self, redis: Any, ttl_seconds: int = 24 * 60 * 60):
        self.redis = redis
        self.ttl_seconds = ttl_seconds

    @staticmethod
    def _key(chat_id: int, message_id: int) -> str:
        return f"topic_msg:{chat_id}:{message_id}"

    async def remember_message_context(
        self,
        chat_id: int,
        message_id: int,
        thread_id: int,
        user_id: int | None = None,
        username: str | None = None,
        full_name: str | None = None,
        sender_chat_id: int | None = None,
        sender_chat_title: str | None = None,
    ) -> None:
        payload = {
            "thread_id": thread_id,
            "user_id": user_id,
            "username": username,
            "full_name": full_name,
            "sender_chat_id": sender_chat_id,
            "sender_chat_title": sender_chat_title,
        }
        await self.redis.set(self._key(chat_id, message_id), json.dumps(payload), ex=self.ttl_seconds)

    async def get_message_context(self, chat_id: int, message_id: int) -> dict[str, Any] | None:
        value = await self.redis.get(self._key(chat_id, message_id))
        if value is None:
            return None
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        return json.loads(value)
