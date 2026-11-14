import asyncio
from logging.config import fileConfig

from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context
from backend.app.config import get_settings
from backend.app.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    settings = get_settings()
    db_url = config.get_main_option("sqlalchemy.url") or settings.DATABASE_URL
    
    from urllib.parse import urlparse
    from backend.app.database import APPROVED_SQLITE_SCHEMES, is_test_env, validate_test_database_allowlist
    if is_test_env:
        validate_test_database_allowlist(db_url)

    is_sqlite = urlparse(db_url).scheme.lower() in APPROVED_SQLITE_SCHEMES
    engine_kwargs = {}
    if is_sqlite:
        engine_kwargs["connect_args"] = {"check_same_thread": False}

    connectable = create_async_engine(db_url, **engine_kwargs)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode using AsyncIO engine."""
    asyncio.run(run_async_migrations())


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    settings = get_settings()
    url = config.get_main_option("sqlalchemy.url") or settings.DATABASE_URL
    from backend.app.database import is_test_env, validate_test_database_allowlist
    if is_test_env:
        validate_test_database_allowlist(url)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
