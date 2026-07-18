"""Tests for Redis-backed throttling scopes."""

import asyncio
import datetime
from types import SimpleNamespace
from typing import Any, cast

import pytest
from aiogram import types

import middlewares.throttling as throttling
from tests.fakes import FakeAsyncMethod


class FakeRedis:
    def __init__(self):
        self.values: dict[str, dict[str, float]] = {}
        self.ttls: dict[str, int] = {}

    async def hmget(self, name: str, keys: list[str]):
        bucket = self.values.get(name, {})
        await asyncio.sleep(0)
        return [bucket.get(key) for key in keys]

    async def hset(self, name: str, *, mapping: dict[str, float]):
        self.values[name] = mapping.copy()

    async def set(self, name: str, value: str, *, nx: bool, px: int):
        if nx and name in self.values:
            return None
        self.values[name] = {"value": float(value)}
        self.ttls[name] = px
        return True

    async def pttl(self, name: str):
        return self.ttls.get(name, -2)


def _message(*, chat_id: int, user_id: int) -> types.Message:
    return types.Message(
        message_id=1,
        date=datetime.datetime.now(),
        chat=types.Chat(id=chat_id, type="supergroup", title="Test"),
        from_user=types.User(id=user_id, is_bot=False, first_name="User"),
        text="/tr en hello",
    )


@pytest.mark.asyncio
async def test_global_user_rate_limit_blocks_same_user_across_chats():
    @throttling.global_user_rate_limit(5, "translate")
    async def handler():
        return None

    redis = FakeRedis()
    middleware = throttling.ThrottlingMiddleware(cast(Any, redis))
    middleware.event_throttled = FakeAsyncMethod()
    data = {"handler": SimpleNamespace(callback=handler)}

    await middleware.on_process_event(_message(chat_id=-1001, user_id=42), data)

    with pytest.raises(throttling.CancelHandler):
        await middleware.on_process_event(_message(chat_id=-1002, user_id=42), data)

    assert list(redis.values) == ["throttle_translate_42"]


@pytest.mark.asyncio
async def test_global_user_rate_limit_is_atomic_for_concurrent_requests():
    @throttling.global_user_rate_limit(5, "translate")
    async def handler():
        return None

    redis = FakeRedis()
    middleware = throttling.ThrottlingMiddleware(cast(Any, redis))
    middleware.event_throttled = FakeAsyncMethod()
    data = {"handler": SimpleNamespace(callback=handler)}

    results = await asyncio.gather(
        middleware.on_process_event(_message(chat_id=-1001, user_id=42), data),
        middleware.on_process_event(_message(chat_id=-1002, user_id=42), data),
        return_exceptions=True,
    )

    assert sum(isinstance(result, throttling.CancelHandler) for result in results) == 1
