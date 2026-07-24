# Current Task (overwrite each session)

Holds exactly one task — the one being worked on right now.

- **Session:** idle — no task in progress.
- **Last completed:** Session 26 (2026-07-24, Super Z cloud) — **N15 done.** Shipped SNI Host Hunter Phase 2: 5 new backend modules (`dns_check.py` ECH via RFC 9848, `sources/certstream.py`, `reverseip.py`, `portcheck.py`, `apply.py` "use as SNI"), 5 new `/api/sni/*` endpoints, sidebar "05 · SNI HUNTER" module (config panel + live results table + verdict pills + per-row action buttons), 60 new tests (suite 91→151, ruff clean). All endpoints curl-verified + Node harness drove the real `api.js` against the live backend. `dnspython` added. See `reviews/2026-07-24-phase2-review.md`.
- **Next up:** N16 (SNI Host Hunter Phase 3 — defensive mode: ISP zero-rating enforcement verification, nDPI-style SNI/Host-header mismatch, TLS fingerprint comparison). Also: user should confirm the Phase 2 sidebar module in the packaged Electron app (DOM rendering + IPC handlers — couldn't verify headless in the cloud sandbox). Optional: `pip install certstream` to enable the WATCH button / `sni watch` terminal command.
