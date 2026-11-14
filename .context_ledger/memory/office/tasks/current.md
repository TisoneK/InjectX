# Current Task (overwrite each session)

Holds exactly one task — the one being worked on right now.

- **Session:** Forge (OF01SS34) — **N18 Android app.** Phase 1 complete and **building green** on a real toolchain. At a checkpoint before the big scheme-porting phase.
- **Toolchain (installed this session, user-level, no sudo):** JDK 17.0.21 (Temurin) + Gradle 8.9 in `~/.local/toolchain/` (Intel mac). Build/test `:core`: `cd android && JAVA_HOME="$HOME/.local/toolchain/jdk-17.0.21+9/Contents/Home" ./gradlew :core:test`. Gradle wrapper is committed (`./gradlew` works on a fresh clone).
- **Done this session:** 31 verified golden fixtures (ASCII-safe names); Gradle scaffold; `Models.kt` (port of `ir/models.py`) **compiles**; `GoldenParityTest` **passes** (all 31 fixtures deserialize + match the Python backend). Commits `1f78661`, `62e5cc8` (product) + ledger commits.
- **Next up (Phase 2→5 — the port, each scheme vs its golden):** port `detector.py` → `core/detect/Detector.kt`; then crypto primitives + KeyStore; then the schemes **with golden coverage first — A5 (hc), B2 (ehi), H1 (ziv), I1 (dark)**; then `router.py` + `parse_engine.py`, extending `GoldenParityTest` to run the full Kotlin pipeline and assert `pipeline(source) == fixture.normalized`. See `android/TASKS.md`.
- **Blocked later (not now):** `:app` (UI/APK) needs the **Android SDK (API 34)** — deferred; only ~5 GB disk free, so adding the SDK (several GB) likely needs disk freed first. Schemes without samples (hat/npv/nsh/vhd/legacy hc-ehi) need samples added (**N3**) for golden coverage.
- Prior pending items (N3/N4, packaged-Electron confirmations) unchanged.
