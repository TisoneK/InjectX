# Current Task (overwrite each session)

Holds exactly one task — the one being worked on right now.

- **Session:** Forge (OF01SS34) — **N18 Android app.** All four golden-covered decrypt schemes ported + verified in Kotlin.
- **Toolchain (user-level):** JDK 17.0.21 + Gradle 8.9 in `~/.local/toolchain/`. Build/test: `cd android && JAVA_HOME="$HOME/.local/toolchain/jdk-17.0.21+9/Contents/Home" ./gradlew :core:test`. `:app` auto-skips with no SDK.
- **Done:** `:core` has **5 green suites**. Schemes verified decrypt-layer vs the Python `_all_fields`: **ZIV H1** (5be53ab), **DARK I1** (128db9a), **HC A5** (5be466c, 13/13), **EHI B2** (4c0d976, 6/6). `Primitives.kt` = PBKDF2, AES-GCM/ECB/CBC, ChaCha20(seek), Argon2id, XChaCha20-Poly1305 (HChaCha20 hand-rolled). Parity contract = ADR-11 (decrypt-layer first, trace excluded).
- **Next up:**
  1. **Detector** (`detector.py` → `Detector.kt`) + **parse engine** (`parse_engine.py`) → then extend parity to **full-pipeline** (`pipeline(source) == fixture.normalized` minus `decrypt_trace`).
  2. **Sample-less schemes** (hat E1, npv C1, nsh D1, vhd G1, legacy hc A1–A4, ehi B1, tls F1): **blocked on N3** — add sample configs so they get golden coverage before porting.
  3. **`:app` UI (Phase 6) + APK (Phase 8):** needs the **Android SDK (API 34)** installed + disk freed (~5 GB free now).
- Prior pending items (N3/N4, packaged-Electron confirmations) unchanged.
