# FinEx — Financial Excellence Platform

**Developer & Owner:** Shivraj Dhote (`shivraj.dhote@finex.internal`)  
**Design System:** Graphite Terminal — Pure Black (`#000000`), Orange Actions (`#F29A60`), Semantic Green/Red status  
**Target Handoff:** 10 November 2026  
**Repository:** [github.com/shivrajdhote4452/finex.final](https://github.com/shivrajdhote4452/finex.final.git)

---

## 1. Architectural Overview

FinEx is an educational financial intelligence platform engineered with strict deterministic domain calculations and real-data provenance:
- **Web Terminal (Primary Production Interface):** React 18, TypeScript, Vite (`localhost:3000`), Lightweight Charts candlestick engine, Trade Time Machine, and custom Graphite design tokens.
- **Backend Core:** FastAPI (`127.0.0.1:8000`), Pydantic v2, SQLAlchemy 2.0 (AsyncIO), PyJWT, and official `google-auth`.
- **Data & Analytics:** PostgreSQL operational transactional database with Alembic migrations; deterministic local Python runners for compliance and retention. (Remote Databricks compute deferred to post-demo per ADR-007).
- **Mobile Architecture:** Flutter 3 client codebase (`mobile/`). (Native store packaging deferred to post-demo per ADR-006).
- **AI & RAG:** Grounded deterministic evaluation engine with traceable citations (SEBI, RBI, NSE regulatory publications).

---

## 📱 Mobile App Downloads (Android APK)

The FinEx mobile app is built with Flutter and natively connected to the live Render backend (`https://finex-final.onrender.com/api/v1`) with live Angel One SmartAPI quotes and Google OAuth.

Download the latest verified release builds directly to your Android device:

| Architecture | APK File | Size | Recommended For | Direct Download Link |
| :--- | :--- | :--- | :--- | :--- |
| **ARM 64-bit (Recommended)** | `app-arm64-v8a-release.apk` | **18.3 MB** | **All Modern Android Phones** (Samsung, OnePlus, Xiaomi, Realme, Vivo, Pixel, etc.) | 📲 [**Download arm64 (18.3 MB)**](https://github.com/shivrajdhote4452/finex.final/releases/download/v1.0.0-android/app-arm64-v8a-release.apk) |
| **ARM 32-bit** | `app-armeabi-v7a-release.apk` | **15.9 MB** | Older 32-bit Android phones | 📲 [**Download armeabi (15.9 MB)**](https://github.com/shivrajdhote4452/finex.final/releases/download/v1.0.0-android/app-armeabi-v7a-release.apk) |
| **x86_64** | `app-x86_64-release.apk` | **19.7 MB** | PC Android Emulators & Chromebooks | 📲 [**Download x86_64 (19.7 MB)**](https://github.com/shivrajdhote4452/finex.final/releases/download/v1.0.0-android/app-x86_64-release.apk) |
| **Universal (All-in-One)** | `app-release.apk` | **52.2 MB** | Universal multi-architecture installer | 📲 [**Download Universal (52.2 MB)**](https://github.com/shivrajdhote4452/finex.final/releases/download/v1.0.0-android/app-release.apk) |

👉 **[View Full Release Details on GitHub](https://github.com/shivrajdhote4452/finex.final/releases/tag/v1.0.0-android)**

> **Installation Tip:** For almost all modern Android phones, download the **ARM 64-bit (`18.3 MB`)** version. Tap the downloaded APK to install (enable "Install from unknown sources" if prompted) and sign in with your verified Google account.

---

## 2. Quickstart & Local Setup

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- PostgreSQL 16+

### Environment Configuration
Copy the template configuration:
```powershell
cp .env.example .env
```
Ensure `JWT_SECRET_KEY` is configured (minimum 32 characters in production).

### Backend Setup (FastAPI)
```powershell
# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install exact pinned dependencies (lockfile guarantees reproducible installs)
python -m pip install -r backend/requirements.lock
# (Alternatively, for unpinned development ranges: python -m pip install -r backend/requirements.txt)
python -m pip check

# Start live backend server (hot-reload enabled)
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
Interactive API Documentation and System Health Probes will be immediately accessible at:
- **Process Liveness Probe:** `http://127.0.0.1:8000/api/v1/health/live`
- **Dependency Readiness Probe:** `http://127.0.0.1:8000/api/v1/health/ready`
- **Swagger UI:** `http://127.0.0.1:8000/api/v1/docs` (or auto-redirect from `http://127.0.0.1:8000/` and `/docs`)
- **ReDoc UI:** `http://127.0.0.1:8000/api/v1/redoc`
- **OpenAPI Schema:** `http://127.0.0.1:8000/api/v1/openapi.json`

### Web Frontend Setup (React)
```powershell
cd web
npm install
npm run dev
```
Accessible at `http://localhost:3000`.

---

### Database Initialization & Migrations (PostgreSQL / SQLite)
FinEx uses Alembic migrations decoupled from mutable application metadata:
```powershell
# Run all forward migrations to latest head revision (007)
python -m alembic upgrade head

# Inspect raw SQL without applying:
python -m alembic upgrade head --sql
```

---

## 3. Quality Gates & Release Verification

CI pipeline is **FULLY GREEN** with all gates passing:
- **Coverage Floor:** 60% baseline floor (`--cov-fail-under=60`).
- **Backend Tests:** 168 / 168 unit & API integration tests passing.
- **AI Module & Evals:** 10 / 10 unit tests and 30 / 30 baseline evaluation cases passing (100% pass rate).

Run all mandatory CI and regression checks locally:

```powershell
# 1. Dependency integrity check
python -m pip check

# 2. Ruff linter & style conformance
python -m ruff check backend ai
python -m ruff format --check backend ai

# 3. Backend regression test suite (168 tests) with coverage
pytest --cov=backend/app --cov-fail-under=60 -m "not live" backend/tests

# 4. AI tests & evaluation check
pytest ai/tests
python ai/evaluation/evaluate.py

# 5. Web production build & TypeScript validation
cd web
npm run build
```

---

## 4. Documentation Catalog

- **Demo-Day Runbook (10 Nov 2026):** [`docs/demo-runbook.md`](docs/demo-runbook.md)
- **Clean-Machine Rehearsal Report (CORR-9):** [`docs/clean-machine-rehearsal-report.md`](docs/clean-machine-rehearsal-report.md)
- **Go-Live Checklist & Verification:** [`docs/runbooks/go-live-checklist.md`](docs/runbooks/go-live-checklist.md)
- **Security Secrets Audit Report (CORR-5):** [`docs/secrets-scan-report.md`](docs/secrets-scan-report.md)
- **Demo-Blocker Issues Checklist:** [`docs/demo-blocker-issues.md`](docs/demo-blocker-issues.md)
- **Architecture Decisions (ADR 001–007):** [`docs/architecture-decisions.md`](docs/architecture-decisions.md)
- **Task Matrix (96 Tasks):** [`docs/task-matrix.md`](docs/task-matrix.md)
- **API Endpoints Reference (52 Endpoints):** [`docs/api-endpoints-reference.md`](docs/api-endpoints-reference.md)
- **API Standard & Envelope Contract:** [`docs/api-standard-v1.md`](docs/api-standard-v1.md)
- **OpenAPI 3.1 Specification:** [`docs/openapi.json`](docs/openapi.json)

---

## 5. Security & Authentication Model

1. **Fail-Closed Private Routes:** Missing, invalid, expired, or revoked Bearer JWTs return `HTTP 401 Unauthorized` with `WWW-Authenticate: Bearer`.
2. **Google Identity Verification:** Cryptographically validates Google OAuth ID tokens (`aud`, `iss`, `exp`, `sub`) using `google.oauth2.id_token`.
3. **Session Revocation & Rotation:** Single-use refresh token rotation; revoked tokens are permanently blacklisted in PostgreSQL across backend process restarts.
4. **Tenant Isolation:** Cross-user data isolation enforced on all entity queries and mutations.
5. **Zero Leaked Secrets:** Verified clean across 104 commits via Gitleaks v8.30.1; `.env` is gitignored and has never been committed.

---

## 6. Known External Dependencies & Platform Requirements

- **10 November 2026 Demo Mode:** On 10 November (Diwali–Balipratipada), Indian stock exchanges are closed. The platform operates in honest cached and replay mode via the Trade Time Machine, displaying explicit provenance labels (`REPLAY`, `FALLBACK_CACHED`, `LIVE`, or `DISCONNECTED`), with zero fabricated numbers.
- **Google OAuth Credentials:** Production live Google sign-in requires a valid Google Cloud Console OAuth 2.0 Web Client ID in `GOOGLE_CLIENT_ID`. For simulated testing, use Developer Sandbox Sign-In.
- **Operational Database:** PostgreSQL 16+ is used for operational transactional storage; migrations support SQLite batch operations for isolated unit testing.
- **Market Data Feed:** External market quotes use public REST endpoints with raw payload SHA-256 evidence hashing, automatic caching, and graceful fallback to verified baseline observations during network outages.
