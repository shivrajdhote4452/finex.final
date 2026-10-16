# FinEx — Real-Data Source Registry & Lineage Log

**Compliance:** Zero-fabricated numbers. Genuine observations and public regulatory documents only.  

---

## 1. Market Data Sources

### Primary Adapter: Yahoo Finance (yfinance / Direct REST)
- **Use Case:** Historical daily prices and quotes for initial Indian equity universe.
- **Initial Verified Universe:**
  1. `RELIANCE.NS` (Reliance Industries Ltd)
  2. `TCS.NS` (Tata Consultancy Services Ltd)
  3. `INFY.NS` (Infosys Ltd)
  4. `HDFCBANK.NS` (HDFC Bank Ltd)
  5. `ICICIBANK.NS` (ICICI Bank Ltd)
- **Currency:** INR
- **Fields Preserved:**
  - `source`: `"yfinance"`
  - `canonical_id`: e.g. `"NSE:RELIANCE"`
  - `observed_at`: UTC timestamp of trading session close
  - `ingested_at`: UTC timestamp when fetched
  - `open`, `high`, `low`, `close`, `adj_close`, `volume`
  - `currency`: `"INR"`
  - `served_from_cache`: boolean

### Fallback Policy
- If upstream provider fails or rate-limits:
  1. Return last recorded real price from cache with its exact `observed_at` timestamp.
  2. Mark `status`: `"CACHED"` or `"UNAVAILABLE"`.
  3. NEVER return `0` or random mock numbers in production/demo mode.

---

## 2. Regulatory & Educational Documents for RAG

Approved real documents for Sprint 1 & Sprint 4 RAG ingestion:
1. **SEBI Investor Education Material:**
   - *Title:* SEBI Guide to Financial Education for Beginners
   - *Publisher:* Securities and Exchange Board of India (SEBI)
   - *Topic:* Equities, Mutual Funds, Risk Diversification
2. **NSE Factsheet / Market Fundamentals:**
   - *Title:* NIFTY 50 Index Factsheet & Methodology
   - *Publisher:* NSE Indices Limited
   - *Topic:* Index construction, sector weights, market capitalization rules
3. **Reserve Bank of India (RBI) Financial Literacy Content:**
   - *Title:* RBI Financial Literacy Guide - Savings, Borrowing, and Budgeting
   - *Publisher:* Reserve Bank of India
   - *Topic:* Compounding, emergency funds, debt management
