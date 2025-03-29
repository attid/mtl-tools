from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from other.config_reader import config

engine = create_engine(config.firebird_url, pool_pre_ping=True)
quik_pool = sessionmaker(bind=engine)