# Technical Report: Mobile APK Size Optimization (Universal Compression & ABI Splitting)

**Author:** FinEx Engineering Team  
**Project:** FinEx Mobile Application (Flutter 3.47 / Dart 3.13 / Android)  
**Subject:** Android Application Package (APK) Size Reduction Analysis & Implementation  
**Status:** Verified & Released (`v1.0.0-android`)  

---

## 1. Executive Summary

This report outlines the technical strategy, root causes, and empirical verification behind reducing the FinEx Android application release package from **52.2 MB** down to:
- **23.6 MB** for a **Single Universal APK** supporting all architectures (**54.9% reduction**, saving **30.1 MB**).
- **18.3 MB** for a **Targeted ARM 64-bit APK** (**65.0% reduction**, saving **33.9 MB**).

### Key Objective
Achieve significant binary size reduction **without altering any application behavior, code logic, visual design, user experience, or dependency integrity**. Both optimized binaries provide 100% feature parity with the baseline universal binary, running against the live production backend (`https://finex-final.onrender.com/api/v1`) with full Angel One SmartAPI and Google OAuth functionality.

### Benchmark Results Summary

| Build Strategy | Generated File | Size | % Reduction | Primary Target |
| :--- | :--- | :--- | :--- | :--- |
| **Universal Compressed (⭐ Recommended All-in-One)** | `finex-universal-compressed-release.apk` | **23.6 MB** | **-54.9%** | **Universal Single-File Installer** (bundles compressed `arm64-v8a`, `armeabi-v7a`, `x86_64`) |
| **Optimized: 64-bit ARM (Single ABI)** | `app-arm64-v8a-release.apk` | **18.3 MB** | **-64.9%** | **95%+ Modern Android Phones** (Samsung, OnePlus, Xiaomi, Realme, Pixel) |
| **Optimized: 32-bit ARM (Single ABI)** | `app-armeabi-v7a-release.apk` | **15.9 MB** | **-69.5%** | Older / Budget 32-bit Android phones |
| **Optimized: x86_64 (Single ABI)** | `app-x86_64-release.apk` | **19.7 MB** | **-62.3%** | PC Android Emulators & Chromebooks |
| **Baseline (Uncompressed Fat Universal APK)** | `app-release.apk` | **52.2 MB** | Baseline (0.0%) | Legacy uncompressed multi-architecture build |
| **Android App Bundle (`.aab`)** | `app-release.aab` | **~12–15 MB** | **~75.0%** | Google Play Store Dynamic Delivery (per-device download) |

---

## 2. Root Cause Analysis: Why Was the Baseline APK 52.2 MB?

When compiling with default settings (`flutter build apk --release`), Flutter and Android Gradle Plugin produce an uncompressed **Universal ("Fat") APK**.

### A. The Multi-Architecture Multiplier
Android devices run on diverse CPU architectures (ABIs — Application Binary Interfaces):
1. **`arm64-v8a`**: 64-bit ARM architecture powering virtually all modern smartphones.
2. **`armeabi-v7a`**: Older 32-bit ARM architecture used in legacy devices.
3. **`x86_64`**: 64-bit Intel/AMD architecture used by PC emulators and ChromeOS.

To ensure a Universal APK runs on *any* phone, it must package:
- Compiled C++ Flutter Engine (`libflutter.so`) **3 times** (once per ABI).
- Compiled Dart Ahead-Of-Time (AOT) machine code (`libapp.so`) **3 times**.
- Compiled native C/C++ plugins (e.g. `libdartjni.so`) **3 times**.

### B. Uncompressed Native Libraries in Modern AGP
In Android Gradle Plugin (AGP) 8+, the default packaging behavior stores native `.so` files with **0% compression** (the `STORED` zip method) rather than compressing them. While this allows the Android OS to memory-map (`mmap`) libraries directly from the APK file at runtime without extracting them to disk, it creates a massive download size penalty when bundling multiple ABIs into a single APK:

