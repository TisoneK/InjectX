# Session 25 — General Sweep (2026-07-26)

- **Agent:** GitHub Copilot / DeepSeek V4 Flash Free
- **Environment:** Local Windows (`$env:USERNAME=tison`, `C:\Users\tison\Dev\InjectX`)
- **Trigger:** `git pull --rebase origin main` pulled SNI Host Hunter Phase 1 (~53 files)
- **Baseline:** 91/91 tests pass, `ruff` clean, `main` branch

## What was done

### Phase 1-2: Setup & Review
- Verified deps installed, ran full test suite (91 pass), `ruff` clean
- Confirmed SNI Host Hunter code landed cleanly — no regressions
- Read full codebase state: `main.py`, `frontend/main.js`, `renderer.js`, `api.js`

### Phase 3: Stale-doc fixes (READ ME — 8 edits)
1. **Supported Formats table** — DARK: "None (proprietary)" → "Yes — scheme I1 (base64 JSON envelope)". Added ZIV (H1) and LNK rows. TLS updated to note key rotation. HC updated to mention A5 for v2.7+.
2. **Key Finding section** — DARK: "proprietary encryption, no public decryptor" → "base64 JSON envelope with optional DRM lock (scheme I1)". Added ZIV entry.
3. **Research Sources section** — DARK: "remains unsupported (proprietary encryption)" → "DARK (I1) decryptor is a native implementation". Added ZIV H1 as reverse-engineered from APK (Session 15). Noted TLS key rotation blockage.
4. **Project Structure tree** — Removed orphaned `dark_parser.py`. Added `ziv_parser.py`, `parse_engine.py`. Expanded `decrypt/` to list all 11 decryptors. Added `ziv/` and `lnk/` under `assets/configs/`.
5. **Opening line** — Added ZIV to the format list.
6. **`/api/formats` note** — `A1–G1` → `A1–I1`.

### Phase 3: Environment docs
- Added **Local Windows dev machine** block to `environments.md` — `$env:USERNAME=tison`, Python 3.13.1, PowerShell, verified commands, Windows-specific quirks (especially `python -m ruff` not working).

### Phase 4-5: Memory
- Updated `current.md` to point to this session.
- Logged two inefficiencies:
  1. README stale across 6+ sections (added a Pitfall suggestion for the protocol).
  2. `python -m ruff` fails on Windows venv (workaround recorded in environments.md).

## Files changed
- `README.md` — 8 corrections across 6 sections
- `.context/memory/system/environments.md` — Added Windows block
- `.context/memory/tasks/current.md` — Updated to reflect this session
- `.context/memory/inefficiencies/log.md` — Added 2 entries for this session

## Git status
- Clean working tree after changes. Ready to commit and push.

## Next up (unchanged)
- N15: SNI Host Hunter Phase 2 (sidebar UI, CertStream, ECH detection, etc.)
- User should confirm the Phase 1 feature in the packaged Electron app
