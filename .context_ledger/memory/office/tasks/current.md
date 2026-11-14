# Current Task (overwrite each session)

Holds exactly one task — the one being worked on right now.

- **Session:** Forge (OF01SS34) — **N18 Android app.** Porting the Kotlin decrypt pipeline, verified against goldens. First scheme (ZIV H1) done.
- **Toolchain (user-level):** JDK 17.0.21 + Gradle 8.9 in `~/.local/toolchain/`. Build/test: `cd android && JAVA_HOME="$HOME/.local/toolchain/jdk-17.0.21+9/Contents/Home" ./gradlew :core:test`. `:app` auto-skips when no Android SDK (settings.gradle.kts), so `:core` runs on a bare JDK.
- **Done so far:** 31 golden fixtures; Gradle scaffold; `Models.kt` (compiles); `GoldenParityTest` (model contract) passes; **ZIV H1 ported + decrypt-layer parity passes** (`Primitives.kt` PBKDF2+AES-GCM, `ZivH1.kt`, `ZivH1DecryptTest` vs all 6 ziv samples). Commits `1f78661`, `62e5cc8`, `5be53ab`. Parity methodology = **ADR-11** (decrypt-layer first; full-pipeline parity later, excluding `decrypt_trace`).
- **Next up:** port `detector.py` → `Detector.kt`; then more schemes decrypt-layer-first — **I1 (dark, simple base64 envelope), then A5 (hc), B2 (ehi)** [+ their crypto primitives: ChaCha20, Argon2id, XXTEA, AES-ECB/CBC, HC XOR]; then `router.py` + `parse_engine.py` and extend parity to full-pipeline. See `android/TASKS.md`.
- **Deferred:** `:app` (UI/APK) needs Android SDK (API 34) + ~several GB disk (only ~5 GB free). Schemes without samples (hat/npv/nsh/vhd/legacy) need samples (**N3**) for golden coverage.
- Prior pending items (N3/N4, packaged-Electron confirmations) unchanged.
