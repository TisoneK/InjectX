# Current Task (overwrite each session)

Holds exactly one task — the one being worked on right now.

- **Session:** Forge (OF01SS34) — **N18 Android app.** Design v3 (neon + real icon) shipped; **SNI Hunter two-phase functional rework shipped** (aecaa96). Next: device run + de-decorate Decode/SNI to neon v3.
- **Toolchain (user-level):** JDK 17.0.21 + Gradle 8.9 (`~/.local/toolchain/`) + Android SDK API 34 (`~/.local/android-sdk`, via `android/local.properties`). Build: `cd android && JAVA_HOME="$HOME/.local/toolchain/jdk-17.0.21+9/Contents/Home" ./gradlew :core:test` / `:app:assembleDebug`. Ship APK: `android/scripts/export-apk.sh`.
- **Done (base):** `:core` **7 green suites** (decrypt-layer H1/I1/A5/B2 + full-pipeline parity 31/31 + SNI logic). Full decode pipeline ported + golden-verified. APK install fix: minSdk 26→24; export-apk.sh re-signs **v1+v2+v3**; `android/dist/` git-tracked, latest versioned copy on Desktop.
- **Done (design v3 — this session):** Reversed the calm/gray pass per the user's critique. **Neon palette restored** (`Color.kt`: near-black green ground, #32E39B green + #45D6E8 cyan). **Real app icon is the ONE logo source** — `res/drawable/injectx_logo.png` (from `assets/icons/icon.png`); `HexLogo` renders it scaled everywhere, no per-screen redraws. `formatColor` covers all **9 formats**. Kept the plain-language tool descriptions + responsible-use disclaimer; one nav (hub-and-spoke, ADR-12). `:app:assembleDebug` green; APK `dist/injectx-debug-v0.1.0-6b3dc06.apk` on Desktop. Spec: `features/android-ui.md` §10. **Compile-verified only — not seen on a device.**
- **Done (SNI rework — this session, aecaa96):** all 12 of `features/android-ui.md` §11. Core (pure, `SniHunterTest` 12 green): `DomainInput` (one flexible input, clean/dedupe/count/skips), `HuntSession`+`HuntCodec` (two-phase, 3-state results, network labels, `pending()` resume, JSON round-trip), carriers + `loadBundled` removed, timeout-tagged probes, `Export.working()`. App: `HuntStore` (filesDir persistence), `NetworkStatus` (live chip), `SniScreen` two-step (Discover→handoff→Test, start/pause/resume, 3-state rows, export). Compile-verified only.
- **Next up:**
  1. **Runtime verification** — needs a device/emulator (not available here; UI + SNI network + persistence compile-verified only). This is now the biggest unknown.
  2. **De-decorate / align** Decode + SNI result components to the neon v3 look (SNI rows already use the neon palette; Decode result view still from the calm pass).
  3. **Empty-state output previews** (sample decoded result / "last scan" card).
  4. **SNI deferred niceties:** a saved/named seedlist *library* (§11.1 — currently per-hunt entry/import); probe concurrency (sequential now).
  5. **Release build** (Phase 8) — signing + release APK.
  6. **Sample-less schemes** (hat/npv/nsh/vhd/legacy/tls) — blocked on **N3** (add samples for goldens).
- Prior pending items (N3/N4, packaged-Electron confirmations) unchanged.
- **Housekeeping:** office is full (47 / 20 sessions) — `ledger-history close` is due before the next *fresh* check-in (not blocking this continued session).
