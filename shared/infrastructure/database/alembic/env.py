import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from shared.infrastructure.database.models import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# --- НАЧАЛО ИЗМЕНЕНИЙ ---
# Получаем URL из переменной окружения 'POSTGRES_URL'.
# Если переменная не установлена, используем значение из alembic.ini.
db_url = os.getenv('POSTGRES_URL', config.get_main_option("sqlalchemy.url"))

# Устанавливаем это значение как основное для Alembic
config.set_main_option('sqlalchemy.url', db_url)
# --- КОНЕЦ ИЗМЕНЕНИЙ ---

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired a number of ways:
# in the config itself, defined in setup.py entry points, etc.
# config.set_main_option('sqlalchemy.url', 'postgresql://user:password@host:port/dbname') # Example

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here send the SQL to the console with the
    above options.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
