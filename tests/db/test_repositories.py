import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from shared.infrastructure.database.models import Base, Chat, ChatMember, BotUsers
from db.repositories.config import ConfigRepository
from db.repositories.chats import ChatsRepository
from other.pyro_tools import GroupMember
from datetime import datetime

# --- Fixtures ---

@pytest.fixture
def db_session():
    # Use in-memory SQLite for testing
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

# --- ConfigRepository Tests ---

def test_save_and_load_bot_value(db_session):
    repo = ConfigRepository(db_session)
    chat_id = 123
    chat_key = 1
    value = "test_value"

    # Test saving simple string
    repo.save_bot_value(chat_id, chat_key, value)
    db_session.commit()
    loaded_value = repo.load_bot_value(chat_id, chat_key)
    assert loaded_value == value

    # Test updating value
    new_value = "new_test_value"
    repo.save_bot_value(chat_id, chat_key, new_value)
    db_session.commit()
    loaded_value = repo.load_bot_value(chat_id, chat_key)
    assert loaded_value == new_value

    # Test deleting value
    repo.save_bot_value(chat_id, chat_key, None)
    db_session.commit()
    loaded_value = repo.load_bot_value(chat_id, chat_key, default_value="default")
    assert loaded_value == "default"

def test_json_handling(db_session):
    repo = ConfigRepository(db_session)
    chat_id = 456
    chat_key = 2
    
    # Test JSON object
    json_value = {"key": "value", "list": [1, 2, 3]}
    repo.save_bot_value(chat_id, chat_key, json_value)
    db_session.commit()
    
    loaded_value = repo.load_bot_value(chat_id, chat_key)
    # The repository might return JSON string or dict depending on implementation/DB type.
    # Postgres JSONB returns dict, but our logic handles string conversion.
    # In SQLite, it stores as JSON type or String depending on SA support.
    # ConfigRepository.load_bot_value logic:
    # if record.chat_value is dict/list -> return json.dumps (to match old behavior?) 
    # OR return raw object? Let's check implementation.
    # Implementation: if isinstance(val, (dict, list)): return json.dumps(val)
    assert json.loads(loaded_value) == json_value

def test_dict_value_operations(db_session):
    repo = ConfigRepository(db_session)
    chat_id = 789
    chat_key = 3
    
    # Update dict value (should create new record)
    repo.update_dict_value(chat_id, chat_key, "field1", "value1")
    db_session.commit()
    
    val = repo.get_dict_value(chat_id, chat_key, "field1")
    assert val == "value1"
    
    # Update another field
    repo.update_dict_value(chat_id, chat_key, "field2", "value2")
    db_session.commit()
    
    assert repo.get_dict_value(chat_id, chat_key, "field1") == "value1"
    assert repo.get_dict_value(chat_id, chat_key, "field2") == "value2"
    assert repo.get_dict_value(chat_id, chat_key, "field3", "def") == "def"

def test_kv_store(db_session):
    repo = ConfigRepository(db_session)
    key = "test_key"
    value = {"data": 123}
    
    repo.save_kv_value(key, value)
    db_session.commit()
    
    loaded = repo.load_kv_value(key)
    assert loaded == value
    
    repo.save_kv_value(key, "updated")
    db_session.commit()
    assert repo.load_kv_value(key) == "updated"

# --- ChatsRepository Tests ---

def test_update_chat_info(db_session):
    repo = ChatsRepository(db_session)
    chat_id = 1001
    
    member1 = GroupMember(user_id=1, username="user1", full_name="User One", is_admin=True)
    member2 = GroupMember(user_id=2, username="user2", full_name="User Two", is_admin=False)
    
    # Initial update
    repo.update_chat_info(chat_id, [member1, member2])
    db_session.commit()
    
    # Verify Chat created
    chat = db_session.query(Chat).filter_by(chat_id=chat_id).first()
    assert chat is not None
    assert 1 in chat.admins
    assert 2 not in chat.admins
    
    # Verify Members created
    members = db_session.query(ChatMember).filter_by(chat_id=chat_id).all()
    assert len(members) == 2
    
    # Verify BotUsers created
    users = db_session.query(BotUsers).all()
    assert len(users) == 2
    
    # Test update (member2 becomes admin, member1 leaves?)
    # update_chat_info doesn't automatically remove missing members unless clear_users=True,
    # but it updates existing.
    
    member2_updated = GroupMember(user_id=2, username="user2", full_name="User Two", is_admin=True)
    repo.update_chat_info(chat_id, [member2_updated])
    db_session.commit()
    
    chat = db_session.query(Chat).filter_by(chat_id=chat_id).first()
    # Logic in update_chat_info: 
    # if member.is_admin: admin_ids.add
    # else: admin_ids.discard
    # It starts with set(chat.admins). 
    # member1 was in admins. We didn't pass member1 in new list.
    # So member1 should still be in admins? 
    # No, usually update_chat_info is called with FULL list from API. 
    # But if we pass partial list, it only updates those in list.
    # Correct logic check:
    assert 2 in chat.admins
    assert 1 in chat.admins # Since we didn't process user 1 in second call to remove him or unset admin

def test_add_and_remove_user(db_session):
    repo = ChatsRepository(db_session)
    chat_id = 2002
    member = GroupMember(user_id=10, username="joiner", full_name="Joiner", is_admin=False)
    
    repo.add_user_to_chat(chat_id, member)
    db_session.commit()
    
    chat_member = db_session.query(ChatMember).filter_by(chat_id=chat_id, user_id=10).first()
    assert chat_member is not None
    assert chat_member.left_at is None
    
    repo.remove_user_from_chat(chat_id, 10)
    db_session.commit()
    
    chat_member = db_session.query(ChatMember).filter_by(chat_id=chat_id, user_id=10).first()
    assert chat_member.left_at is not None

def test_get_users_joined_last_day(db_session):
    repo = ChatsRepository(db_session)
    chat_id = 3003
    
    # Add user joined now
    m1 = GroupMember(user_id=100, username="u1", full_name="U1", is_admin=False)
    repo.add_user_to_chat(chat_id, m1)
    db_session.commit()
    
    # Manually simulate old user
    old_date = datetime(2020, 1, 1)
    m2 = GroupMember(user_id=101, username="u2", full_name="U2", is_admin=False)
    repo.add_user_to_chat(chat_id, m2)
    db_session.commit()
    
    # Hack to update created_at
    db_member = db_session.query(ChatMember).filter_by(user_id=101).first()
    db_member.created_at = old_date
    db_session.commit()
    
    joined = repo.get_users_joined_last_day(chat_id)
    assert len(joined) == 1
    assert joined[0].user_id == 100
