# ADR 006: Mobile (Flutter) Scope Decision — Defer vs. Fund

- **Status:** DECIDED (DEFER)
- **Decision:** APPROVED (Option A — Defer to Post-Demo)
- **Decision Date:** 25 October 2026
- **Decision Authority:** Shivraj Dhote (Project Owner & Sole Developer)

---

## Decision Record
**Decision:** **APPROVED (Option A — Defer to Post-Demo)**

**Rationale:**
As a solo developer with the official demonstration handoff scheduled for 10 November 2026 (16 days remaining), dedicating 15–20 hours to Android Keystore signing, Gradle build configuration, and emulator validation poses an unacceptable risk to core demo stability. The React + Vite web platform is 100% feature-complete, accessible, and verified across all 8 sprint domains. Deferring native mobile packaging to Phase 2 (Sprint 9+) guarantees 100% focus on web hardening, offline market replay rehearsal, and clean demonstration execution.

**Revisit Condition:**
Immediately following the 10 November 2026 demonstration handoff.

---

## Context
The React + Vite web platform (`web/`) is 100% feature-complete, responsive, WCAG-accessible, and verified across all 8 sprint domains (live market feed, FinEx live charts, paper trading ledger, AI assistant, risk profiling, portfolio analytics).

The Flutter mobile codebase (`mobile/lib/`) currently contains skeleton screens and widget abstractions. Bringing the native mobile application to release-grade quality for the 10 November 2026 demonstration requires mobile testing, Android keystore signing, emulator validation, and platform packaging.

---

## Tradeoff Analysis (Defer vs. Fund)

### Option A: Defer to Post-Demo (Adopted Decision)
- **Tradeoff:**
  - **Pros:** Zero risk of mobile emulator crashes, platform dependency friction, or store signing failures during the 10 November demonstration. Allows 100% focus on web hardening, cached-mode market demonstration, and educational paper-trading workflows.
  - **Cons:** Demo is web-only; mobile is shown as an architectural companion repository rather than a live-running APK/IPA.
- **Estimated Effort:** 0 additional hours before 10 November 2026. Native packaging scheduled for Sprint 9+ (Phase 2).

### Option B: Fund Before 31 October 2026
- **Tradeoff:**
  - **Pros:** Live Android APK demonstrated alongside web application on 10 November.
  - **Cons:** Diverts ~20 hours of sole-developer capacity away from web reliability, market rehearsal, and clean-machine verification; introduces simulator and device resolution liabilities during presentation.
- **Estimated Effort:** 15–20 hours before 31 October 2026 (Keystore configuration, gradle build optimization, device testing).

