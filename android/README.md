# InjectX — Android app (`android/`)

Native Android port of InjectX: pick a VPN tunnel config → detect format →
decrypt → show the normalized config; plus the SNI Host Hunter. Build plan,
architecture and scope are fixed by **ADR-10** and
`.context_ledger/memory/features/android-app.md`; tracked as backlog **N18**.

## Status — Phase 1 built & green (`:core`)

A user-level JDK 17 + Gradle 8.9 toolchain is installed (`~/.local/toolchain`),
and **`:core` compiles and `:core:test` passes** — the golden harness verifies
all 31 fixtures deserialize into the Kotlin model and match the Python backend.
The `:app` (Android/Compose) module is **not yet built**: it needs the Android
SDK (API 34), which this host lacks the disk headroom for (~5 GB free).

Done so far:
- ✅ **Golden-vector fixtures** — `goldens/generate_goldens.py` + `goldens/fixtures/*.json` (31 fixtures, generated and verified against the Python backend; ASCII-safe names).
- ✅ **Gradle project** — `:core` (pure Kotlin/JVM lib) + `:app` (Android/Compose). Wrapper committed (`./gradlew` works on a fresh clone).
- ✅ **Shared model** — `core/.../model/Models.kt`, faithful port of `backend/ir/models.py`. **Compiles.**
- ✅ **Golden parity test** — `core/.../GoldenParityTest.kt`, **passing** (contract check now; full pipeline-vs-golden parity once the pipeline lands).
- ⏳ **Not yet ported:** Detector, the 13 decrypt schemes, KeyStore, parse engine, SNI Hunter, the UI. See `TASKS.md`.

Build & test `:core` (no Android SDK needed):

```bash
cd android
JAVA_HOME="$HOME/.local/toolchain/jdk-17.0.21+9/Contents/Home" ./gradlew :core:test
```

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
