# InjectX — Android app (`android/`)

Native Android port of InjectX: pick a VPN tunnel config → detect format →
decrypt → show the normalized config; plus the SNI Host Hunter. Build plan,
architecture and scope are fixed by **ADR-10** and
`.context_ledger/memory/features/android-app.md`; tracked as backlog **N18**.

## ⚠️ Status — Phase 1, partially built

This scaffold was authored on a host with **no JVM / Gradle / Kotlin / Android
SDK**, so **no Kotlin here has been compiled, tested, or built into an APK.**
What IS verified: the golden-vector fixtures (`goldens/`), produced by running
the real Python backend. Treat all `.kt` / `.gradle.kts` as written-but-unbuilt
until a toolchain-equipped session (or Android Studio) compiles them.

Done so far:
- ✅ **Golden-vector fixtures** — `goldens/generate_goldens.py` + `goldens/fixtures/*.json` (31 fixtures, generated and verified against the Python backend).
- ✅ **Gradle project scaffold** — `:core` (pure Kotlin/JVM lib) + `:app` (Android/Compose).
- ✅ **Shared model** — `core/.../model/Models.kt`, a faithful port of `backend/ir/models.py`.
- ✅ **Golden parity test harness** — `core/.../GoldenParityTest.kt` (loads fixtures; contract check now, full parity once the pipeline lands).
- ⏳ **Not yet ported:** Detector, the 13 decrypt schemes, KeyStore, parse engine, SNI Hunter, the UI. See `TASKS.md`.

## Module layout

```
android/
├── settings.gradle.kts        :core + :app
├── build.gradle.kts           pinned plugin versions (ADR-10)
├── core/                      PURE Kotlin/JVM library — NO Android deps
│   ├── build.gradle.kts         Bouncy Castle, kotlinx-serialization, OkHttp, dnsjava
│   └── src/main/kotlin/com/injectx/core/
│       ├── model/Models.kt      ← backend/ir/models.py  (DONE)
│       ├── detect/              ← backend/parser/detector.py  (TODO)
│       ├── crypto/              ← backend/decrypt/*  (TODO: primitives, KeyStore, 13 schemes, router)
│       ├── parse/               ← backend/parser/*  (TODO)
│       └── sni/                 ← backend/snihunter/*  (TODO, Phase 7)
├── app/                       Android/Compose UI — the ONLY module needing the SDK
└── goldens/                   Python→fixture bridge (shared with :core tests)
```

**Why `:core` is pure Kotlin/JVM, not Android:** all crypto/parsing logic lives
there, so its unit + golden-vector tests run on a plain **JDK 17** with
`./gradlew :core:test` — no emulator, no Android SDK. Only `:app` (UI) needs the
SDK. This keeps the hard-to-verify crypto cheaply testable.

## Build requirements (none present on the authoring host)

- JDK 17
- Android SDK (API 34) + an Android Studio or command-line SDK install
- Gradle 8.9 — or just open `android/` in Android Studio, which provisions the
  wrapper. `gradle-wrapper.jar` is intentionally gitignored (can't be produced
  without Gradle); first step on a real host:
  `cd android && gradle wrapper --gradle-version 8.9`.

## First steps on a toolchain-equipped host

1. `cd android && gradle wrapper --gradle-version 8.9` (or open in Android Studio).
2. `./gradlew :core:compileKotlin` — fix any annotation nits in `Models.kt`.
3. `./gradlew :core:test` — the golden harness should load all fixtures green.
4. Work `TASKS.md` phase by phase; port each scheme against its golden fixture.
