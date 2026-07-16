# Current Task (overwrite each session)

Holds exactly one task — the one being worked on right now.

- **Session:** idle — no task in progress.
- **Last session:** 2026-07-16 Session 21 (Claude Fable 5, local macOS) — **done.** Terminal/assets fixes (`f1f6dbe`): (1) Terminal COPY/CLEAR toolbar buttons + per-line copy. (2) Quoted-arg tokenizer + path-aware `targets info/debug` (`resolveOrParse` parses a filesystem path fresh via backend if not a loaded target) + new `targets pick` (native file dialog) — the exact failing screenshot command `targets info "C:\...\Airtelke (3).hc"` now works. (3) Assets are dev-only: the 31 "assets" came from the sidebar Import Assets button (NOT auto-import — main.js sets no INJECTX_AUTOIMPORT); exposed `app.isPackaged` as `isDev` (IPC→preload→api) and hid the Import Assets button in the packaged app. Verified in-browser; no console errors. `targets pick` + isDev-hide are Electron-main paths (verified by logic/syntax; confirm in packaged app). See `reviews/2026-07-16-review-5.md`.
