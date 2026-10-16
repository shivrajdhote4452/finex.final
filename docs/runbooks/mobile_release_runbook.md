# FinEx Mobile Application Release and Store Publication Runbook

**Author:** Shivraj Dhote (`shivraj.dhote@finex.internal`)  
**Task ID:** S8-PRD-02  
**Date:** 16 October 2026  
**Classification:** Internal Engineering Standard  

---

## 1. Application Overview & Target Platforms
- **Framework:** Flutter 3.47.0 (Dart 3.13)
- **Targets:**
  - **Android:** API Level 26 (Android 8.0 Oreo) up to API Level 35 (Android 15)
  - **iOS:** iOS 15.0+ (Xcode 15+ toolchain required for final App Store signing)
  - **Web Terminal:** Modern Chromium / Safari WebGL engines
- **Theme Standard:** Pure graphite black terminal (`#000000`, 0% tint) per Terminal Visual Guide.

---

## 2. Security & Permissions Review

### Android Manifest Audit (`mobile/android/app/src/main/AndroidManifest.xml`)
The application strictly enforces least privilege:
- `android.permission.INTERNET`: Required for FastAPI TLS communication.
- `android.permission.ACCESS_NETWORK_STATE`: Required for offline/online connectivity banner.
- **Explicitly Excluded / Forbidden:**
  - ❌ `READ_CONTACTS` / `READ_CALL_LOG`
  - ❌ `ACCESS_FINE_LOCATION` / `ACCESS_COARSE_LOCATION`
  - ❌ `CAMERA` / `RECORD_AUDIO`
  - ❌ `READ_EXTERNAL_STORAGE` (no broad storage access)

### Secure Storage & Token Hygiene
- Authentication tokens stored in encrypted platform storage (`flutter_secure_storage` / Keychain / Keystore).
- Zero tokens logged to console outputs or debug logs.
- Automatic session invalidation upon token revocation or refresh failure.

---

## 3. Production Release Build Commands

### Android Production Bundle (AAB for Google Play)
```bash
# Clean previous build artifacts
flutter clean
flutter pub get

# Build optimized production Android App Bundle
flutter build appbundle --release --obfuscate --split-debug-info=build/app/outputs/symbols

# Output location:
# build/app/outputs/bundle/release/app-release.aab
```

### Android Standalone APK (for Direct Sideloading / Internal Testing)
```bash
flutter build apk --release --split-per-abi
# Output location:
# build/app/outputs/flutter-apk/app-arm64-v8a-release.apk
```

### iOS Archive Configuration
```bash
# Pre-requisite: macOS environment with Xcode 15+ and valid Apple Developer Team profile
flutter build ipa --release --export-options-plist=ios/ExportOptions.plist
```
> **Note on Solo Developer Environment:** In accordance with the Sprint Plan handbook principles, iOS archive creation is prepared via reproducible source code and Xcode project files; physical `.ipa` generation is executed when running on macOS CI runners with provisioned signing certificates.

---

## 4. Google Play & App Store Listing Packet

### Store Metadata
- **Application Title:** FinEx — Financial Terminal & Educational Lab
- **Subtitle:** Authentic Indian Market Analytics & Paper Trading
- **Category:** Finance / Education
- **Content Rating:** PEGI 3 / Everyone (No simulated gambling, no real-money transactions)
- **Privacy Policy URL:** `https://finex.finance/privacy`
- **Support Email:** `shivraj.dhote@finex.internal`

### Short Description (80 Characters)
> Authentic NSE analytics, risk metrics, virtual trading & document-grounded AI.

### Full Store Description
```text
FinEx is a premier educational financial terminal built for investors and learners seeking authentic Indian market intelligence without real-money speculation.

Key Features:
- REAL MARKET OBSERVATIONS: Sourced authentic NSE Bhavcopy data across Nifty 50, Energy, IT, Banking, and Consumer equities.
- RISK & VOLATILITY ANALYTICS: Calculate exact Beta, Value at Risk (VaR 95%), and sector concentrations with zero rounding shortcuts.
- ZERO-RISK PAPER PRACTICE: Hone portfolio management using a ₹1,00,000 virtual ledger with atomic trade execution and educational trade coaching.
- SMART ALERTS: Configure deterministic price and sector concentration alerts with cooldown deduplication.
- GOAL PLANNING & SPENDING: Compound monthly projection models and bank statement spending categorizations with 100% PII masking.
- DOCUMENT-GROUNDED AI: Research assistant strictly grounded in authentic SEBI circulars and investor charters.

STATUTORY EDUCATIONAL DISCLAIMER:
FinEx is strictly an educational research platform and virtual practice environment. It does NOT provide SEBI-registered investment advice, stock tips, or guaranteed returns. All market figures are provided for financial literacy only.
```

---

## 5. Mobile Smoke Test & Rollback Checklist
- [x] Application boots into pure black canvas (`#000000`).
- [x] Ticker tape displays authenticated workspace status ("Shivraj's workspace").
- [x] Bottom navigation transitions cleanly across: Overview, Markets, Ask FinEx, More.
- [x] More menu navigates to Paper Practice, Alerts, Goals, and Spending screens.
- [x] Zero network or assertion crashes in release profile.
