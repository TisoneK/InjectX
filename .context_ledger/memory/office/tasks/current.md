# Current Task (overwrite each session)

Holds exactly one task — the one being worked on right now.

- **Session:** Forge (OF01SS34) — **N18 Android app.** Verified decode core + Compose UI now build into a debug APK.
- **Toolchain (user-level, no sudo):** JDK 17.0.21 + Gradle 8.9 in `~/.local/toolchain/`; Android SDK (API 34, build-tools 34.0.0, platform-tools) in `~/.local/android-sdk` (Gradle finds it via `android/local.properties`, gitignored). Build: `cd android && JAVA_HOME="$HOME/.local/toolchain/jdk-17.0.21+9/Contents/Home" ./gradlew :core:test` (logic) or `:app:assembleDebug` (APK).
- **Done:** `:core` 6 green suites (decrypt-layer H1/I1/A5/B2 + full-pipeline parity 31/31). **`:app` Compose UI** (SAF pick → `ParseEngine.parseConfig` → render + export) **assembles → app-debug.apk (13 MB)**. Last commit 036836e.
- **Next up:**
  1. **Runtime verification** — install/run the APK on a device or emulator (NOT possible on this host: no emulator, ~4 GB disk free, Intel). The UI code compiles + links against the verified core but its behaviour is unconfirmed.
  2. **Release build** (Phase 8) — signing config + release APK.
  3. **SNI Host Hunter (Phase 7)** — portable to `:core` (OkHttp/dnsjava); network code, so unit-test logic + manual network checks.
  4. **Sample-less schemes** (hat/npv/nsh/vhd/legacy/tls) — **blocked on N3** (add samples for goldens); primitives mostly already in `Primitives.kt`.
- Prior pending items (N3/N4, packaged-Electron confirmations) unchanged.
