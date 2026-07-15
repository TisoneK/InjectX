# Backlog (append-only)

Open items for future sessions. Append at the bottom; never delete or
reorder. When an item is done, check it off and note the session/commit —
don't remove the line.

<!-- TEMPLATE — copy below the last entry:
---
- [ ] **<short title>** (added YYYY-MM-DD by <agent>) — <enough context that
      a fresh agent can act on this without any chat history. Severity if known.>
-->

---
- [ ] **N1: Rewrite architecture doc to match v0.4** (added 2026-07-15 by Super Z) — `docs/InjectX-Architecture.md` is stale vs the v0.4 implementation. Says HAT/DARK/TLS have "no public decryptor" but code has working decryptors for HAT (scheme E1) and TLS (scheme F1); only DARK lacks a decryptor. Says EHI uses "base64 unlock" but code uses 2-stage AES (scheme B1). Lists `python-magic` in requirements but it's neither in `requirements.txt` nor imported. Either rewrite the doc to match v0.4 or mark it explicitly as "historical proposal — see code for actual architecture". Severity: nice to have (doc-only).
- [ ] **N2: Cross-platform setup guide** (added 2026-07-15 by Super Z) — `docs/setup-guide.md` is Windows-only (`C:\Projects\injectx`, `tasklist`, PowerShell examples) but the project works on Linux/Mac too (`frontend/main.js` already handles Linux venv path). Also references "InjectX v0.3.0" while the project is at v0.4.0. Rewrite to be cross-platform or split per-OS; update version refs. Severity: nice to have (doc-only).
- [ ] **N3: Add test infrastructure** (added 2026-07-15 by Super Z) — No `tests/` directory, no `conftest.py`, no `pyproject.toml [tool.pytest]`, no test runner config. The 7 format parsers and 7 decryptors have zero automated coverage — changes to crypto code are verified only by ad-hoc manual testing. Add `pytest` + `pytest-cov` + `ruff` + `mypy` to dev deps; add `tests/` with at least one happy-path test per format (using a known-good sample) and one negative test per format (malformed input). Severity: nice to have but high-leverage — this is the highest-value next session.
- [ ] **N4: Add GitHub Actions CI** (added 2026-07-15 by Super Z) — No `.github/workflows/`. Pushes to `main` are not validated. Add a minimal workflow running `pytest`, `ruff check`, `npm install` on every push/PR. Depends on N3. Severity: nice to have.
- [ ] **N5: Cap config_store size or persist to SQLite** (added 2026-07-15 by Super Z) — `config_store: dict[str, dict] = {}` in `backend/main.py` grows forever; no eviction, no max size. Each entry includes the full `decrypt_trace` (can be large — 21 attempts × multiple fields for a B1 scheme that fails on all keys). Long-running sessions parsing many configs will accumulate memory. Either (a) cap at N entries with LRU eviction, or (b) persist to SQLite (per architecture doc §10.2 — already planned for v2). Severity: nice to have for power users.
- [ ] **N6: Narrow bare `except Exception:` clauses in parser code** (added 2026-07-15 by Super Z) — 60+ bare `except Exception:` clauses in `backend/decrypt/` and `backend/parser/` swallow errors silently. In decrypt code this is intentional (try-many-keys pattern); leave as-is but add `logger.debug` calls. In parser code, narrow exception types (e.g., `except (KeyError, TypeError, json.JSONDecodeError):`) and log at `WARNING`. Broad refactor; flagged for a future session. Severity: nice to have (code quality).
- [ ] **N7: Implement documented env vars** (added 2026-07-15 by Super Z) — Architecture doc §11 documents `INJECTX_PORT`, `INJECTX_HOST`, `INJECTX_UPLOAD_DIR` env vars, but `backend/main.py` reads none of them (port/host hardcoded to `127.0.0.1:8742`, upload dir hardcoded to `~/.injectx/configs`). `NODE_ENV` IS implemented in `frontend/main.js` (for DevTools). Add env var reads with sensible defaults in `main.py`. Severity: nice to have (small change, useful for portable installs / port conflicts).
