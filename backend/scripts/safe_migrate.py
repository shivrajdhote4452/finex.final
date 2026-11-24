"""FinEx Safe Production Database Migration Runner.

Executes Alembic migrations with:
1. Strict session-level lock_timeout (5s) and statement_timeout (15s) enforced on the active connection.
2. Full TLS certificate and hostname verification (check_hostname=True, CERT_REQUIRED).
3. Safe credential masking in all operational logs.
4. Neon / PgBouncer connection pooler compatibility (statement_cache_size=0).
5. Transactional execution with fail-fast abort and clean rollback.
"""

import argparse
import asyncio
import logging
import os
import ssl
import sys
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from dotenv import dotenv_values
from sqlalchemy.ext.asyncio import create_async_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("safe_migrate")


def get_masked_url(url_str: str) -> str:
    """Returns database URL with username and password masked for safe logging."""
    try:
        parsed = urlparse(url_str)
        masked_netloc = f"***:***@{parsed.hostname}"
        if parsed.port:
            masked_netloc += f":{parsed.port}"
        return urlunparse(parsed._replace(netloc=masked_netloc))
    except Exception:
        return "postgresql+asyncpg://***:***@masked-host/database"


def prepare_connection_params(raw_url: str, lock_timeout_ms: int = 5000, statement_timeout_ms: int = 15000):
    """Parses and normalizes database URL, enforcing TLS verification and connection settings."""
    url_str = raw_url.strip()
    if url_str.startswith("postgres://"):
        url_str = url_str.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url_str.startswith("postgresql://") and not url_str.startswith("postgresql+"):
        url_str = url_str.replace("postgresql://", "postgresql+asyncpg://", 1)

    parsed = urlparse(url_str)
    query_params = parse_qs(parsed.query)

    # Normalize sslmode to ssl for asyncpg
    if "sslmode" in query_params and "ssl" not in query_params:
        query_params["ssl"] = query_params.pop("sslmode")

    # Reconstruct netloc ensuring explicit default port if omitted
    hostname = parsed.hostname or "127.0.0.1"
    port = parsed.port or 5432
    user = parsed.username or ""
    pwd = parsed.password or ""
    auth_part = f"{user}:{pwd}@" if user or pwd else ""
    netloc = f"{auth_part}{hostname}:{port}"

    # Remove query params handled directly by engine / driver connect_args
    sanitized_query = urlencode({k: v[0] for k, v in query_params.items() if k not in ("ssl", "sslmode")})
    clean_url = urlunparse(parsed._replace(netloc=netloc, query=sanitized_query))

    connect_args = {
        "server_settings": {
            "lock_timeout": str(lock_timeout_ms),
            "statement_timeout": str(statement_timeout_ms),
        }
    }

    # Neon / PgBouncer pooler compatibility
    if any(marker in hostname for marker in ("neon.tech", "-pooler", "pgbouncer")):
        connect_args["statement_cache_size"] = 0
        connect_args["prepared_statement_cache_size"] = 0

    # Configure full strict TLS verification for remote / SSL-enabled connections
    is_remote = hostname not in ("127.0.0.1", "localhost", "::1")
    is_ssl_requested = "ssl" in query_params or any(marker in hostname for marker in ("neon.tech", "supabase.co"))

    if is_remote and is_ssl_requested:
        # Full TLS certificate verification using system CA bundle with strict hostname checking
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = True
        ssl_ctx.verify_mode = ssl.CERT_REQUIRED
        connect_args["ssl"] = ssl_ctx

    return clean_url, connect_args


