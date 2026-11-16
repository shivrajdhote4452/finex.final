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

---

## 6. Release History & Verification Matrix

### Release v1.0.1-android (16 November 2026) — PR #38 Parity Build
- **Version:** `1.0.1+2` (versionCode: `2`, versionName: `1.0.1`)
- **Source Base:** `f0cefe7e895628ca810f6be6b4e264d3bcbfa2ad` (PR #38 merge into `main`)
- **Version & Documentation Commit:** `60bee148566da8181f9a0397579f1db1ee4ea1e8` (PR #39 on `dev`)
- **Release Tag Target:** Merge commit of PR #39 on `main` (tag: `v1.0.1-android`)
- **Key Parity Fixes:**
  - Authoritative paper order handling with no fake fills on backend rejection.
  - Idempotent order reconciliation on network timeouts (`mob-ord-...`).
  - Elimination of hardcoded fallback market prices (neutral `—` for unavailable quotes).
  - Authentic account state (elimination of hardcoded ₹1,00,000 cash fallbacks; honest error views).
  - Safety confirmation dialog for account resets (cash restored to ₹1,00,000, positions cleared, order history preserved, pending orders not canceled).
  - Owner-gated deposit controls matching web and backend contracts.
- **Verification:**
  - `flutter analyze`: 0 issues found.
  - `flutter test`: 28 / 28 passed.
  - APK Signature: Scheme v2 verified.
  - Device Testing: Not tested on a live physical device or emulator (none attached).

| Package | Architecture | Size | SHA-256 Checksum |
| :--- | :--- | :--- | :--- |
| `app-arm64-v8a-release.apk` | ARM 64-bit (`arm64-v8a`) | 8.52 MB (8,938,665 B) | `8D1B4717DEF824685D3135B15BFB81353E2417B65BAD0DA6E3705B076CD338BE` |
| `app-armeabi-v7a-release.apk` | ARM 32-bit (`armeabi-v7a`) | 8.07 MB (8,460,147 B) | `2CF2CD11E9FA94C254465C172D3076E057D3AD97E8CDC5C29F3AA4A71E704D75` |
| `app-x86_64-release.apk` | x86_64 | 8.71 MB (9,135,032 B) | `78ED75A6E0535120F5A000236DB9ABE3CC34C8AD819CBE2ED75E9950245A7B2F` |
| `finex-universal-compressed-release.apk` | Universal (`arm64`, `armeabi`, `x86_64`) | 23.61 MB (24,756,384 B) | `BCE91AD4226CEDDC65FA2421A17B54042993233479E77CE90022A4CD9D7E18EE` |
| `finex-release.aab` | Play Store Bundle (`.aab`) | 51.05 MB (53,530,717 B) | `1361A5E169BB98AFF4FB244CB218B44B85E0B4C43E7752F624189CF401C6FD59` |

### Release v1.0.0-android (29 October 2026) — Initial Mobile Release
- **Version:** `1.0.0+1` (versionCode: `1`, versionName: `1.0.0`)
- **GitHub Release:** [`v1.0.0-android`](https://github.com/shivrajdhote4452/finex.final/releases/tag/v1.0.0-android)
- **Status:** Preserved permanently with original APK and AAB assets intact.

