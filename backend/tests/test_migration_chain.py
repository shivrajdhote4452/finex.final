"""Automated PostgreSQL Disposable Database Migration Chain Verification.

Tests:
1. Completely clean empty database upgraded to head.
2. Existing database at revision 005 (6d8e21a9f023) upgraded to head with backfills.
3. Database with revision 006 already applied forward-migrated to head (007).
"""

import os
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from backend.app.config import get_settings
from sqlalchemy.ext.asyncio import create_async_engine


@pytest.fixture
def anyio_backend():
    return "asyncio"


def get_admin_and_disposable_urls(db_name: str):
    settings = get_settings()
    base_url = settings.DATABASE_URL.rsplit("/", 1)[0]
    admin_url = f"{base_url}/postgres"
    disposable_url = f"{base_url}/{db_name}"
    return admin_url, disposable_url


async def create_disposable_database(db_name: str):
    admin_url, disposable_url = get_admin_and_disposable_urls(db_name)
    engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    async with engine.connect() as conn:
        await conn.execute(sa.text(f'CREATE DATABASE "{db_name}"'))
    await engine.dispose()
    return disposable_url


async def drop_disposable_database(db_name: str):
    admin_url, _ = get_admin_and_disposable_urls(db_name)
    engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    async with engine.connect() as conn:
        # Terminate any lingering connections
        await conn.execute(
            sa.text(
                f"SELECT pg_terminate_backend(pg_stat_activity.pid) "
                f"FROM pg_stat_activity "
                f"WHERE pg_stat_activity.datname = '{db_name}' AND pid <> pg_backend_pid()"
            )
        )
        await conn.execute(sa.text(f'DROP DATABASE IF EXISTS "{db_name}"'))
    await engine.dispose()


def run_alembic_upgrade_sync(target_url: str, revision: str = "head"):
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", target_url)
    # Set environment variable so env.py picks it up
    orig_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = target_url
    try:
        command.upgrade(alembic_cfg, revision)
    finally:
        if orig_url:
            os.environ["DATABASE_URL"] = orig_url
        else:
            os.environ.pop("DATABASE_URL", None)


@pytest.mark.asyncio
async def test_migration_chain_clean_database_to_head():
    """Verify a completely clean empty database successfully upgrades to head without duplicate column errors."""
    import asyncio

    db_name = f"finex_test_clean_{uuid.uuid4().hex[:8]}"
    disposable_url = await create_disposable_database(db_name)
    try:
        # Run upgrade to head in separate thread so env.py can asyncio.run()
        await asyncio.to_thread(run_alembic_upgrade_sync, disposable_url, "head")

        # Inspect resulting schema
        engine = create_async_engine(disposable_url)
        async with engine.connect() as conn:

            def inspect_schema(sync_conn):
                inspector = sa.inspect(sync_conn)
                tables = set(inspector.get_table_names())
                assert "market_quotes" in tables
                assert "paper_proposals" in tables
                assert "securities" in tables

                mq_cols = {c["name"] for c in inspector.get_columns("market_quotes")}
                assert "symbol" in mq_cols
                assert "close_price" in mq_cols

                pp_cols = {c["name"] for c in inspector.get_columns("paper_proposals")}
                assert "requested_budget" in pp_cols
                assert "attempt_count" in pp_cols
                assert "conversation_id" in pp_cols

            await conn.run_sync(inspect_schema)
        await engine.dispose()
    finally:
        await drop_disposable_database(db_name)


