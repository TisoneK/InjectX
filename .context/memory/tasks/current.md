# Current Task (overwrite each session)

Holds exactly one task — the one being worked on right now.

- **Session:** idle — no task in progress.
- **Last session:** 2026-07-16 Session 22 (Claude Fable 5, local macOS) — **done.** Folder import + IDE-style remember-last-folder (`cb71d75`). Electron main: persisted `settings.json` (userData: lastDir/lastFolder), `open-folder-dialog`, `list-config-files` (fs scan by CONFIG_EXTENSIONS), get/set-last-folder; file dialog defaults to + records the last dir. Renderer: `importFolder()`/`openFolder()`, sidebar **Open Folder** button, terminal `targets openfolder` + `targets import <folder>` (folder = last path segment has no dot), and a startup **reopen-last-folder** (silent re-import — backend store is memory-only so it restores the working set). Verified in-browser with mocked Electron APIs (dialog/fs/settings are main-process, not preview-testable): `targets import "<folder with spaces>"` → 3/3, reopen re-imports 3, button wired, no console errors. **Confirm in packaged app:** native folder dialog defaults to last location; settings.json persists; last folder reopens on next launch. See `reviews/2026-07-16-review-6.md`.