```
Baseline Universal APK (52.2 MB Uncompressed)
├── lib/
│   ├── arm64-v8a/
│   │   ├── libapp.so          (6.42 MB - 0% compression, STORED)
│   │   ├── libflutter.so      (11.75 MB - 0% compression, STORED)
│   │   └── libdartjni.so      (0.13 MB - 0% compression, STORED)
│   ├── armeabi-v7a/
│   │   ├── libapp.so          (7.05 MB - 0% compression, STORED)
│   │   ├── libflutter.so      (8.62 MB - 0% compression, STORED)
│   │   └── libdartjni.so      (0.08 MB - 0% compression, STORED)
│   └── x86_64/
│       ├── libapp.so          (6.55 MB - 0% compression, STORED)
│       ├── libflutter.so      (13.05 MB - 0% compression, STORED)
│       └── libdartjni.so      (0.12 MB - 0% compression, STORED)
├── assets/                    (Fonts, Icons, Shaders)
├── res/                       (Drawables, Layouts)
└── classes.dex                (Dalvik/ART executable Java bytecode)
```

**Total uncompressed native `.so` size:** ~53.7 MB across the three architectures.

---

## 3. Solution Strategy 1: Universal Native Library Compression (`useLegacyPackaging`)

### The Solution: Keep One Universal APK, Compress the Binaries
For teams that prefer distributing **one single universal installer** that works on every Android device without asking users to choose an ABI, Android Gradle Plugin provides native library compression via `useLegacyPackaging = true`.

### Gradle Implementation
In `mobile/android/app/build.gradle`:

```groovy
android {
    ...
    defaultConfig {
        applicationId "com.finex.mobile"
        minSdkVersion flutter.minSdkVersion
        targetSdkVersion 35
        versionCode flutterVersionCode.toInteger()
        versionName flutterVersionName
    }

    packaging {
        jniLibs {
            useLegacyPackaging = true
        }
    }
}
```

### Build Command
```bash
cd mobile
flutter build apk --release --dart-define=API_BASE_URL=https://finex-final.onrender.com
```

### Empirical Compression Results

| Shared Object File | Uncompressed Size | Compressed Size | Compression Ratio |
| :--- | :--- | :--- | :--- |
| `lib/arm64-v8a/libapp.so` | 6,423,432 bytes | **2,526,898 bytes** | **60.7% reduction** |
| `lib/arm64-v8a/libflutter.so` | 11,747,528 bytes | **5,478,700 bytes** | **53.4% reduction** |
| `lib/arm64-v8a/libdartjni.so` | 131,400 bytes | **26,050 bytes** | **80.2% reduction** |
| `lib/armeabi-v7a/libapp.so` | 7,045,704 bytes | **2,787,346 bytes** | **60.4% reduction** |
| `lib/armeabi-v7a/libflutter.so` | 8,615,468 bytes | **4,741,076 bytes** | **45.0% reduction** |
| `lib/armeabi-v7a/libdartjni.so` | 81,600 bytes | **24,669 bytes** | **69.8% reduction** |
| `lib/x86_64/libapp.so` | 6,554,504 bytes | **2,566,914 bytes** | **60.8% reduction** |
| `lib/x86_64/libflutter.so` | 13,051,040 bytes | **5,628,396 bytes** | **56.9% reduction** |
| `lib/x86_64/libdartjni.so` | 116,792 bytes | **28,385 bytes** | **75.7% reduction** |
| **Total APK Footprint** | **54,753,228 bytes (52.2 MB)** | **24,697,936 bytes (23.6 MB)** | **-54.89% Overall** |

### Key Benefits:
1. **Universal Compatibility:** One file installs seamlessly on ARM64, ARM32, and x86_64 devices.
2. **55% Download Reduction:** Reduces user bandwidth consumption by over **30 MB per install**.
3. **Zero Code Risk:** Preserves 100% of application code, dependencies, and UI assets unchanged.

---

## 4. Solution Strategy 2: ABI Splitting (`--split-per-abi`)

### Mechanism
For scenarios where maximum per-device size reduction is preferred, the build toolchain can slice the APK into separate, single-architecture binaries:

```bash
cd mobile
flutter build apk --release --split-per-abi --dart-define=API_BASE_URL=https://finex-final.onrender.com/api/v1
```

### Result:
- `app-arm64-v8a-release.apk` (**18.3 MB**): Removes 32-bit and x86_64 binaries completely, saving **65.0%** of the baseline size for modern devices.
- `app-armeabi-v7a-release.apk` (**15.9 MB**): Targeted exclusively at legacy 32-bit phones.
- `app-x86_64-release.apk` (**19.7 MB**): Targeted exclusively at PC emulators and ChromeOS.

