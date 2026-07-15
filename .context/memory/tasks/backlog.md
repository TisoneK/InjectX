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
- [x] **N7: Implement documented env vars** (added 2026-07-15 by Super Z) — Architecture doc §11 documents `INJECTX_PORT`, `INJECTX_HOST`, `INJECTX_UPLOAD_DIR` env vars, but `backend/main.py` reads none of them (port/host hardcoded to `127.0.0.1:8742`, upload dir hardcoded to `~/.injectx/configs`). `NODE_ENV` IS implemented in `frontend/main.js` (for DevTools). Add env var reads with sensible defaults in `main.py`. Severity: nice to have (small change, useful for portable installs / port conflicts). **DONE — commit `8ce5782` (Session 1, post-log) added all three with `test_env_config.py`; verified live Session 2. Follow-up `b08043b` (Session 2) made the CORS loopback origins track `INJECTX_PORT` too.**

---
## Session 2 progress notes (2026-07-15, Claude Fable 5) — append-only

- **N3 partially advanced:** `backend/tests/` now holds `test_env_config.py` (Session 1) + `test_path_validation.py` (Session 2, 8 tests). Still open: `pyproject.toml [tool.pytest]` config, `ruff` + `mypy` setup, `.github/workflows/` CI (N4), and per-format parser/decryptor coverage with sample files. N3 stays open until the parser/decryptor suite exists.
- **Fold into N6 when tackled:** two cosmetic nits in `backend/parser/parse_engine.py` found Session 2 — (a) `_apply_field_map` annotates `dict[str, any]` using the builtin `any` instead of `typing.Any` (~lines 207–208; harmless at runtime, `mypy` would flag it); (b) `_normalize` sets `decryption_status = NOT_ENCRYPTED` for the EHI-unencrypted branch (~line 95) which is then unconditionally overwritten at ~line 112 — dead assignment, final value is still correct. Not worth separate commits; fix during the N6 pass.
- **New hardening recommendation:** `_validate_config_path` has now been the site of two related traversal issues (C1 Session 1 + S2-1 symlink bypass Session 2). A property/fuzz test over path shapes (encoded, symlink chains, `..`, device files) would harden it against a third. See `reviews/2026-07-15-review-2.md` §7.
