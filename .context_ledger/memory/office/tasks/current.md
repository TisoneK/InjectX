# Current Task (overwrite each session)

Holds exactly one task — the one being worked on right now.

- **Session:** Forge (OF01SS34) — **N18 Android app, Phase 1.** BLOCKED on build environment (no JVM/Gradle/Kotlin/Android SDK on this host).
- **Done this session:** Golden-vector harness (`android/goldens/generate_goldens.py`) + **31 verified fixtures** from the real Python backend (A5/B2/H1 success, I1 partial, F1 known-failed). Gradle scaffold — `:core` (pure Kotlin/JVM lib, testable on a plain JDK) + `:app` (Android/Compose). Faithful port of `ir/models.py` → `core/.../model/Models.kt`. Golden parity test harness. `android/README.md` + `android/TASKS.md`. Committed `1f78661` (product) — **not yet built/compiled** (no toolchain).
- **Blocked on:** a Kotlin/Android build environment. Options for the user: (a) install JDK 17 + Android SDK locally so an agent builds+tests here; (b) run a cloud/sandbox session with the toolchain. Porting the 13 crypto schemes blind (no compiler, no golden tests runnable) is deliberately deferred — it would produce unverified crypto.
- **Next up (once a toolchain exists):** `android/TASKS.md` Phase 1 finish (`gradle wrapper`, `:core:test` green), then Phase 2 (detector) → Phase 4 (schemes, each vs its golden) → Phase 5 (parse engine) → Phase 6 (UI) → Phase 7 (SNI). Add samples for hat/npv/nsh/vhd/legacy formats (ties to **N3**) so those schemes get golden coverage. Prior pending items (N3/N4, packaged-Electron confirmations) unchanged.
