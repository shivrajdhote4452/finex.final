# FinEx Defect Repair & Verification Acceptance Matrix

**Repository:** `https://github.com/shivrajdhote4452/finex.final.git`  
**Base Commit:** `3ff3f9285b27913d444ff37afd770c7b88a204f7`  
**Repair Branch:** `fix/schema-flutter-realdata-repairs`  
**Author / Owner:** Shivraj Dhote  
**Date of Audit & Repair:** 18 October 2026  

---

## 1. Executive Summary & Verification Claims

All six defect packages were repaired on branch `fix/schema-flutter-realdata-repairs` with zero regressions:
1. **Schema Compatibility and Database Initialization**: Fully reconciled Alembic migrations (`001`, `002`, `003`, and forward repair `004`), standalone SQL (`data/init_finex_db.sql`), and SQLAlchemy ORM metadata (`Base.metadata`). Both fresh installations (PostgreSQL and SQLite) and forward migration from earlier versions pass cleanly with zero unexplained column mismatches.
2. **Real Flutter Google Sign-In**: Native Google Sign-In integration implemented using `google_sign_in: ^6.2.1` and `flutter_secure_storage: ^9.2.2`. Removed compile-time static tokens, implemented dynamic ID token submission to backend, persisted session tokens in secure storage, restored session on app start, restricted dev sandbox login to `kDebugMode`, and implemented the 4-question risk onboarding survey UI.
3. **Real Market Data & Document Ingestion**: Disabled synthetic fixture fallback by default (`MARKET_ALLOW_FIXTURES: bool = False`), wired settings to routers, ensured simulated source outages return `503 Service Unavailable` with `data_status="unavailable"` rather than invented static prices, integrated real NSE/Yahoo Finance public v8 fetching with SHA-256 evidence hashing, and ingested official regulatory documents with chunk extraction and strict `INSUFFICIENT_EVIDENCE` fallback.
4. **Persistence of Previews & Remaining User Records**: Added `TransactionPreview` ORM model, database tables, and dual-phase persistence (`preview_csv_db` and `commit_csv_db`) to withstand backend process restarts and multi-worker concurrent commits with row-level transaction safety. Watchlists, smart alerts, notifications, and AI chat sessions were wired directly to PostgreSQL database models.
5. **Server-Owned Risk Questionnaire Weights**: Replaced client-supplied scores with strict server-side catalog evaluation in `backend/app/domain/risk.py`. Enforces questionnaire version, question IDs, option IDs, and time horizon validation. Flutter UI submits selected option IDs without client score fabrication.
6. **CI, SQLite Compatibility & Validation Claims**: Replaced PostgreSQL-specific `func.to_char` with portable year-month date boundary filtering in spending analysis, isolated environment settings in `test_config.py`, registered the `@pytest.mark.live` marker, and verified that all 120 integration/domain tests pass (119 offline + 1 live).

---

## 2. Acceptance Matrix

