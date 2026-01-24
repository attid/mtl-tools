import pytest
from unittest.mock import AsyncMock, patch
from other.aiogram_tools import cmd_sleep_and_delete_task

@pytest.mark.asyncio
async def test_cmd_sleep_and_delete_task_none_sleep_time():
    message = AsyncMock()
    
    # This should now succeed with the fix (treating None as 0 sleep)
    with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
        await cmd_sleep_and_delete_task(message, None)
        
        mock_sleep.assert_awaited_once_with(0)
        message.delete.assert_awaited_once()

@pytest.mark.asyncio
async def test_cmd_sleep_and_delete_task_valid_sleep_time():
    message = AsyncMock()
    
    # Mock asyncio.sleep to avoid waiting
    with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
        await cmd_sleep_and_delete_task(message, 10)
        
        mock_sleep.assert_awaited_once_with(10)
        message.delete.assert_awaited_once()
