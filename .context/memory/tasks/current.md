# Current Task (overwrite each session)

Holds exactly one task — the one being worked on right now. Set it at
session start (protocol Step 3), clear it at session end (Step 15). If
you find a stale in-progress entry here, a prior session died mid-task —
check its session entry and backlog before starting.

- **Session:** idle — no task in progress.
- **Last session:** 2026-07-15 Session 14 (Claude Fable 5, local macOS) — **done.** Focus: algorithms for all formats. **Cracked DARK Tunnel** — every prior session wrongly called it "proprietary, no decryptor"; a `.dark` file is actually `darktunnel://base64(JSON)` with type/name/transport in plaintext and only the optional `encryptedLockedConfig` (author DRM lock) sealed. Shipped scheme **I1** (`decrypt/dark_decrypt.py`, commit `ac2eed1`): 4/4 DARK samples now decode; router keeps PARTIAL payloads; orphaned `dark_parser.py` removed; `/api/formats` updated; +5 tests (48 total). Produced a full per-format algorithm inventory (`reviews/2026-07-15-review-7.md`): **works now** = HC/EHI/DARK; **algorithm present, key rotated** = TLS/ZIV (need a current key — `INJECTX_KEYFILE` path exists from Session 13); **algorithm present, no sample** = HAT/NPV/NSH/VHD; **unknown** = LNK. New backlog N13 (samples for NPV/NSH/VHD/HAT + identify LNK). Remaining formats are blocked on inputs (real samples or current keys), not missing algorithms. See `.context/memory/agents/sessions.md` Session 14.
