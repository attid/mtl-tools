from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from other.config_reader import config

engine = create_engine(config.postgres_url, pool_pre_ping=True)
SessionPool = sessionmaker(bind=engine)

def create_session():
    return SessionPool()
