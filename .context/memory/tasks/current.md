# Current Task (overwrite each session)

Holds exactly one task — the one being worked on right now.

- **Session:** idle — no task in progress.
- **Last completed:** Session 24 (2026-07-23, Claude Code / Opus 4.8, local) — SNI Host Hunter Phase 1 (MVP), backlog N14. Shipped `backend/snihunter/` + 7 `/api/sni/*` endpoints + `sni` terminal commands + 37 tests (suite 54→91) + docs; ratified ADR-6/7/8; updated core 0.2.0→0.3.0. See `.context/memory/reviews/2026-07-23-feature-review.md`.
- **Next up:** N15 (SNI Host Hunter Phase 2 — sidebar UI module, "use as SNI", CertStream, ECH detection via RFC 9848, reverse-IP/port checks). Also: user should confirm the feature in the packaged Electron app (IPC registration + terminal DOM couldn't be verified headless on this machine).