---

## 5. Supplementary Optimization Strategies

### Strategy A: Android App Bundle (`.aab`) for Google Play Store
For official distribution through the Google Play Store, Google requires the **Android App Bundle** format:

```bash
flutter build appbundle --release --dart-define=API_BASE_URL=https://finex-final.onrender.com/api/v1
```

#### How Dynamic Delivery Works:
1. A single `.aab` is uploaded to Google Play Console.
2. Google Play's **Dynamic Delivery Engine** analyzes the user's specific device model upon download.
3. Google dynamically generates and delivers a custom APK containing **only the target device's ABI, screen density (e.g. xxhdpi), and language**.
4. The user downloads an ultra-compact package of approximately **12 MB to 15 MB**.

### Strategy B: Icon Font Tree-Shaking (Active in Release Builds)
Flutter automatically tree-shakes icon fonts in release builds:
- **Pre-shake size:** `1,645,184 bytes` (1.64 MB)
- **Post-shake size:** `9,396 bytes` (9.3 KB)
- **Efficiency:** **99.4% reduction** in icon asset overhead.

---

## 6. Verification & Deployment

All optimized binaries are validated and published on GitHub Releases.

### Verified GitHub Release Assets (`v1.0.0-android`)

| Package | Direct Link | File Size | Description |
| :--- | :--- | :--- | :--- |
| **Universal Compressed (⭐ Recommended All-in-One)** | [Download `finex-universal-compressed-release.apk`](https://github.com/shivrajdhote4452/finex.final/releases/download/v1.0.0-android/finex-universal-compressed-release.apk) | **23.6 MB** | Bundles compressed `arm64-v8a`, `armeabi-v7a`, and `x86_64` into a single universal APK |
| **ARM 64-bit (Single ABI)** | [Download `app-arm64-v8a-release.apk`](https://github.com/shivrajdhote4452/finex.final/releases/download/v1.0.0-android/app-arm64-v8a-release.apk) | **18.3 MB** | Single ABI sliced build for modern phones |
| **ARM 32-bit (Single ABI)** | [Download `app-armeabi-v7a-release.apk`](https://github.com/shivrajdhote4452/finex.final/releases/download/v1.0.0-android/app-armeabi-v7a-release.apk) | **15.9 MB** | Single ABI sliced build for older 32-bit phones |
| **x86_64 (Single ABI)** | [Download `app-x86_64-release.apk`](https://github.com/shivrajdhote4452/finex.final/releases/download/v1.0.0-android/app-x86_64-release.apk) | **19.7 MB** | Single ABI sliced build for PC emulators |
| **Universal Uncompressed (Baseline)** | [Download `app-release.apk`](https://github.com/shivrajdhote4452/finex.final/releases/download/v1.0.0-android/app-release.apk) | **52.2 MB** | Legacy uncompressed multi-architecture installer |

### Release Verification Metadata
- **Backend Gateway:** `https://finex-final.onrender.com/api/v1` (Healthy & Verified)
- **Live Data Gateway:** Angel One SmartAPI (Live Quotes & Historical Session Bars)
- **Google OAuth Client:** `com.finex.mobile` (Package verified with SHA-1 fingerprint)
- **Signature Scheme:** APK Signature Scheme v2 (Compatible in-place upgrade)
- **Compilation Toolchain:** Flutter 3.47.0 • Dart 3.13.0 • Kotlin 2.2.20 • Gradle 9.3.1

---

## 7. Recommendations for Engineering Presentation

When presenting this optimization to technical leadership:

1. **For General Internal Testing / Sideloading (Universal):**
   - Distribute **`finex-universal-compressed-release.apk` (23.6 MB)**.
   - **Why:** Anyone on the team can install it regardless of their phone or emulator model, without experiencing the 52 MB download overhead.

2. **For Bandwidth-Constrained Device Sideloading:**
   - Distribute **`app-arm64-v8a-release.apk` (18.3 MB)** for team members with modern phones.

3. **For Official Production Distribution:**
   - Deploy as an **Android App Bundle (`.aab`)** to Google Play Store to leverage server-side dynamic delivery (~14 MB downloads).

4. **Code Safety Guarantee:**
   - Both optimizations were achieved purely via compilation toolchain and packaging configuration. Zero application logic, UI design, API integration, or data layer components were altered.
