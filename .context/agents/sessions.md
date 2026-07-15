# Agent Sessions (append-only)

One entry per agent session, newest at the bottom. Never edit or delete
past entries — append corrections instead.

<!-- TEMPLATE — copy below the last entry:
---
## YYYY-MM-DD — Session N
- **Agent:** <name> | **Model:** <model id> | **Platform:** <machine/sandbox + OS> | **Role:** <engineer, or overlay from the protocol package's roles/>
- **Task:** <what this session set out to do>
- **Commits:** <count> (<first-sha>..<last-sha>)
- **Outcome:** <done / partial / blocked — one line>
- **Open items:** <pointers into tasks/backlog.md, or "none">
- **Report:** .context/reviews/YYYY-MM-DD-review.md
-->

---
## 2026-07-15 — Session 1
- **Agent:** Super Z | **Model:** unknown (GLM family; system prompt states "GLM model developed by Z.ai" without a specific version — recorded as `unknown` per the protocol's no-guess rule) | **Platform:** Z.ai cloud sandbox — Debian 13 trixie, Python 3.12.13, Node v24.18.0 | **Role:** engineer
- **Task:** General sweep — discover InjectX, review all focus areas, fix safe issues, flag architectural ones, push to main, write `.context/reviews/` report.
- **Commits:** 0 (bootstrap commit pending below)
- **Outcome:** in-progress
- **Open items:** none yet — first session
- **Report:** .context/reviews/2026-07-15-review.md (to be written)

---
## 2026-07-15 — Session 1 (end-of-session update)

The bootstrap entry above was written prematurely at Step 1b (before any
work was done) — kept intact per the append-only rule. The actual session
outcome:

- **Commits:** 9 (`23ea9cf`..`c90fafb`) — 1 bootstrap + 7 fixes + 1 review report + 1 CHANGELOG
- **Outcome:** done — 1 critical security fix (path traversal in /parse and /detect), 1 high (CORS wildcard+credentials), 2 medium (upload validation, route shadowing of /detect and /export), 3 low (Pydantic v2 .dict() deprecation, print()→logging, stale package-lock.json). 7 nice-to-have items flagged in backlog.
- **Open items:** 7 backlog items (N1–N7): rewrite architecture doc, cross-platform setup guide, add test infrastructure, add CI, cap config_store, narrow bare excepts, implement env vars. See `tasks/backlog.md`.
- **Report:** .context/reviews/2026-07-15-review.md

---
## 2026-07-15 — Session 2
- **Agent:** Claude Code | **Model:** claude-fable-5 (Claude Fable 5; exact ID from system prompt) | **Platform:** local macOS (Darwin 24.6.0), Python 3.9.6, Node v24.17.0 | **Role:** engineer
- **Task:** General sweep — first local-agent session. Discover on a fresh local env, re-verify Session 1's security fixes, review the untested parser/decrypt surface, fix safe issues, push to main, write report.
- **Commits:** 6 (`3d12269`..`6f4533e`) — 3 project fixes (1 High security, 2 Low) + 1 changelog + 1 review report + (this) context log
- **Outcome:** done — Found & fixed a **High-severity symlink bypass** that reopened Session 1's C1 path-traversal fix (`_validate_config_path` checked the link's extension but not the resolved target's; `evil.ehi -> /etc/passwd` read arbitrary files). Fix `3d12269` + 8 regression tests. Also: CORS loopback origins now track `INJECTX_PORT` (`b08043b`), Pydantic `json_encoders` → `field_serializer` (`5665cd7`). All Session 1 fixes re-verified live on macOS/Py3.9. N7 confirmed done; N3 partially advanced (tests/ now has 9 tests).
- **Open items:** N1, N2, N3 (partial), N4, N5, N6 in `tasks/backlog.md`. New ADR-5 (resolved-extension re-check). Recommended next: finish N3 (per-format parser/decryptor tests + pytest/ruff/mypy config), then N4 (CI).
- **Report:** .context/reviews/2026-07-15-review-2.md
