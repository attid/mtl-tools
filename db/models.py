from datetime import datetime
from sqlalchemy import String, func, SmallInteger, Float, ForeignKey, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, BigInteger, DateTime
from sqlalchemy.orm import relationship

Base = declarative_base()
metadata = Base.metadata


class BotTable(Base):
    __tablename__ = 'BOT_TABLE'
    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger)
    chat_key = Column(BigInteger)
    chat_value = Column(String(8000))


class BotUsers(Base):
    __tablename__ = 'BOT_USERS'
    user_id = Column(BigInteger, primary_key=True)
    user_name = Column(String(60))
    user_type = Column(SmallInteger, default=0)


class BotUserChats(Base):
    __tablename__ = 'BOT_USER_CHATS'
    user_id = Column(BigInteger, primary_key=True)
    chat_id = Column(BigInteger, primary_key=True)
    dt_last = Column(DateTime, default=datetime.now)


class TMessage(Base):
    __tablename__ = 'T_MESSAGE'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger)
    topic_id = Column(BigInteger, default=0)
    text = Column(String(4000))
    was_send = Column(Integer, default=0)
    dt_add = Column(DateTime, default=datetime.now)
    use_alarm = Column(Integer, default=0)
    update_id = Column(BigInteger, default=0)
    button_json = Column(String(4000))


class TDivList(Base):
    __tablename__ = 'T_DIV_LIST'
    id = Column(Integer, primary_key=True, autoincrement=True)
    dt_pay = Column(DateTime, default=func.current_timestamp(), nullable=False)
    memo = Column(String(60))
    pay_type = Column(SmallInteger, default=0, nullable=False)  # 0 - div, 1 - bod 4 - sats 5 - usdm

    transactions = relationship("TTransaction", back_populates="div_list")


class TLedgers(Base):
    __tablename__ = 'T_LEDGERS'
    ledger = Column(BigInteger, primary_key=True)

    def __init__(self, ledger_value):
        self.ledger = ledger_value


class TOperations(Base):
    __tablename__ = 'T_OPERATIONS'
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
    ledger = Column(Integer)



class TPayments(Base):
    __tablename__ = 'T_PAYMENTS'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_key = Column(String(60))
    mtl_sum = Column(Float)
    user_calc = Column(Float)
    user_div = Column(Float)
    id_div_list = Column(Integer, ForeignKey('T_DIV_LIST.id'))
    was_packed = Column(SmallInteger, default=0, nullable=False)


class TWatchList(Base):
    __tablename__ = 'T_WATCH_LIST'
    account = Column(String(64), primary_key=True)


class TTransaction(Base):
    __tablename__ = 'T_TRANSACTION'
    id = Column(Integer, primary_key=True)
    id_div_list = Column(Integer, ForeignKey('T_DIV_LIST.id'))
    xdr_id = Column(BigInteger)
    xdr = Column(Text)
    was_send = Column(Boolean, default=False)

    div_list = relationship("TDivList", back_populates="transactions")


class MyMtlWalletBot(Base):
    __tablename__ = 'MYMTLWALLETBOT'

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
    balances = Column(Text)  # Now using Text for the balances field
    balances_event_id = Column(String(32), default='0')


class MyMtlWalletBotLog(Base):
    __tablename__ = 'MYMTLWALLETBOT_LOG'

    log_id = Column('LOG_ID', Integer, primary_key=True)
    user_id = Column('USER_ID', BigInteger)
    log_dt = Column('LOG_DT', DateTime)
    log_operation = Column('LOG_OPERATION', String(32))
    log_operation_info = Column('LOG_OPERATION_INFO', String(32))


class TSummary(Base):
    __tablename__ = 'T_SUMMARY'
    id = Column(Integer, primary_key=True)
    text = Column(String(4000))
    summary_id = Column(Integer, ForeignKey('T_SUMMARY.id'))
    summary = relationship("TSummary", remote_side=[id])
    messages = relationship("TSavedMessages", back_populates="summary")


class TSavedMessages(Base):
    __tablename__ = 'T_SAVED_MESSAGES'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger)
    username = Column(String(60))
    chat_id = Column(BigInteger)
    thread_id = Column(Integer)
    text = Column(String(4000))
    dt = Column(DateTime, default=func.now())
    summary_id = Column(Integer, ForeignKey('T_SUMMARY.id'))
    summary = relationship("TSummary", back_populates="messages")


# def update_db():
#    Base.metadata.create_all(bind=engine)
#    employee = session.query(Employee).filter(Employee.first_name == first_name, Employee.last_name == last_name).one()
#    #metadata.create_all(engine)


if __name__ == "__main__":
    pass
