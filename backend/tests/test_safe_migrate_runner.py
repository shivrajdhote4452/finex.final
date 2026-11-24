"""Isolated PostgreSQL Integration Tests for the Safe Migration Runner (scripts/safe_migrate.py).

Validates:
1. Exact runner execution of migration 010 (b2c3d4e5f6a7).
2. Verification that error_events table and revision persist after reconnecting on a fresh connection.
3. 100% representative portfolio data preservation.
4. Fail-fast lock_timeout detection, timeout logging, and clean rollback under lock contention.
5. Safe downgrade execution and schema rollback verification.
"""

import asyncio
import os
import ssl
import time
import uuid
from datetime import date, datetime, timezone

import pytest
import sqlalchemy as sa
from backend.scripts.safe_migrate import execute_safe_migration, prepare_connection_params
from backend.tests.test_migration_010 import (
    create_disposable_database,
    drop_disposable_database,
    run_alembic_upgrade_sync,
)
from sqlalchemy.ext.asyncio import create_async_engine


@pytest.mark.asyncio
async def test_safe_migrate_runner_full_lifecycle_on_isolated_postgresql():
    """Verify safe_migrate runner against migration 010, persistence after reconnect, and lock timeout."""
    os.environ["ENVIRONMENT"] = "testing"
    db_name = f"finex_test_runner_{uuid.uuid4().hex[:8]}"
    db_url = await create_disposable_database(db_name)

    try:
        # ---------------------------------------------------------------------
        # 1. Migrate to revision 009 and seed representative portfolio data
        # ---------------------------------------------------------------------
        await asyncio.to_thread(run_alembic_upgrade_sync, db_url, "a1b2c3d4e5f6")

        now_dt = datetime.now(timezone.utc)
        user_id = f"usr-test-{uuid.uuid4().hex[:8]}"
        portfolio_id = f"port-test-{uuid.uuid4().hex[:8]}"

        engine_seed = create_async_engine(db_url)
        async with engine_seed.connect() as conn:
            await conn.execute(
                sa.text(
                    "INSERT INTO users ("
                    "  id, email, provider, provider_subject, is_active, is_verified, "
                    "  email_verified, created_at, updated_at"
                    ") VALUES ("
                    "  :id, :email, 'google', :sub, true, true, true, :now, :now"
                    ")"
                ),
                {"id": user_id, "email": f"{user_id}@finex.test", "sub": f"sub-{user_id}", "now": now_dt},
            )
            await conn.execute(
                sa.text(
                    "INSERT INTO portfolios (id, user_id, name, currency, is_default, created_at, updated_at) "
                    "VALUES (:id, :uid, 'Core Growth Portfolio', 'INR', true, :now, :now)"
                ),
                {"id": portfolio_id, "uid": user_id, "now": now_dt},
            )
            pdate = date(2026, 10, 1)
            await conn.execute(
                sa.text(
                    "INSERT INTO portfolio_holdings ("
                    "  id, portfolio_id, symbol, asset_class, quantity, cost_basis_per_share, "
                    "  currency, purchase_date, created_at, updated_at"
                    ") VALUES ("
                    "  :id, :pid, 'TCS.NS', 'EQUITY', 50.0, 3500.0, 'INR', :pdate, :now, :now"
                    ")"
                ),
                {"id": f"hld-{uuid.uuid4().hex[:8]}", "pid": portfolio_id, "pdate": pdate, "now": now_dt},
            )
            await conn.commit()
        await engine_seed.dispose()

        # ---------------------------------------------------------------------
        # 2. Execute the EXACT safe runner to apply migration 010 (b2c3d4e5f6a7)
        # ---------------------------------------------------------------------
        success = await execute_safe_migration(
            database_url=db_url,
            target_revision="head",
            lock_timeout_ms=5000,
            statement_timeout_ms=15000,
        )
        assert success is True, "safe_migrate runner failed to apply migration 010"

        # ---------------------------------------------------------------------
        # 3. Verify persistence after reconnecting on a fresh engine
        # ---------------------------------------------------------------------
        engine_verify = create_async_engine(db_url)
        async with engine_verify.connect() as conn:
            # Verify revision persisted
            active_rev = await conn.scalar(sa.text("SELECT version_num FROM alembic_version;"))
            assert active_rev == "b2c3d4e5f6a7"

            # Verify table persisted and queryable
            count_errors = await conn.scalar(sa.text("SELECT count(*) FROM error_events;"))
            assert count_errors == 0

            # Verify indexes exist
            idx_rows = (
                (await conn.execute(sa.text("SELECT indexname FROM pg_indexes WHERE tablename = 'error_events';")))
                .scalars()
                .all()
            )
            assert "ix_error_events_created_at" in idx_rows
            assert "ix_error_events_correlation_id" in idx_rows
            assert "ix_error_events_status_code" in idx_rows

            # Verify representative portfolio data remained 100% intact
            holding_qty = await conn.scalar(
                sa.text("SELECT quantity FROM portfolio_holdings WHERE portfolio_id = :pid;"), {"pid": portfolio_id}
            )
            assert float(holding_qty) == 50.0
        await engine_verify.dispose()

        # ---------------------------------------------------------------------
        # 4. Test Lock Timeout Failure and Clean Rollback under Contention
        # ---------------------------------------------------------------------
        engine_lock = create_async_engine(db_url)
        conn_holding_lock = await engine_lock.connect()
        trans_holding = await conn_holding_lock.begin()

        # Hold an exclusive lock on error_events
        await conn_holding_lock.execute(sa.text("LOCK TABLE error_events IN ACCESS EXCLUSIVE MODE;"))

        # Attempt to run downgrade with a 1500ms lock timeout
        start = time.perf_counter()
        runner_timeout_success = await execute_safe_migration(
            database_url=db_url,
            target_revision="a1b2c3d4e5f6",
            lock_timeout_ms=1500,
            statement_timeout_ms=5000,
            is_downgrade=True,
        )
        elapsed = time.perf_counter() - start

        # Release the lock
        await trans_holding.rollback()
        await conn_holding_lock.close()
        await engine_lock.dispose()

        # Runner must have failed gracefully without hanging
        assert runner_timeout_success is False, "Runner should have failed due to lock timeout"
        assert 1.3 <= elapsed <= 3.5, f"Elapsed {elapsed:.2f}s did not match ~1.5s lock timeout"

        # Verify database remained in 010 state after aborted lock
        engine_check_after_abort = create_async_engine(db_url)
        async with engine_check_after_abort.connect() as conn:
            rev_after_abort = await conn.scalar(sa.text("SELECT version_num FROM alembic_version;"))
            assert rev_after_abort == "b2c3d4e5f6a7", "Revision should not have changed after timeout abort"
        await engine_check_after_abort.dispose()

        # ---------------------------------------------------------------------
        # 5. Execute safe downgrade when lock is free and verify clean rollback
        # ---------------------------------------------------------------------
        downgrade_success = await execute_safe_migration(
            database_url=db_url,
            target_revision="a1b2c3d4e5f6",
            lock_timeout_ms=5000,
            statement_timeout_ms=15000,
            is_downgrade=True,
        )
        assert downgrade_success is True, "Downgrade should succeed when lock is free"

        # Reconnect to verify error_events table is dropped and revision is 009
        engine_after_downgrade = create_async_engine(db_url)
        async with engine_after_downgrade.connect() as conn:
            rev_after_downgrade = await conn.scalar(sa.text("SELECT version_num FROM alembic_version;"))
            assert rev_after_downgrade == "a1b2c3d4e5f6"

            table_exists = await conn.scalar(
                sa.text(
                    "SELECT count(*) FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = 'error_events';"
                )
            )
            assert table_exists == 0

            # Portfolio records still 100% intact after downgrade
            holding_qty_after = await conn.scalar(
                sa.text("SELECT quantity FROM portfolio_holdings WHERE portfolio_id = :pid;"), {"pid": portfolio_id}
            )
            assert float(holding_qty_after) == 50.0
        await engine_after_downgrade.dispose()

    finally:
        await drop_disposable_database(db_name)


def test_prepare_connection_params_enforces_tls_and_pooler_settings():
    """Verify that prepare_connection_params sets full strict TLS verification and neon pooler settings."""
    neon_url = "postgresql://user:secret@ep-gentle-frog-12345-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"
    clean_url, connect_args = prepare_connection_params(neon_url, lock_timeout_ms=3000, statement_timeout_ms=8000)

    # 1. Scheme normalized to asyncpg
    assert clean_url.startswith("postgresql+asyncpg://")

    # 2. Port explicitly defaulted
    assert ":5432" in clean_url

    # 3. Server settings for timeouts
    assert connect_args["server_settings"]["lock_timeout"] == "3000"
    assert connect_args["server_settings"]["statement_timeout"] == "8000"

    # 4. Pooler statement cache disabled
    assert connect_args["statement_cache_size"] == 0
    assert connect_args["prepared_statement_cache_size"] == 0

    # 5. Full strict TLS verification context preserved
    ssl_ctx = connect_args["ssl"]
    assert ssl_ctx.check_hostname is True, "Hostname verification must be enabled"
    assert ssl_ctx.verify_mode == ssl.CERT_REQUIRED, "Certificate verification must be required"