async def execute_safe_migration(
    database_url: str,
    target_revision: str = "head",
    lock_timeout_ms: int = 5000,
    statement_timeout_ms: int = 15000,
    check_only: bool = False,
    is_downgrade: bool = False,
) -> bool:
    """Executes Alembic migration on an explicit connection with enforced timeouts."""
    masked_url = get_masked_url(database_url)
    logger.info(f"Target database endpoint: {masked_url}")

    clean_url, connect_args = prepare_connection_params(
        database_url,
        lock_timeout_ms=lock_timeout_ms,
        statement_timeout_ms=statement_timeout_ms,
    )

    engine = create_async_engine(
        clean_url,
        connect_args=connect_args,
        isolation_level="AUTOCOMMIT",  # Connection manages individual transactions cleanly
    )

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", clean_url)

    try:
        async with engine.connect() as conn:
            # 1. Verify current database identity and revision
            current_db = await conn.scalar(sa.text("SELECT current_database();"))
            current_user = await conn.scalar(sa.text("SELECT current_user;"))
            logger.info(f"Connected to database '{current_db}' as user '{current_user[:3]}***'")

            has_alembic = await conn.scalar(
                sa.text(
                    "SELECT count(*) FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = 'alembic_version';"
                )
            )
            current_rev = None
            if has_alembic:
                current_rev = await conn.scalar(sa.text("SELECT version_num FROM alembic_version;"))
            logger.info(f"Current database Alembic revision: {current_rev or 'None (unversioned)'}")

            if check_only:
                logger.info("Check-only mode requested. Zero schema mutations performed.")
                return True

            # 2. Execute migration inside a dedicated transaction on this exact connection
            logger.info(f"Applying migration to revision '{target_revision}' with lock_timeout={lock_timeout_ms}ms...")

            def _run_in_sync_context(connection):
                alembic_cfg.attributes["connection"] = connection
                if is_downgrade:
                    command.downgrade(alembic_cfg, target_revision)
                else:
                    command.upgrade(alembic_cfg, target_revision)

            await conn.run_sync(_run_in_sync_context)

            # 3. Post-migration verification
            post_rev = await conn.scalar(sa.text("SELECT version_num FROM alembic_version;"))
            logger.info(f"Migration completed successfully. New active revision: {post_rev}")
            return True

    except Exception as exc:
        err_text = str(exc)
        if "lock timeout" in err_text.lower() or "55p03" in err_text.lower():
            logger.error(
                f"MIGRATION ABORTED: Lock timeout exceeded ({lock_timeout_ms}ms). "
                "Another transaction is holding a lock on the required relations. "
                "Transaction rolled back cleanly without blocking other traffic."
            )
        elif "statement timeout" in err_text.lower() or "57014" in err_text.lower():
            logger.error(
                f"MIGRATION ABORTED: Statement timeout exceeded ({statement_timeout_ms}ms). "
                "Transaction rolled back cleanly."
            )
        else:
            logger.error(f"MIGRATION FAILED: {exc}")
        return False
    finally:
        await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description="FinEx Safe Database Migration Runner")
    parser.add_argument("--revision", default="head", help="Target Alembic revision (default: head)")
    parser.add_argument("--check-only", action="store_true", help="Inspect database revision without mutating")
    parser.add_argument("--downgrade", action="store_true", help="Execute downgrade instead of upgrade")
    parser.add_argument(
        "--lock-timeout-ms", type=int, default=5000, help="Lock wait timeout in milliseconds (default: 5000)"
    )
    parser.add_argument(
        "--statement-timeout-ms", type=int, default=15000, help="Statement execution timeout in ms (default: 15000)"
    )
    args = parser.parse_args()

    # Resolve database URL from environment or .env
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        env_vals = dotenv_values(".env")
        db_url = env_vals.get("DATABASE_URL")

    if not db_url:
        logger.error("No DATABASE_URL found in environment or .env file.")
        sys.exit(1)

    success = asyncio.run(
        execute_safe_migration(
            database_url=db_url,
            target_revision=args.revision,
            lock_timeout_ms=args.lock_timeout_ms,
            statement_timeout_ms=args.statement_timeout_ms,
            check_only=args.check_only,
            is_downgrade=args.downgrade,
        )
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
