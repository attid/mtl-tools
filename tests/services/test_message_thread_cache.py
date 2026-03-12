import pytest

from services.message_thread_cache import RedisMessageThreadCacheService


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.set_calls = []
        self.get_calls = []

    async def set(self, key, value, ex=None):
        self.set_calls.append((key, value, ex))
        self.values[key] = value

    async def get(self, key):
        self.get_calls.append(key)
        return self.values.get(key)


@pytest.mark.asyncio
async def test_message_thread_cache_remember_and_get():
    redis = FakeRedis()
    service = RedisMessageThreadCacheService(redis, ttl_seconds=86400)

    await service.remember_message_context(
        chat_id=123,
        message_id=456,
        thread_id=789,
        user_id=42,
        username="user",
        full_name="Test User",
    )

    payload = await service.get_message_context(123, 456)

    assert payload is not None
    assert payload["thread_id"] == 789
    assert payload["user_id"] == 42
    assert payload["username"] == "user"
    assert redis.set_calls[0][2] == 86400


@pytest.mark.asyncio
async def test_message_thread_cache_returns_none_for_missing_message():
    redis = FakeRedis()
    service = RedisMessageThreadCacheService(redis)

    payload = await service.get_message_context(1, 2)

    assert payload is None
