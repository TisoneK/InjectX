# Current Task (overwrite each session)

Holds exactly one task — the one being worked on right now.

- **Session:** idle — no task in progress.
- **Last completed:** Session 28 (2026-07-24, Claude Code / Opus 4.8, local) — SNI Host Hunter **Phase 3 (defensive mode)**, backlog N16. Shipped `backend/snihunter/defensive.py` (`probe_fronting`: SNI/Host-mismatch domain-fronting probe + TLS-cert fingerprint comparison + `classify_fronting` verdict), `POST /api/sni/fronting`, `sni fronting <sni> <host>` terminal command, 15 tests (suite 151→166). Ratified ADR-9. Also fixed pulled test-infra breakage (`710890d`, pytest-asyncio). **SNI Host Hunter is now feature-complete (all 3 phases).** See `.context/memory/reviews/2026-07-24-phase3-review.md`.
- **Next up:** N17 (expose the fronting probe in the sidebar UI — Phase 3 is terminal + API only). Also pending USER confirmations in the packaged Electron app: (a) Phase 2 sidebar module (Session 26), (b) Phase 3 `sni fronting` terminal command (Session 28), (c) `npm run dist` after the fast-uri override (Session 27). N3/N4 (pin dev deps + CI) remain high-leverage.