| ID | Defect & Root Cause | Changed Files | Test / Verification Method | Command & Environment | Actual Result | Status |
|---|---|---|---|---|---|---|
| **PKG-01** | Missing columns (`paper_accounts.status`, `paper_accounts.account_number`, `goal_contributions.user_id`) in initial migration; `revoked_tokens` column mismatch (`jti`/`expires_at` vs `token`/`revoked_at`); missing `paper_trades` in standalone SQL; SQLite batch alter crash on unique constraints. | `alembic/versions/2146f33543d1_001_initial_schema.py`<br>`alembic/versions/3a5e12f9b8c4_002_receipt_and_uniqueness.py`<br>`alembic/versions/5c7e81d9f012_004_schema_compatibility.py`<br>`data/init_finex_db.sql`<br>`backend/app/models/paper_trading.py` | Standalone schema validation script, forward upgrade script, SQLite and PostgreSQL migration suite. | `alembic upgrade head`<br>`pytest backend/tests/test_paper_trading_api.py`<br>`pytest backend/tests/test_ch_acceptance_matrix.py` | Fresh PostgreSQL migrates to head (`004`). SQLite migration executes with `batch_alter_table`. Zero schema mismatches against `Base.metadata`. | **Verified** |
| **PKG-02** | Flutter Google Sign-In used compile-time static `GOOGLE_ID_TOKEN` instead of native OAuth flow; tokens were stored only in ephemeral memory; dev login button was accessible unconditionally. | `mobile/pubspec.yaml`<br>`mobile/lib/screens/auth_screen.dart`<br>`mobile/lib/services/api_client.dart`<br>`mobile/lib/main.dart`<br>`mobile/ios/Runner/Info.plist`<br>`mobile/test/widget_test.dart` | `flutter analyze` static analysis and Flutter widget test suite. | `flutter analyze`<br>`flutter test` in `mobile/` | `flutter analyze`: No issues found (0 warnings). `flutter test`: 2/2 tests passed with mock secure storage and OAuth redirect schemes. | **Verified (Code & Tests)**<br>*(Live device OAuth blocked by lack of physical device / active Google client credentials)* |
| **PKG-03** | `RealMarketDataProvider` defaulted `allow_fixture_fallback=True`, serving static `nse_official_baseline_snapshot` prices during outages; config variable `MARKET_ALLOW_FIXTURES` was not wired to routers. | `backend/app/config.py`<br>`backend/app/adapters/market_data_provider.py`<br>`backend/app/routers/market.py`<br>`backend/tests/test_live_ingestion_and_rag_grounding.py` | Live ingestion test with SHA-256 payload hashing; simulated provider outage test asserting 503 unavailable; RAG ungrounded query test asserting `INSUFFICIENT_EVIDENCE`. | `pytest backend/tests/test_live_ingestion_and_rag_grounding.py -v` | Live RELIANCE quote ingested from external API with SHA-256 hash. Outage test confirmed 503 with `data_status="unavailable"`. Ungrounded question returned `INSUFFICIENT_EVIDENCE`. All 4 tests passed. | **Verified** |
| **PKG-04** | Uncommitted CSV upload previews were stored exclusively in memory (`_PREVIEWS_STORE`), causing HTTP 404 upon backend restart and failing multi-worker commit operations. Watchlists, alerts, and chat lacked DB persistence. | `backend/app/models/spending.py`<br>`backend/app/domain/spending_service.py`<br>`backend/app/routers/watchlists.py`<br>`backend/app/routers/alerts.py`<br>`backend/app/routers/ai_chat.py`<br>`backend/tests/test_restart_persistence_and_isolation.py` | Restart survival test: write preview, re-instantiate storage/app, commit preview; concurrent `asyncio.gather` commit collision test; multi-tenant isolation. | `pytest backend/tests/test_restart_persistence_and_isolation.py -v` | All 8 restart/isolation tests passed. Uncommitted preview committed after simulated process restart; concurrent duplicate commits created exactly 1 set of transactions with duplicate suppression. | **Verified** |
| **PKG-05** | Risk questionnaire endpoint accepted client-submitted question/option scores, allowing a user to manipulate their score to `AGGRESSIVE` while selecting `CONSERVATIVE` answers. Flutter UI used hardcoded answers. | `backend/app/domain/risk.py`<br>`backend/app/routers/risk.py`<br>`mobile/lib/screens/auth_screen.dart` | Tampered-score test (client score ignored, derived strictly from server catalog); question ID and option ID validation; full 4-question interactive Flutter survey widget. | `pytest backend/tests/test_goals_and_spending_api.py -v` | Submitting mismatched scores does not alter outcome; invalid options/questions rejected with 422; score calculated strictly from server weights. | **Verified** |
| **PKG-06** | CI failure due to inherited `ENVIRONMENT=testing` in `test_config.py`; SQLite failure on PostgreSQL-specific `func.to_char`; unregistered `@pytest.mark.live` marker; load test cold-start latency spike. | `backend/app/domain/spending_service.py`<br>`backend/tests/test_config.py`<br>`pyproject.toml`<br>`backend/pyproject.toml`<br>`backend/scripts/run_load_test.py` | Settings isolation via `monkeypatch.delenv`; portable year-month date range parsing; full test suite run; load test benchmark. | `pytest backend/tests/test_config.py`<br>`pytest backend/tests/ -v -m "not live"`<br>`pytest backend/tests/test_api_load_and_reliability.py` | All 119 non-live tests + 1 live test passed. Load benchmark passed SLA with 100% success rate and p95 < 500ms. `ruff check .` passed with 0 errors. React build passed. | **Verified** |

