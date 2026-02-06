from sqlalchemy import Column, Integer, BigInteger, String, DateTime, SmallInteger, Float, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

# Define a JSON type that uses JSONB on PostgreSQL and generic JSON (TEXT) on SQLite/others
JSON_VARIANT = JSON().with_variant(JSONB, "postgresql")

# --- Firebird-derived models (adapted for PostgreSQL) ---

class BotTable(Base):
    __tablename__ = 'bot_table'
    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger)
    chat_key = Column(BigInteger)
    chat_value = Column(Text) # Changed from String(8000) to Text for PostgreSQL

class BotUsers(Base):
    __tablename__ = 'bot_users'
    user_id = Column(BigInteger, primary_key=True)
    user_name = Column(String(60))
    user_type = Column(SmallInteger, default=0)

class BotUserChats(Base):
    __tablename__ = 'bot_user_chats'
    user_id = Column(BigInteger, primary_key=True)
    chat_id = Column(BigInteger, primary_key=True)
    dt_last = Column(DateTime, default=datetime.now)

class TMessage(Base):
    __tablename__ = 't_message'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger)
    topic_id = Column(BigInteger, default=0)
    text = Column(Text) # Changed from String(4000) to Text
    was_send = Column(Integer, default=0)
    dt_add = Column(DateTime, default=datetime.now)
    use_alarm = Column(Integer, default=0)
    update_id = Column(BigInteger, default=0)
    button_json = Column(Text) # Changed from String(4000) to Text

class TDivList(Base):
    __tablename__ = 't_div_list'
    id = Column(Integer, primary_key=True, autoincrement=True)
    dt_pay = Column(DateTime, default=datetime.now, nullable=False) # func.current_timestamp() -> datetime.now
    memo = Column(String(60))
    pay_type = Column(SmallInteger, default=0, nullable=False)

    transactions = relationship("TTransaction", back_populates="div_list")

class TLedgers(Base):
    __tablename__ = 't_ledgers'
    ledger = Column(BigInteger, primary_key=True)

class TOperations(Base):
    __tablename__ = 't_operations'
    id = Column(String(32), primary_key=True)
    dt = Column(DateTime)
    operation = Column(String(32))
    amount1 = Column(String(32))
    code1 = Column(String(64))
    amount2 = Column(String(32))
    code2 = Column(String(64))
    from_account = Column(String(64))
    for_account = Column(String(64))
    memo = Column(String(64))
    transaction_hash = Column(String(64))
    ledger = Column(BigInteger) # Changed from Integer to BigInteger

class TPayments(Base):
    __tablename__ = 't_payments'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_key = Column(String(60))
    mtl_sum = Column(Float)
    user_calc = Column(Float)
    user_div = Column(Float)
    id_div_list = Column(Integer, ForeignKey('t_div_list.id'))
    was_packed = Column(SmallInteger, default=0, nullable=False)

class TWatchList(Base):
    __tablename__ = 't_watch_list'
    account = Column(String(64), primary_key=True)

class TTransaction(Base):
    __tablename__ = 't_transaction'
    id = Column(Integer, primary_key=True)
    id_div_list = Column(Integer, ForeignKey('t_div_list.id'))
    xdr_id = Column(BigInteger)
    xdr = Column(Text)
    was_send = Column(SmallInteger, default=0)

    div_list = relationship("TDivList", back_populates="transactions")

class MyMtlWalletBot(Base):
    __tablename__ = 'mymtlwalletbot'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    public_key = Column(String(60))
    secret_key = Column(String(160))
    credit = Column(Integer)
    last_use_day = Column(DateTime)
    use_pin = Column(SmallInteger, default=0)
    free_wallet = Column(SmallInteger, default=1)
    default_wallet = Column(SmallInteger, default=0)
    need_delete = Column(SmallInteger, default=0)
    last_event_id = Column(String(32), default='0')
    balances = Column(Text)
    balances_event_id = Column(String(32), default='0')

class TSummary(Base):
    __tablename__ = 't_summary'
    id = Column(Integer, primary_key=True)
    text = Column(Text) # Changed from String(4000) to Text
    summary_id = Column(Integer, ForeignKey('t_summary.id'))
    summary = relationship("TSummary", remote_side=[id])
    messages = relationship("TSavedMessages", back_populates="summary")

class TSavedMessages(Base):
    __tablename__ = 't_saved_messages'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger)
    username = Column(String(60))
    chat_id = Column(BigInteger)
    thread_id = Column(BigInteger)
    text = Column(Text) # Changed from String(4000) to Text
    dt = Column(DateTime, default=datetime.now)
    summary_id = Column(Integer, ForeignKey('t_summary.id'))
    summary = relationship("TSummary", back_populates="messages")

# --- MongoDB-derived models (hybrid for PostgreSQL) ---

class KVStore(Base):
    __tablename__ = 'kv_store'
    kv_key = Column(String, primary_key=True)
    kv_value = Column(JSON_VARIANT)

class BotConfig(Base):
    __tablename__ = 'bot_config'
    chat_id = Column(BigInteger, primary_key=True)
    chat_key = Column(BigInteger, primary_key=True)
    chat_key_name = Column(String)
    chat_value = Column(JSON_VARIANT) # Using JSONB variant for flexibility

class Chat(Base):
    __tablename__ = 'chats'
    chat_id = Column(BigInteger, primary_key=True)
    username = Column(String)
    title = Column(String)
    created_at = Column(DateTime)
    last_updated = Column(DateTime)
    admins = Column(ARRAY(BigInteger))
    metadata_ = Column('metadata', JSON_VARIANT) # Using metadata_ to avoid Python keyword conflict

    members = relationship("ChatMember", back_populates="chat")

class ChatMember(Base):
    __tablename__ = 'chat_members'
    chat_id = Column(BigInteger, ForeignKey('chats.chat_id'), primary_key=True)
    user_id = Column(BigInteger, ForeignKey('bot_users.user_id'), primary_key=True) # FK to bot_users
    created_at = Column(DateTime)
    left_at = Column(DateTime)
    metadata_ = Column('metadata', JSON_VARIANT) # For any other user-specific chat metadata

    chat = relationship("Chat", back_populates="members")
    user = relationship("BotUsers") # Relationship to the BotUsers table