@pytest.mark.asyncio
async def test_migration_chain_upgrade_from_005_with_backfills():
    """Verify an existing database at revision 005 (6d8e21a9f023) upgrades to head and accurately backfills."""
    import asyncio

    db_name = f"finex_test_upgrade_{uuid.uuid4().hex[:8]}"
    disposable_url = await create_disposable_database(db_name)
    try:
        # 1. Upgrade to revision 005
        await asyncio.to_thread(run_alembic_upgrade_sync, disposable_url, "6d8e21a9f023")

        # 2. Populate legacy data matching revision 005 schema
        engine = create_async_engine(disposable_url)
        async with engine.connect() as conn:
            # Insert user
            user_id = f"usr-legacy-{uuid.uuid4().hex[:6]}"
            now_dt = datetime.now(timezone.utc)
            await conn.execute(
                sa.text(
                    "INSERT INTO users (id, email, provider, provider_subject, is_active, created_at, updated_at) "
                    "VALUES (:id, :email, 'google', :sub, true, :now, :now)"
                ),
                {"id": user_id, "email": f"{user_id}@finex.test", "sub": user_id, "now": now_dt},
            )
            # Insert security (id is UUID)
            sec_id = str(uuid.uuid4())
            await conn.execute(
                sa.text(
                    "INSERT INTO securities (id, symbol, name, exchange, is_active, created_at, updated_at) "
                    "VALUES (:id, 'INFY', 'Infosys Ltd', 'NSE', true, :now, :now)"
                ),
                {"id": sec_id, "now": now_dt},
            )
            # Insert market_quotes (id is UUID, symbol is NULL initially)
            mq_id = str(uuid.uuid4())
            await conn.execute(
                sa.text(
                    "INSERT INTO market_quotes (id, security_id, symbol, price, previous_close, volume, source, observed_at, ingested_at, created_at) "
                    "VALUES (:id, :sec_id, NULL, 1500.50, 1500.00, 1000, 'TEST', :now, :now, :now)"
                ),
                {"id": mq_id, "sec_id": sec_id, "now": now_dt},
            )
            # Insert market_price_history (id is UUID, symbol and observed_at are NULL initially)
            mph_id = str(uuid.uuid4())
            hist_date = date(2026, 10, 15)
            await conn.execute(
                sa.text(
                    "INSERT INTO market_price_history (id, security_id, trade_date, open_price, high_price, low_price, close_price, adj_close_price, volume, source, currency, ingested_at, created_at) "
                    "VALUES (:id, :sec_id, :trade_date, 1490.0, 1510.0, 1485.0, 1500.50, 1500.50, 50000, 'TEST', 'INR', :now, :now)"
                ),
                {"id": mph_id, "sec_id": sec_id, "trade_date": hist_date, "now": now_dt},
            )
            # Insert paper account
            acct_id = f"acct-legacy-{uuid.uuid4().hex[:6]}"
            await conn.execute(
                sa.text(
                    "INSERT INTO paper_accounts (id, user_id, account_number, initial_balance, current_cash) "
                    "VALUES (:id, :uid, 'ACC-LEGACY', 100000.00, 100000.00)"
                ),
                {"id": acct_id, "uid": user_id},
            )
            # Insert paper proposal (rev 005: requested_budget and attempt_count are NULL initially)
            prop_id = f"prop-legacy-{uuid.uuid4().hex[:6]}"
            exp_time = datetime(2026, 10, 19, 12, 0, 0, tzinfo=timezone.utc)
            await conn.execute(
                sa.text(
                    "INSERT INTO paper_proposals (id, user_id, account_id, instruction_text, proposed_allocations, total_budget, status, expires_at) "
                    "VALUES (:id, :uid, :aid, 'Buy INFY', '[]'::json, 5000.00, 'PROPOSED', :exp)"
                ),
                {"id": prop_id, "uid": user_id, "aid": acct_id, "exp": exp_time},
            )
            await conn.commit()
        await engine.dispose()

        # 3. Upgrade to head
        await asyncio.to_thread(run_alembic_upgrade_sync, disposable_url, "head")

        # 4. Verify backfills
        engine2 = create_async_engine(disposable_url)
        async with engine2.connect() as conn:
            # Check market_quotes backfill
            res_mq = await conn.execute(
                sa.text("SELECT symbol, close_price, price FROM market_quotes WHERE id = :id"),
                {"id": mq_id},
            )
            row_mq = res_mq.mappings().one()
            assert row_mq["symbol"] == "INFY", "market_quotes.symbol was not backfilled from securities"
            assert Decimal(str(row_mq["close_price"])) == Decimal("1500.50"), (
                "market_quotes.close_price not backfilled from price"
            )

            # Check market_price_history backfill
            res_mph = await conn.execute(
                sa.text("SELECT symbol, interval, observed_at FROM market_price_history WHERE id = :id"),
                {"id": mph_id},
            )
            row_mph = res_mph.mappings().one()
            assert row_mph["symbol"] == "INFY", "market_price_history.symbol was not backfilled"
            assert row_mph["interval"] == "1D", "market_price_history.interval was not set to default '1D'"
            assert row_mph["observed_at"] is not None, (
                "market_price_history.observed_at was not backfilled from trade_date"
            )

            # Check paper_proposals backfill
            res_pp = await conn.execute(
                sa.text("SELECT requested_budget, total_budget, attempt_count FROM paper_proposals WHERE id = :id"),
                {"id": prop_id},
            )
            row_pp = res_pp.mappings().one()
            assert Decimal(str(row_pp["requested_budget"])) == Decimal("5000.00"), (
                "requested_budget not backfilled from total_budget"
            )
            assert row_pp["attempt_count"] == 1, "attempt_count was not backfilled to 1"

        await engine2.dispose()
    finally:
        await drop_disposable_database(db_name)


@pytest.mark.asyncio
async def test_migration_chain_upgrade_from_006_to_007():
    """Verify an existing database where revision 006 is already applied upgrades cleanly to 007."""
    import asyncio

    db_name = f"finex_test_006_{uuid.uuid4().hex[:8]}"
    disposable_url = await create_disposable_database(db_name)
    try:
        # Upgrade to revision 006
        await asyncio.to_thread(run_alembic_upgrade_sync, disposable_url, "7e9f32b0a134")

        # Upgrade to head (007)
        await asyncio.to_thread(run_alembic_upgrade_sync, disposable_url, "head")

        # Verify attempt_count exists
        engine = create_async_engine(disposable_url)
        async with engine.connect() as conn:

            def check_col(sync_conn):
                inspector = sa.inspect(sync_conn)
                cols = {c["name"] for c in inspector.get_columns("paper_proposals")}
                assert "attempt_count" in cols

            await conn.run_sync(check_col)
        await engine.dispose()
    finally:
        await drop_disposable_database(db_name)