---

## 3. Test Suite & Verification Results

### 3.1 Backend Test Matrix (pytest)
```bash
$env:PYTHONPATH="."; .\.venv\Scripts\pytest.exe backend/tests/ -v -m "not live"
======================= 119 passed, 1 deselected, 25 warnings in 27.51s =======================

$env:PYTHONPATH="."; .\.venv\Scripts\pytest.exe backend/tests/test_live_ingestion_and_rag_grounding.py -v -m "live"
======================= 1 passed, 3 deselected in 0.99s =======================
```
**Total Backend Tests:** 120 / 120 Passing (100% Pass Rate).

### 3.2 Mobile Analysis & Tests (Flutter)
```bash
flutter analyze
Analyzing mobile...
No issues found! (ran in 6.5s)

flutter test
00:01 +2: All tests passed!
```

### 3.3 Web Frontend Production Build (React / Vite)
```bash
npm run build
> tsc -b && vite build
✓ 47 modules transformed.
dist/index.html                   0.96 kB
dist/assets/index-Ce5OVtMb.css    6.90 kB
dist/assets/index-Bxfg4wLD.js   317.60 kB
✓ built in 1.19s
```

### 3.4 Code Quality & Linting (Ruff)
```bash
.\.venv\Scripts\ruff.exe check .
All checks passed!
```

---

## 4. Platform & Environment Breakdown

1. **PostgreSQL (Local / Production)**:
   - Live PostgreSQL database running at `localhost:5432/finex_db` verified at revision `5c7e81d9f012` (`004_schema_compatibility`).
   - All tables and columns match `Base.metadata` with zero missing columns or discrepancies.
2. **SQLite (Development / Testing)**:
   - Verified with `batch_alter_table` in migrations for unique constraints.
   - Replaced PostgreSQL `func.to_char(Transaction.booking_date, 'YYYY-MM')` with portable datetime bounds (`start_of_month <= booking_date < start_of_next_month`), ensuring identical query execution across both database engines.
3. **Flutter Platforms**:
   - iOS: Configured `CFBundleURLTypes` for Google Sign-In redirect schemes in `Info.plist`.
   - Android: Secure storage and Google Sign-In plugins registered.
   - Tested: Headless unit/widget test runner passed with mock secure storage and OAuth flows.
   - *Note on Device Testing:* Physical device launch and real Google cloud credentials require deployment to user hardware or active Google Cloud OAuth client keys.
4. **External Integrations**:
   - Ingested live external quote for `RELIANCE` from Yahoo Finance public v8 with SHA-256 evidence hashing.
   - Outage failover confirmed: returning HTTP 503 with explicit `unavailable` status when external sources fail, without fallback to fake baseline prices.

---

## 5. Next Steps for Deployment

1. Review git diff on branch `fix/schema-flutter-realdata-repairs`.
2. To apply forward migration to any staging or production PostgreSQL database, execute:
   ```bash
   alembic upgrade head
   ```
3. To supply real production Google OAuth client credentials for Android/iOS, configure `google-services.json` (Android) and `GoogleService-Info.plist` (iOS) in the `mobile/` directory.
