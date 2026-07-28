# Current Task (overwrite each session)

Holds exactly one task — the one being worked on right now.

- **Session:** idle — no task in progress.
- **Last completed:** Session 30 (2026-07-28, GitHub Copilot) — **Fixed `pyproject.toml` pip install.** Added `[build-system]`, `[project]`, and `[tool.setuptools.packages.find]` with explicit package include list so `pip install -e .` succeeds. Added `*.egg-info/` to `.gitignore`. Commit `78d012a`.
- **Next up:** No SNI Hunter follow-ons remain (feature complete). Highest-leverage open items: **N3/N4** (pin dev deps + CI — would prevent the "passes in sandbox, fails in clean env" recurrences from Sessions 11 + 28). Also pending USER confirmations in the packaged Electron app: (a) Phase 2 sidebar module (Session 26), (b) `npm run dist` after fast-uri override (Session 27), (c) Phase 3 `sni fronting` terminal command (Session 28), (d) Session 29's defensive panel.
