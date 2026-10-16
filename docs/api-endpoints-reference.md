# FinEx API v1 Complete Endpoint Reference

**Base URL:** `http://localhost:8000/api/v1`  
**Interactive Swagger UI:** [`http://localhost:8000/api/v1/docs`](http://localhost:8000/api/v1/docs)  
**Interactive ReDoc UI:** [`http://localhost:8000/api/v1/redoc`](http://localhost:8000/api/v1/redoc)  
**OpenAPI Specification:** [`docs/openapi.json`](file:///f:/Project%20File/Finex%20Final/docs/openapi.json)  
**Standard Envelope Specification:** [`docs/api-standard-v1.md`](file:///f:/Project%20File/Finex%20Final/docs/api-standard-v1.md)  
**Author:** Shivraj Dhote (`shivraj.dhote@finex.internal`)  

---

## 1. Authentication & Identity (`/auth` & `/users`)
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/v1/auth/google` | Authenticate with Google OAuth ID token & issue JWT | No |
| `POST` | `/api/v1/auth/refresh` | Single-use rotation: revokes prior token & issues fresh JWT | Yes (Bearer) |
| `POST` | `/api/v1/auth/revoke` | Explicitly invalidate an active JWT token | Yes (Bearer) |
| `GET` | `/api/v1/users/me` | Fetch authenticated user investor profile & verification state | Yes (Bearer) |
| `POST` | `/api/v1/users/consent` | Audit-compliant recording of terms and disclaimer acceptance | Yes (Bearer) |

---

## 2. Market Data & Watchlists (`/market` & `/watchlists`)
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/v1/market/instruments` | List all supported NSE instruments, sectors, and canonical IDs | No |
| `GET` | `/api/v1/market/search` | Search instruments by symbol, company name, or sector | No |
| `GET` | `/api/v1/market/quotes/{symbol}` | Sourced authentic closing quote (Bhavcopy prices, P/E, EPS) | No |
| `GET` | `/api/v1/market/history/{symbol}` | Historical OHLCV candle bars with observation timestamps | No |
| `GET` | `/api/v1/watchlists` | List personal watchlists for caller | Yes (Bearer) |
| `POST` | `/api/v1/watchlists` | Create a new user watchlist | Yes (Bearer) |
| `POST` | `/api/v1/watchlists/{id}/items` | Add security symbol to watchlist | Yes (Bearer) |
| `DELETE` | `/api/v1/watchlists/{id}/items/{symbol}` | Remove security from watchlist | Yes (Bearer) |

---

## 3. Portfolio Management & Intelligence (`/portfolios` & `/portfolio-intelligence`)
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/v1/portfolios/me` | Retrieve active portfolio, holdings, and sector allocations | Yes (Bearer) |
| `POST` | `/api/v1/portfolios/{id}/holdings` | Add or update an equity holding with acquisition cost basis | Yes (Bearer) |
| `DELETE` | `/api/v1/portfolios/{id}/holdings/{h_id}` | Remove holding from portfolio | Yes (Bearer) |
| `GET` | `/api/v1/portfolios/{id}/summary` | Deterministic equity valuation, unrealized PnL, cash balance | Yes (Bearer) |
| `GET` | `/api/v1/portfolio-intelligence` | Concentration risk (HHI index) & top holdings exposure | Yes (Bearer) |
| `POST` | `/api/v1/portfolio-intelligence/scenario` | Run deterministic shock simulation (e.g. 15% IT decline) | Yes (Bearer) |

---

## 4. Risk Profile & Assessments (`/risk`)
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/v1/risk/questions` | Sourced regulatory risk capacity & horizon questionnaire | No |
| `POST` | `/api/v1/risk/assessments` | Submit answers and receive deterministic score (1–10) | Yes (Bearer) |

---

## 5. Paper Trading Simulator (`/paper-trading`)
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/v1/paper-trading/account` | Virtual account summary (₹1,00,000 baseline cash & equity) | Yes (Bearer) |
| `POST` | `/api/v1/paper-trading/orders` | Atomic market buy/sell order with idempotency protection | Yes (Bearer) |
| `GET` | `/api/v1/paper-trading/orders` | History of virtual submitted, filled, and rejected orders | Yes (Bearer) |
| `GET` | `/api/v1/paper-trading/positions` | Current active virtual open positions and mark-to-market PnL | Yes (Bearer) |
| `GET` | `/api/v1/paper-trading/ledger` | Append-only cash ledger movements and trade executions | Yes (Bearer) |
| `POST` | `/api/v1/paper-trading/reset` | Controlled virtual account reset with audit trail | Yes (Bearer) |

---

## 6. Smart Alerts & Notification Center (`/alerts` & `/notifications`)
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/v1/alerts/rules` | Create alert rule (`PRICE_ABOVE`, `PRICE_BELOW`, etc.) | Yes (Bearer) |
| `GET` | `/api/v1/alerts/rules` | List user configured alert rules with cooldown timers | Yes (Bearer) |
| `GET` | `/api/v1/alerts/rules/{id}` | Inspect specific rule definition and trigger thresholds | Yes (Bearer) |
| `PATCH` | `/api/v1/alerts/rules/{id}` | Update rule threshold value or comparison operator | Yes (Bearer) |
| `DELETE` | `/api/v1/alerts/rules/{id}` | Permanently delete alert rule | Yes (Bearer) |
| `POST` | `/api/v1/alerts/evaluate` | Deterministic evaluation of all due rules against prices | Yes (Bearer) |
| `GET` | `/api/v1/notifications` | List in-app notifications with read status & delivery status | Yes (Bearer) |
| `PATCH` | `/api/v1/notifications/{id}/read` | Mark individual notification as read | Yes (Bearer) |
| `POST` | `/api/v1/notifications/mark-all-read` | Mark all user notifications as read | Yes (Bearer) |
| `GET` | `/api/v1/notifications/unread-count` | Retrieve badge counter for unread notifications | Yes (Bearer) |

---

## 7. Financial Goals & Planning (`/goals`)
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/v1/goals` | Create goal with deterministic monthly compounding validation | Yes (Bearer) |
| `GET` | `/api/v1/goals` | List all user goals sorted by target completion date | Yes (Bearer) |
| `GET` | `/api/v1/goals/{id}` | Get goal details, progress percentage, and shortfall | Yes (Bearer) |
| `PATCH` | `/api/v1/goals/{id}` | Update goal title, target corpus, or assumed CAGR % | Yes (Bearer) |
| `POST` | `/api/v1/goals/{id}/contributions` | Record progress deposit toward goal | Yes (Bearer) |
| `GET` | `/api/v1/goals/{id}/projection` | Retrieve future value projection & monthly required savings | Yes (Bearer) |

---

## 8. Spending Analytics & Privacy-Preserving Ingestion (`/spending`)
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/v1/spending/upload` | Upload CSV bank statement; auto-masks PII (`****`) | Yes (Bearer) |
| `GET` | `/api/v1/spending/transactions` | List masked transactions with assigned spending categories | Yes (Bearer) |
| `PATCH` | `/api/v1/spending/transactions/{id}/category`| Override/review categorization with confidence score | Yes (Bearer) |
| `GET` | `/api/v1/spending/summary` | Monthly debit/credit rollups and category breakdowns | Yes (Bearer) |

---

## 9. AI Research Assistant & Citations (`/ai`)
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/v1/ai/conversations` | List conversation sessions with user isolation | Yes (Bearer) |
| `POST` | `/api/v1/ai/conversations` | Create a new document-grounded research conversation | Yes (Bearer) |
| `GET` | `/api/v1/ai/conversations/{id}/messages` | Retrieve message transcript with citations & feedback | Yes (Bearer) |
| `POST` | `/api/v1/ai/conversations/{id}/messages` | Send query; answers strictly grounded in SEBI circulars | Yes (Bearer) |
| `DELETE` | `/api/v1/ai/conversations/{id}` | Delete conversation session | Yes (Bearer) |
| `POST` | `/api/v1/ai/feedback` | Submit thumbs up/down rating with correlation ID | Yes (Bearer) |
| `GET` | `/api/v1/ai/compare` | AI-assisted comparative valuation across 2-3 securities | Yes (Bearer) |

---

## 10. Health & Diagnostics (`/health`)
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/v1/health/live` (or `/healthz`) | Process liveness probe (returns 200 when alive) | No |
| `GET` | `/api/v1/health/ready` (or `/readyz`) | Dependency readiness probe (returns 503 if DB down) | No |
