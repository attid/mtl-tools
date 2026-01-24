import pytest
import asyncio
from other.aiogram_tools import cmd_sleep_and_delete_task
from tests.fakes import FakeAsyncMethod

@pytest.mark.asyncio
async def test_cmd_sleep_and_delete_task_none_sleep_time():
    message = type("Msg", (), {})()
    message.delete = FakeAsyncMethod(return_value=None)
    calls = []

    async def fake_sleep(seconds):
        calls.append(seconds)

    original_sleep = asyncio.sleep
    asyncio.sleep = fake_sleep
    try:
        await cmd_sleep_and_delete_task(message, None)
    finally:
        asyncio.sleep = original_sleep

    assert calls == [0]
    message.delete.assert_awaited_once()

@pytest.mark.asyncio
async def test_cmd_sleep_and_delete_task_valid_sleep_time():
    message = type("Msg", (), {})()
    message.delete = FakeAsyncMethod(return_value=None)
    calls = []

    async def fake_sleep(seconds):
        calls.append(seconds)

    original_sleep = asyncio.sleep
    asyncio.sleep = fake_sleep
    try:
        await cmd_sleep_and_delete_task(message, 10)
    finally:
        asyncio.sleep = original_sleep

    assert calls == [10]
    message.delete.assert_awaited_once()
