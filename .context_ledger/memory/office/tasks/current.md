# Current Task (overwrite each session)

Holds exactly one task — the one being worked on right now.

- **Session:** Forge (OF01SS34) — **N18 Android app.** Redesigned UI + Decode/SNI tabs; SNI Hunter screen wired to the ported logic.
- **Toolchain (user-level):** JDK 17.0.21 + Gradle 8.9 (`~/.local/toolchain/`) + Android SDK API 34 (`~/.local/android-sdk`, via `android/local.properties`). Build: `cd android && JAVA_HOME="$HOME/.local/toolchain/jdk-17.0.21+9/Contents/Home" ./gradlew :core:test` / `:app:assembleDebug`.
- **Done:** `:core` **7 green suites** (decrypt-layer H1/I1/A5/B2 + full-pipeline parity 31/31 + SNI logic). `:app` **redesigned Compose UI** (branded `ui/theme` + `ui/Brand.kt` hex logo; empty/loading/error/result states, status pills, format badges, copyable rows, expandable JSON) + **launcher icon** → `app-debug.apk` (13 MB) builds; APK + icon on `~/Desktop/`. **SNI Hunter core** in `core/sni/` (tested logic; `SniNetwork` compile-verified). Last commit 4d4b5cb.
- **Next up:**
  1. **SNI remainder:** defensive fronting probe (ADR-9), ECH/reverse-IP/port-check, CertStream; a "use this host as SNI" bridge from a scan result into a decoded config.
  2. **Runtime verification** of the app (needs a device/emulator — not available here; UI + SNI network are compile-verified only).
  3. **Release build** (Phase 8) — signing + release APK.
  4. **Sample-less schemes** (hat/npv/nsh/vhd/legacy/tls) — blocked on **N3** (add samples for goldens).
- Prior pending items (N3/N4, packaged-Electron confirmations) unchanged.
