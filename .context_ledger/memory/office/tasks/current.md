# Current Task (overwrite each session)

Holds exactly one task — the one being worked on right now.

- **Session:** Forge (OF01SS34) — **N18 Android app.** The full decode pipeline (detect → decrypt → normalize) is ported to Kotlin and verified end-to-end.
- **Toolchain (user-level):** JDK 17.0.21 + Gradle 8.9 in `~/.local/toolchain/`. Build/test: `cd android && JAVA_HOME="$HOME/.local/toolchain/jdk-17.0.21+9/Contents/Home" ./gradlew :core:test`. `:app` auto-skips with no SDK.
- **Done:** `:core` has **6 green suites**. Decrypt-layer parity: ZIV H1, DARK I1, HC A5 (13/13), EHI B2 (6/6). **Full-pipeline parity** (`FullPipelineTest`): `parseConfig(file) == NormalizedConfig` for all 31 samples (minus decrypt_trace + filepath, ADR-11). Ported: `Detector.kt`, `ParseEngine.kt`, `Primitives.kt` (PBKDF2/AES-GCM-ECB-CBC/ChaCha20/Argon2id/XChaCha20-Poly1305), scheme decryptors, `Models.kt`. Last commit 6617220.
- **Next up:**
  1. **`:app` UI (Phase 6)** — SAF file pick → `ParseEngine.parseConfig` → render NormalizedConfig + export. **Needs the Android SDK (API 34)** installed + disk freed (~5 GB free).
  2. **Sample-less schemes** (hat E1, npv C1, nsh D1, vhd G1, legacy hc A1–A4, ehi B1, tls F1): **blocked on N3** — add sample configs for golden coverage, then port. The core crypto primitives for most are already in `Primitives.kt`.
  3. **SNI Host Hunter (Phase 7)** + **APK packaging (Phase 8)**.
- Prior pending items (N3/N4, packaged-Electron confirmations) unchanged.
