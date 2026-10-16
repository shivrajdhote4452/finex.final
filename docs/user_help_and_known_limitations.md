# FinEx End-User Guide and Known Limitations Handbook

**Author:** Shivraj Dhote (`shivraj.dhote@finex.internal`)  
**Task ID:** S8-PRD-03  
**Date:** 16 October 2026  
**Classification:** Product Release Documentation  

---

## 1. Welcome to FinEx
FinEx is a precision financial intelligence and paper-trading terminal crafted for self-directed investors, students, and financial analysts in the Indian market. Built on modern graphite-black aesthetics, FinEx pairs sourced authentic market observations with mathematical rigor and educational AI assistance.

---

## 2. Core Feature Overview

### 2.1 Authentic Market Overview & Quotes
- **Authentic Data Sources:** Powered by official NSE Bhavcopy closing reports and verified filings.
- **Coverage:** Benchmark equities across Nifty 50, Energy (RELIANCE), IT (TCS, INFY), Banking (HDFCBANK, ICICIBANK), and Consumer Goods (ITC).
- **Exact Math:** PE ratios, EPS, and market valuations are calculated deterministically without LLM approximations.

### 2.2 Risk & Volatility Analysis
- **Beta Sensitivity:** Measures portfolio co-movement relative to the Nifty 50 index.
- **Value at Risk (VaR 95%):** Parametric 1-day potential downside estimation based on historical variance.
- **Sector Concentration (HHI):** Identifies over-exposure to single industries before market shocks occur.

### 2.3 Virtual Paper Practice Desk
- **Zero Real-Money Risk:** Practice portfolio seeded with ₹1,00,000 in virtual cash.
- **Atomic Trade Execution:** Buy and sell orders executed against authentic market prices with double-spend protection.
- **Ledger Audit Trail:** Append-only transaction ledger recording every virtual credit, debit, and fee.
- **Automated Trade Coach:** Instant behavioral feedback explaining liquidity, opportunity cost, and position sizing.

### 2.4 Smart Alerts & Notifications
- **Deterministic Trigger Rules:** Create threshold rules for price ceilings (`PRICE_ABOVE`), floors (`PRICE_BELOW`), and concentration limits.
- **Cooldown Deduplication:** Built-in 60-minute cooling window prevents duplicate alert spam during volatile market swings.
- **In-App Notification Center:** Actionable alerts with unread counters and read status tracking.

### 2.5 Goal Planning & Compounding Projections
- **Deterministic Projections:** Monthly compound interest model calculating future corpus and required monthly savings (`PMT`).
- **Interactive Scenarios:** Dynamically evaluate changing monthly contributions or extended timelines.
- **Milestone Tracking:** Visual progress bars displaying current funding status toward retirement, emergency funds, or capital purchases.

### 2.6 Spending Trend Analysis & Privacy Shield
- **100% PII Masking:** Bank CSV descriptions are automatically sanitized. Card PANs, bank accounts, and UPI IDs are masked (`****`) before storage.
- **Automated Categorization:** Rule-based tagging across Food, Groceries, Utilities, Housing, Travel, Shopping, Healthcare, and Investments.
- **Monthly Budget Summaries:** Comprehensive rollups of monthly debits, credits, and net savings rate.

### 2.7 Document-Grounded AI Research
- **Strict Grounding:** Research assistant draws exclusively from verified SEBI regulatory circulars and investor charters.
- **Explicit Citations:** Every claim links directly to the underlying regulatory paragraph.
- **Zero Hallucinated Tips:** Strictly refuses to recommend speculative trades, guaranteed returns, or stock tips.

---

## 3. Known Limitations and Boundary Disclosures

To uphold absolute technical transparency, the following environment-specific boundaries are documented:

1. **Market Data Latency:**
   - Observations represent official end-of-day NSE Bhavcopy closing prices and verified filing data.
   - Live tick-by-tick sub-second Level 2 orderbook feeds are outside the scope of this educational installation.
2. **AI Advice Boundary:**
   - FinEx AI is an educational research tool, **NOT a SEBI-registered Investment Advisor (RIA)**.
   - It will refuse all prompts requesting "sure-shot tips", "guaranteed profit percentages", or speculative derivative trade setups.
3. **CSV Statement Compatibility:**
   - Statement uploads require standard columns: `Date`, `Amount`, `Description` (or `Narration`), and optional `Type` (`DEBIT`/`CREDIT`).
   - Password-protected encrypted PDF statements must be converted to CSV prior to upload.
4. **Environment Infrastructure:**
   - FinEx operates in local developer sandbox mode utilizing high-performance in-memory and SQLite relational stores with complete schema isolation.
   - While architected for Azure Container Apps and Databricks Unity Catalog, logical local environments do not claim multi-region cloud cluster deployment.
