# FinEx Repository Secrets Scan Report (CORR-5)

**Date:** 25 October 2026  
**Auditor:** Antigravity Agent  
**Repository:** `shivrajdhote4452/finex.final`  
**Branch:** `audit/secrets-scan-and-demo-issues` (against `main`)  

---

## 1. Scan Scope

A comprehensive security secrets audit was conducted across:
1. **Working Tree:** All tracked source code, configuration files, and documentation in the repository.
2. **Full Git Commit History:** All 104 commits across all branches in `shivrajdhote4452/finex.final`.
3. **Targeted Credential Signatures:**
   - Groq API keys (`gsk_*`)
   - Google / Gemini API keys (`AIza*`)
   - Alpaca Paper / Live API keys and secrets (`AK*`, `PK*`, `CK*`)
   - Generic API keys, private keys, JWT secrets, and high-entropy secret patterns
   - Historical verification of `.env` file commits

---

## 2. Tools & Methodology Used

1. **Gitleaks v8.30.1**:
   - Repository-wide scan executed with 100% secret redaction:
     `gitleaks detect --source=. -v --redact=100`
   - Scanned 104 commits (~3.79 MB) covering the entire commit graph.
2. **Deep History Git Diff Inspection**:
   - Targeted regex search across all commit diffs (`git log --all -p -G <pattern>`) for Groq, Google/Gemini, Alpaca, AWS, GitHub tokens, and private keys.
3. **Environment File Audit**:
   - Inspection of git history for any commit adding or modifying `.env`:
     `git log --all --full-history -- "**.env*" ".env"`
   - Verification of `.gitignore` configuration for local development environment files.

---

## 3. Findings & Triage Analysis

### 3.1 Git History Findings (Tracked Codebase)
Across all 104 historical commits, Gitleaks flagged 8 items under the `generic-api-key` rule. Every single occurrence was triaged and confirmed to be a synthetic test fixture:

| Commit | File Path | Line Number | Rule Name | Finding Classification |
| :--- | :--- | :--- | :--- | :--- |
| `d7c08f24` | `backend/tests/test_paper_trading_api.py` | 475 | `generic-api-key` | **Placeholder / Test Fixture** (`idempotency_key`) |
| `94fc0dd3` | `backend/tests/test_paper_trading_api.py` | 305 | `generic-api-key` | **Placeholder / Test Fixture** (`idempotency_key`) |
| `94fc0dd3` | `backend/tests/test_paper_trading_api.py` | 319 | `generic-api-key` | **Placeholder / Test Fixture** (`idempotency_key`) |
| `94fc0dd3` | `backend/tests/test_ch_acceptance_matrix.py` | 228 | `generic-api-key` | **Placeholder / Test Fixture** (test key variable) |
| `94fc0dd3` | `backend/tests/test_ch_acceptance_matrix.py` | 229 | `generic-api-key` | **Placeholder / Test Fixture** (test key variable) |
| `37f7d595` | `backend/tests/test_paper_trading_api.py` | 73 | `generic-api-key` | **Placeholder / Test Fixture** (`idempotency_key`) |
| `37f7d595` | `backend/tests/test_paper_trading_api.py` | 118 | `generic-api-key` | **Placeholder / Test Fixture** (`idempotency_key`) |
| `37f7d595` | `backend/tests/test_paper_trading_api.py` | 142 | `generic-api-key` | **Placeholder / Test Fixture** (`idempotency_key`) |

### 3.2 Working Tree Findings (Tracked Files)
In the current working tree, the only occurrences flagged are:
- `backend/tests/test_paper_trading_api.py` (lines 102, 147, 174, 335, 349, 480): Synthetic idempotency key fixtures used for deduplication unit tests.
- `backend/tests/test_ch_acceptance_matrix.py` (lines 267, 268): Synthetic idempotency key fixtures used for order replay tests.
- `.env.example`: Public template file containing explicitly marked placeholders (`YOUR_*_HERE`, `placeholder-client-id`, `placeholder-client-secret`).

### 3.3 Historical `.env` Verification
- **Confirmed:** `.env` has **NEVER** been committed to the git history of `shivrajdhote4452/finex.final`.
- **Gitignore Verification:** Line 34 of `.gitignore` actively ignores `.env`, `backend/.env`, and `web/.env`.

### 3.4 Angel One Context
- Prior scans verified Angel One SmartAPI credentials and TOTP implementations as clean. No real Angel One credentials were detected during this broader audit.

---

## 4. Conclusion

**clean: no real non-Angel secrets found**

All flagged occurrences in the repository history and working tree are confirmed to be synthetic test fixtures (order idempotency keys) and documentation placeholders. No real credentials (Groq, Google/Gemini, Alpaca, or generic) are present in the repository or its commit history.
