import pytest
from unittest.mock import MagicMock, patch
from services.database_service import DatabaseService
from db.repositories.config import ConfigRepository

@pytest.fixture
def mock_session_pool():
    with patch("services.database_service.SessionPool") as mock:
        yield mock

def test_save_bot_value_delegation(mock_session_pool):
    # Setup
    service = DatabaseService()
    session_instance = MagicMock()
    mock_session_pool.return_value.__enter__.return_value = session_instance
    
    chat_id = 1
    key = 2
    value = "val"
    
    # Mock Repository within the service context
    # Since ConfigRepository is instantiated inside the method, we can patch it 
    # or just verify session interactions if we trust repository logic (tested separately).
    # Better to patch ConfigRepository to verify delegation.
    
    with patch("services.database_service.ConfigRepository") as MockRepo:
        repo_instance = MockRepo.return_value
        
        # Execute
        # Since the service methods run in a thread (asyncio.to_thread), we need to run async test
        # But for unit testing logic, we can test the sync methods if they were exposed, 
        # or run the async method.
        import asyncio
        asyncio.run(service.save_bot_value(chat_id, key, value))
        
        # Verify
        MockRepo.assert_called_with(session_instance)
        repo_instance.save_bot_value.assert_called_with(chat_id, key, value)
        session_instance.commit.assert_called_once()

def test_load_bot_value_delegation(mock_session_pool):
    service = DatabaseService()
    session_instance = MagicMock()
    mock_session_pool.return_value.__enter__.return_value = session_instance
    
    expected_value = "loaded"
    
    with patch("services.database_service.ConfigRepository") as MockRepo:
        repo_instance = MockRepo.return_value
        repo_instance.load_bot_value.return_value = expected_value
        
        import asyncio
        result = asyncio.run(service.load_bot_value(1, 2))
        
        assert result == expected_value
        repo_instance.load_bot_value.assert_called_with(1, 2, '')

def test_update_chat_info_delegation(mock_session_pool):
    service = DatabaseService()
    session_instance = MagicMock()
    mock_session_pool.return_value.__enter__.return_value = session_instance
    
    chat_id = 100
    members = []
    
    with patch("services.database_service.ChatsRepository") as MockRepo:
        repo_instance = MockRepo.return_value
        
        import asyncio
        asyncio.run(service.update_chat_info(chat_id, members))
        
        MockRepo.assert_called_with(session_instance)
        repo_instance.update_chat_info.assert_called_with(chat_id, members, False)
        session_instance.commit.assert_called_once()
