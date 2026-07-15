# Current Task (overwrite each session)

Holds exactly one task — the one being worked on right now. Set it at
session start (protocol Step 3), clear it at session end (Step 15). If
you find a stale in-progress entry here, a prior session died mid-task —
check its session entry and backlog before starting.

- **Session:** idle — no task in progress.
- **Last session:** 2026-07-15 Session 11 (Claude Fable 5, local macOS) — **done.** General sweep. Added per-format parser smoke tests over all 32 bundled samples (suite 9→41, advances N3); fixed stale `/api/formats` (missing A5/B2 schemes + ziv/lnk formats, verified live); corrected a factually-wrong notes-iframe security comment. Re-verified ADR-1/5 path guard + ADR-2 CORS intact; backend dangerous-pattern scan clean. New backlog N8 (notes-iframe sandbox attr, blocked on Electron GUI verification). See `.context/memory/agents/sessions.md` Session 11 + `reviews/2026-07-15-review-4.md`.
