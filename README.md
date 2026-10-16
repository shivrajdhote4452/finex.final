# FinEx — Financial Excellence Platform

**Developer & Owner:** Shivraj Dhote (`shivraj.dhote@finex.internal`)  
**Design System:** Graphite Terminal — Pure Black (`#000000`), Orange Actions (`#F29A60`), Semantic Green/Red status  
**Target Handoff:** 10 November 2026  
**Repository:** [github.com/shivrajdhote4452/finex.final](https://github.com/shivrajdhote4452/finex.final.git)

---

## 1. Architectural Overview

FinEx is an educational financial intelligence platform engineered with strict deterministic domain calculations and real-data provenance:
- **Backend Core:** FastAPI (`127.0.0.1:8000`), Pydantic v2, SQLAlchemy 2.0 (AsyncIO), PyJWT, and official `google-auth`.
- **Web Terminal:** React 18, TypeScript, Vite (`localhost:3000`), Tailwind-free custom CSS tokens.
- **Mobile Terminal:** Flutter 3, Dart, responsive Graphite Terminal design tokens.
- **Data Engineering:** PostgreSQL/Lakebase operational transactional database, Databricks Delta Lake analytics pipelines.
- **AI & RAG:** Grounded deterministic evaluation engine with traceable citations (SEBI, RBI, NSE regulatory publications).

---

## 2. Quickstart & Local Setup

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- Flutter 3.24+ (and Chrome / Android SDK for device runs)

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

# Install exact declared dependencies
python -m pip install -r backend/requirements.txt
python -m pip check

# Start live backend server (hot-reload enabled)
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
Interactive API Documentation will be immediately accessible at:
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

### Mobile Frontend Setup (Flutter)
```powershell
cd mobile
flutter pub get
flutter run -d chrome
```

---

## 3. Quality Gates & Release Verification

Run all mandatory CI and regression checks locally:

```powershell
# 1. Dependency integrity check
python -m pip check

# 2. Ruff linter & style conformance
python -m ruff check backend ai
python -m ruff format --check backend ai

# 3. Backend & AI regression test suite (92 tests)
python -m pytest backend/tests ai/evaluation -q

# 4. Flutter static analysis
cd mobile
flutter analyze
flutter test
```

---

## 4. Documentation Catalog

- **Task Matrix (96 Tasks):** [`docs/task-matrix.md`](docs/task-matrix.md)
- **API Endpoints Reference (52 Endpoints):** [`docs/api-endpoints-reference.md`](docs/api-endpoints-reference.md)
- **API Standard & Envelope Contract:** [`docs/api-standard-v1.md`](docs/api-standard-v1.md)
- **OpenAPI 3.1 Specification:** [`docs/openapi.json`](docs/openapi.json)

---

## 5. Security & Authentication Model

1. **Fail-Closed Private Routes:** Missing, invalid, expired, or revoked Bearer JWTs return `HTTP 401 Unauthorized` with `WWW-Authenticate: Bearer`.
2. **Google Identity Verification:** Cryptographically validates Google OAuth ID tokens (`aud`, `iss`, `exp`, `sub`) using `google.oauth2.id_token`.
3. **Session Revocation & Rotation:** Single-use refresh token rotation; revoked tokens are permanently blacklisted across requests.
4. **Tenant Isolation:** Cross-user data isolation enforced on all entity queries and mutations.

---

## 6. Known External Dependencies & Blockers

- **Google OAuth Client ID:** Requires a production Google Cloud Console OAuth 2.0 Web Client ID to verify live Google Sign-In logins.
- **Database Server:** Local tests run against async SQLite storage; production deployments require an active PostgreSQL instance configured via `DATABASE_URL`.
- **Market Data Feed:** Default provider is `yfinance` with caching; external market hours and upstream rate limits apply.
