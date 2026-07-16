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

---
## 2026-07-15 — Session 3 (migration to core 0.2.0)

- **Agent:** Super Z | **Model:** unknown (GLM family) | **Platform:** Z.ai cloud sandbox — Debian 13 trixie, Python 3.12.13, Node v24.18.0 | **Role:** engineer
- **Task:** User reported "Context repo has been updated, pull and syncronize" — pulled the `TisoneK/.context` package repo (8 new commits, the 0.2.0 vendored-core release) and migrated InjectX's `.context/` from the 0.1.x flat layout to the 0.2.0 two-zone layout (vendored `core/` + `memory/`).
- **Commits:** 1 (`53838d0`) — `chore(context): migrate to core 0.2.0 two-zone layout`
- **Outcome:** done — zero data loss (every memory file moved via `git mv`, history preserved); `context-sync verify` passes; `memory/core.lock` records `version=0.2.0`. After this commit, future sessions need no package repo access — the protocol is vendored inside this repo at `.context/core/`.
- **Open items:** none new. Backlog N1-N7 still open from prior sessions.
- **Report:** no separate review report (migration session, not a code-review session). Migration details are in the commit message of `53838d0`.

---
## 2026-07-15 — Session 4

- **Agent:** Super Z | **Model:** unknown (GLM family; system prompt states "GLM model developed by Z.ai" without a specific version — recorded as `unknown` per the protocol's no-guess rule) | **Platform:** Z.ai cloud sandbox — Debian 13 trixie, Python 3.12.13, Node v24.18.0 | **Role:** engineer | **Core:** 0.2.0
- **Task:** User said "Clone https://github.com/TisoneK/InjectX.git and start AGENTS.md" — followed the `.context/kickoff.md` protocol (cloud/sandbox edition). Standing Target applied (general sweep — scan everything, fix safe issues).
- **Commits:** 8 product + 2 context = 10 total (`39c2dc7`..`ff7c1d1`). Product commits: 1 Medium frontend fix (INJECTX_PORT mismatch), 1 Medium audit fix (Pydantic v2 `.json()` → `model_dump_json()`), 4 Low fixes (unknown-protocol default, dialog filter, dead-code cleanup, typing.Any), 1 README alignment, 1 pyproject.toml. Context commits: 1 CHANGELOG (`docs:`), 1 review report (`docs(review):`). Plus this Phase 5 update (`chore(context):`).
- **Outcome:** done — found & fixed 2 Medium bugs (one silent IPC-breakage on custom ports, one silently-broken audit-log persistence path), 4 Low bugs, aligned the README with v0.4 reality, shipped test infra config (advances N3). All Session 1+2 security fixes re-verified on this fresh cloud env. 9/9 pytest passing; ruff clean; mypy informational.
- **Open items:** N1, N2, N3 (further advanced), N4, N5, N6 (partially advanced) in `tasks/backlog.md`. Recommended next: N4 (CI) is now the easiest win — `pyproject.toml` makes a `pytest && ruff check .` workflow trivial.
- **Report:** .context/memory/reviews/2026-07-15-review-3.md

---
## 2026-07-15 — Session 5
- **Agent:** Super Z | **Model:** unknown (GLM family; system prompt states "GLM model developed by Z.ai" without a specific version — recorded as `unknown` per the protocol's no-guess rule) | **Platform:** Z.ai cloud sandbox — Debian 13 trixie, Python 3.12.13, Node v24.18.0 | **Role:** engineer
- **Task:** User explicitly asked to focus on UI: "the ui is so basic almost non-functional. Redesign if possible make it complex and like a real hacking tool not a prototype that dsplays non-relevant information to the user. Why would the user want to know the backend workings and technical information?"
- **Commits:** 1 product (`64327e7`..`628a4a0`). Frontend-only: complete rewrite of `index.html`, `src/styles/main.css`, `src/scripts/renderer.js` as a tactical "CIPHER_OPS" interface. ~2100 insertions, ~1600 deletions across the three files.
- **Outcome:** done — Electron frontend redesigned end-to-end. New layout: 4 modules (Targets / Arsenal / Archive / System), status header with live UTC clock + marquee, sidebar with link/node/uplink telemetry, activity console with fake command-line (help/status/targets/clear/purge/about), boot sequence overlay with progress bar, scanline + vignette FX, animated radar empty-state. Backend internals hidden from the user surface: IR version, scheme IDs (A1–G1), decrypt trace (attempts / winning_scheme / key_label / elapsed_ms), decryptor source repos (HCTools/hcdecryptor, PANCHO7532/HCDecryptor), architecture diagram. Decryption status simplified to user-relevant tri-state: DECODED / LOCKED / UNKNOWN.
- **Smoke-tested with headless Chromium (Playwright):** all DOM elements render, all 4 views navigate correctly, no page errors, password fields masked by default (filter: blur(4px)), filter pills correctly exclude non-matching targets, DOM text scan confirms zero leakage of IR/scheme/trace/key-label/decryptor-source strings. Screenshots in `/home/z/my-project/download/injectx-ui-*.png`.
- **Open items:** none new. Functional scope (open/parse/list/delete/export) unchanged — only presentation layer changed. Backend, IPC bridge, preload, Electron main all untouched. Existing tests (9/9 pytest) still pass since no backend code was modified.
- **Report:** this session entry (no separate review file — UI-only change, no security/architecture implications).

---
## 2026-07-15 — Session 6
- **Agent:** Super Z | **Model:** unknown (GLM family) | **Platform:** Z.ai cloud sandbox | **Role:** engineer
- **Task:** User reported: "decipher failed terribly, we have a fancy and non-functional app. Logs are named as archive???? Also no live logs. We need to be able to read files content decrypt the bug host or sni and everything including server etc."
- **Commits:** 1 product (`989c8d5`..`91c1c84`). 12 files changed, 908 insertions, 43 deletions.
- **Outcome:** done — root-caused the HC decryption failure (legacy A1-A4 schemes don't work on HC v2.6+ files which use ChaCha20 + multi-layer encryption), reverse-engineered the new algorithm via web search (found ENIGMATIC-MAN/DECRYPTION_SCRIPTS), implemented as scheme A5 in new `backend/decrypt/hc_v27_decrypt.py`. All 3 user-provided real .hc files now decode successfully, extracting: host, port, ssh_server/user/pass, proxy_host/port, sni, payload (with [crlf]/[split] markers), notes (HTML), protections (hwid/area). Added live log streaming: backend writes real decrypt steps to in-memory buffer, frontend polls /api/logs every 250ms during decryption and streams entries into the activity console (24 entries per parse: "Applying initial XOR layer", "ChaCha20 outer envelope decrypt", "Main block decrypted · 32 fields", etc.). Renamed "Archive" module to "Logs". Added payload syntax highlighting ([crlf] violet, [split] amber, HTTP methods amber, Host: green). Notes HTML rendered in sandboxed iframe. All 9 existing tests pass. E2E test against real files passes with no page errors and no backend-internal leakage.
- **Open items:** none new. The A5 decryptor handles the new-format (cfg.content) and legacy-format (a.xy) v2.7 variants. Older HC files still fall back to A1-A4 via the router.
- **Report:** this session entry.

---
## 2026-07-15 — Session 7
- **Agent:** Super Z | **Model:** unknown (GLM family) | **Platform:** Z.ai cloud sandbox | **Role:** engineer
- **Task:** User asked: "For easier transport of real files why don't we have something like assets/... etc eg assets/configs/hc/ and other formats so that when i upload you get the files directly"
- **Commits:** 1 product (`373344c`..`e503ca2`). 19 files changed.
- **Outcome:** done — created `assets/configs/{format}/` directory tree (9 format subdirs + README + .gitkeep files), moved the 3 real .hc files from upload/ into assets/configs/hc/. Added backend endpoints: `GET /api/configs/assets` (list files in tree) and `POST /api/configs/import-assets` (batch-import all files). Added `INJECTX_AUTOIMPORT=1` env var for auto-import on startup. Added IMPORT ASSETS button to sidebar with live count badge (refreshed every 5s). Button streams real-time import logs to the activity console. Also fixed a pre-existing bug: format-specific normalizers were overwriting filepath/filename with empty strings — now filenames show correctly in /api/configs list and UI target cards. E2E verified: 3 files import in one click, all decode (scheme A5), no page errors, all 9 existing tests pass.
- **Open items:** none new.
- **Report:** this session entry.

---
## 2026-07-15 — Session 8
- **Agent:** Super Z | **Model:** unknown (GLM family) | **Platform:** Z.ai cloud sandbox | **Role:** engineer
- **Task:** User reported: "Rendering of decoded page is messed up i have to export the json to see results"
- **Commits:** 1 product (`f1abf6a`..`5a32bac`). 2 files changed, 92 insertions, 34 deletions.
- **Outcome:** done — root-caused 3 distinct rendering bugs in the detail view:
  1. **highlightPayload() bug**: `$&amp;` in regex replacement appended literal "amp;" to every [crlf]/[split] marker, producing "[crlf]amp;Host: [proxy]amp;amp;..." instead of "[crlf]Host: [proxy][crlf][crlf]...". Fixed to `$&`; also converted [crlf] → ↵ line breaks and [split] → full-width separator.
  2. **Notes iframe not rendering**: `sandbox="allow-same-origin"` blocked srcdoc content in some browsers. Removed sandbox attr; added auto-resize on iframe load event. Notes now render fully with colored fonts (verified: "R0meo" with colorful symbols visible).
  3. **Section ordering**: HTTP PAYLOAD was buried below PROXY/DNS/PROTECTIONS. Reordered to put it right after SSH CREDENTIALS. Added `min-height: 0` to `.detail-content` (flexbox gotcha).
  Also increased payload block max-height 320→480px, line-height 1.6→1.7.
- **Open items:** none.
- **Report:** this session entry.

---
## 2026-07-15 — Session 9
- **Agent:** Super Z | **Model:** unknown (GLM family) | **Platform:** Z.ai cloud sandbox | **Role:** engineer
- **Task:** User: "Pull changes i made in local repo, i added configs and icon you need to set icon for the app also for the taskbar icon and test new configs files i have added for other formats"
- **Commits:** 1 product (`1e1b271`..`7b8a0c2`). 18 files changed.
- **Outcome:** done — (1) App icon wired into Electron BrowserWindow + macOS dock + sidebar + titlebar. Added electron-builder config to package.json with per-platform icon paths. (2) Pulled user's new config files: 4 .dark, 7 .ehi, 7 new .hc, 2 .tls, 6 .ziv. (3) Added EHI v2 decryptor (scheme B2): reverse-engineered from ENIGMATIC-MAN — L1 AES-256-CBC + L2 AES-128-CBC + XXTEA + Argon2id + ChaCha20-Poly1305. All 6 .ehi files now decode (was 0/6). (4) Fixed EHI detector: was rejecting v2 binary format (\\x00\\x03ehi header) because it only accepted ZIPs. (5) Added ZIV format (scheme H1): AES-256-GCM + PBKDF2-SHA256. 6 .ziv files recognized; 0 decode (password rotated). (6) Fixed TLS parser: handles newer base64_payload::::: format. (7) Added argon2-cffi to requirements. Test results: HC 13/13 ✅, EHI 6/6 ✅ (NEW), DARK 0/4 (proprietary), TLS 0/2 (key rotated), ZIV 0/6 (password rotated). All 9 existing tests pass.
- **Open items:** TLS Tunnel and ZIVPN keys have been rotated in newer app builds — not yet publicly reversed. DARK remains proprietary with no public decryptor.
- **Report:** this session entry.

---
## 2026-07-15 — Session 10
- **Agent:** Super Z | **Model:** unknown (GLM family) | **Platform:** Z.ai cloud sandbox | **Role:** engineer
- **Task:** User: "You forgot .lnk files? I had to rename so that windows doesn't see it as a link rather a config file. Btw I have uploaded more icons targets will show their icons freely and users can now just know the type by looking at the file icon. Pull to get them delete screenshots too"
- **Commits:** 1 product (`b3f266b`..`00b493c`).
- **Outcome:** done — (1) Pulled user's per-format icons (dark.png, ehi.jpg, ha.jpg, hc.png, lnk.jpg, npv.png, ziv.png). Copied to frontend/src/assets/ for CSP-safe loading. Added createFormatIcon() helper that shows <img> with onerror fallback to text badge. Icons now appear on target cards (28px), detail view header (40px), and Arsenal cards (36px). (2) Added .lnk format: FormatEnum.LNK, detector extension map, ALLOWED_EXTENSIONS, CONFIG_EXTENSIONS, router (no schemes — NO_DECRYPTOR like DARK), assets/configs/lnk/ directory. (3) Deleted all test screenshots from download/. Verified: 31 target cards, 29 format icons load successfully (TLS has no icon), all 9 tests pass, no page errors.
- **Open items:** .lnk decryption algorithm not yet researched (format recognized, shows as LOCKED). TLS and ZIV keys still rotated.
- **Report:** this session entry.

---
## 2026-07-15 — Session 11
- **Agent:** Claude Code | **Model:** claude-fable-5 (Claude Fable 5; exact ID from system prompt) | **Platform:** local macOS (Darwin 24.6.0), Python 3.9.6, Node v24.17.0 | **Role:** engineer | **Core:** 0.2.0
- **Task:** General sweep (standing default) — first local-agent review since Session 2 (Sessions 3–10 were all cloud). Re-verify security fixes, review the accumulated un-locally-reviewed surface (UI redesign, HC v2.7/EHI v2/ZIV decryptors, assets tree, .lnk/icons), fix safe issues, push to main, write report.
- **Commits:** 5 (`653e5bf`..`db1c736`) — 3 product (1 test, 1 fix(api), 1 docs(ui) comment) + 1 review report (`docs(review):`) + 1 changelog (`docs:`). Plus this Phase 5 context log (`chore(context):`).
- **Outcome:** done — no new Critical/High. (1) Added per-format parser smoke tests over all 32 bundled samples → suite 9→41 (advances N3). (2) Fixed stale `/api/formats` (missing A5/B2 schemes + ziv/lnk formats), verified live. (3) Corrected a factually-wrong notes-iframe security comment (srcdoc is NOT auto-isolated; the inherited CSP is the real protection). Re-verified ADR-1/ADR-5 path-traversal guard + ADR-2 CORS intact; dangerous-pattern scan of backend clean. Synced local venv (was missing argon2-cffi since Session 9).
- **Open items:** N1, N2, N4, N5, N6 (unchanged); N3 substantially advanced (parser tests done; decryptor asserts + F401/mypy remain); **N8 new** (notes-iframe sandbox attr — blocked on Electron GUI verification, as is the Session 4 `webPreferences sandbox:true` note). See `tasks/backlog.md`.
- **Report:** .context/memory/reviews/2026-07-15-review-4.md

---
## 2026-07-15 — Session 12
- **Agent:** Claude Code | **Model:** claude-fable-5 (Claude Fable 5; exact ID from system prompt) | **Platform:** local macOS (Darwin 24.6.0), Python 3.9.6 | **Role:** engineer | **Core:** 0.2.0
- **Task:** User (chat target): "Only the hc decryption works e2e. Fix other files' algorithms if possible, research online, make major files work not just hc. Did we add HA Tunnel (hat)?" Audit real per-format decode status, fix what's fixable, research the rest online.
- **Commits:** 4 product/report (`374c797`..`71f9d0a` + report `docs(review)` + changelog `docs`) — 1 fix(decrypt) TLS padding, 1 chore cleanup, 1 docs changelog, 1 docs(review) report. Plus this Phase 5 context log (`chore(context):`).
- **Outcome:** done — **Corrected the premise:** a full-pipeline probe shows EHI decodes 6/6 (scheme B2), not "only HC." So HC 13/13 + EHI 6/6 both work e2e. Fixed a real TLS base64-padding bug (`374c797`) that made TLS bail before the key loop with an empty trace. Researched TLS + ZIV against the authoritative public decryptors (HCDecryptor on GitLab; EstebanZxx/X-Tools) — InjectX already carries their exact keys/passwords, which MAC-fail because newer app builds rotated the secrets (confirmed by a 256-combo ZIV sweep). TLS/ZIV are therefore blocked on external key material, not wrong algorithms; DARK is proprietary. HAT (scheme E1) is fully implemented but has zero `.hat` samples → unverified. Removed a stray `universal-kickoff.md` from the HC samples dir. 41/41 tests pass.
- **Open items:** N9 (EHI shows empty in UI — frontend, needs GUI), N10 (HAT unverified — needs a real `.hat` sample), N11 (TLS/ZIV blocked on rotated keys — no code fix). N1–N6, N8 unchanged.
- **Report:** .context/memory/reviews/2026-07-15-review-5.md

---
## 2026-07-15 — Session 13
- **Agent:** Claude Code | **Model:** claude-fable-5 (Claude Fable 5; exact ID from system prompt) | **Platform:** local macOS (Darwin 24.6.0), Python 3.9.6 | **Role:** engineer | **Core:** 0.2.0
- **Task:** Continuation of Session 12. User: "So we do what is possible for now?" + side Q on WPA `.cap` 4-way handshake. Ship the achievable in-house-key-supply piece (no APKs needed): make extracted keys loadable at runtime.
- **Commits:** 2 product/docs (`29628d9` feat, `+` changelog `docs`). Plus this Phase 5 context log (`chore(context):`) and review report (`docs(review):`).
- **Outcome:** done — `feat(decrypt)` (`29628d9`): wired `INJECTX_KEYFILE` → `get_router()` → `KeyStore._load_keyfile()`, which was dead code (parse_config called `get_router()` with no path, so no runtime key supply existed). Extracted keys now drop in via a JSON keyfile merged over defaults; TLS + HAT fully keyfile-driven. Added `docs/key-extraction.md` (static jadx + dynamic Frida recipes + keyfile format). +2 tests (suite 41→43), ruff clean. Answered the `.cap` side question: it's WPA-PSK cracking (hashcat -m 22000), a separate 802.11/pcap domain, not part of the config decryptors — logged as a scope decision, not implemented.
- **Open items:** N12 (new — route ZIV/HC-v27/EHI-v2 inline constants through KeyStore so the keyfile covers ZIVPN too). N9/N10/N11 unchanged from Session 12.
- **Report:** .context/memory/reviews/2026-07-15-review-6.md

---
## 2026-07-15 — Session 14
- **Agent:** Claude Code | **Model:** claude-fable-5 (Claude Fable 5; exact ID from system prompt) | **Platform:** local macOS (Darwin 24.6.0), Python 3.9.6 | **Role:** engineer | **Core:** 0.2.0
- **Task:** User: "Our focus is getting algorithms for all the files." Systematic per-format algorithm audit; fill the real gaps.
- **Commits:** 2 product/docs (`ac2eed1` feat, `+` changelog `docs`). Plus this Phase 5 context log (`chore(context):`) and review report (`docs(review):`).
- **Outcome:** done — **Cracked DARK Tunnel**, which every prior session wrongly called "proprietary encryption, no decryptor." A `.dark` file is `darktunnel://base64(JSON)`: type/name/transport are plaintext, only the optional `encryptedLockedConfig` (author DRM lock) is sealed. Shipped scheme **I1** (`decrypt/dark_decrypt.py`) — tolerant base64→JSON, PARTIAL+warning when locked, SUCCESS when not; wired router/normalizer/`/api/formats`; fixed the router to keep PARTIAL payloads; removed the orphaned never-imported `dark_parser.py`. 4/4 DARK samples now decode (protocol+name+transport). +5 tests (43→48). Produced a full per-format algorithm inventory (review-7): works now = HC/EHI/DARK; algorithm-present-but-key-rotated = TLS/ZIV; algorithm-present-but-no-sample = HAT/NPV/NSH/VHD; unknown = LNK.
- **Open items:** N13 (new — samples for NPV/NSH/VHD/HAT + identify LNK). N9/N10/N11/N12 unchanged. Remaining formats are blocked on inputs I don't have (real samples, or current TLS/ZIV keys), not on missing algorithms.
- **Report:** .context/memory/reviews/2026-07-15-review-7.md

---
## 2026-07-15 — Session 15
- **Agent:** Claude Code | **Model:** claude-fable-5 (Claude Fable 5; exact ID from system prompt) | **Platform:** local macOS (Darwin 24.6.0), Python 3.9.6 | **Role:** engineer | **Core:** 0.2.0
- **Task:** Extract the rotated ZIVPN key from the app APK and make `.ziv` decode (user supplied the ZIVPN Tunnel v2.1.5 XAPK).
- **Commits:** 3 product/docs (`f6e91d8` feat + changelog `docs` + this Phase 5 `chore(context)` + review `docs(review)`).
- **Outcome:** done — **CRACKED ZIVPN: `.ziv` now decodes 6/6 (was 0/6).** The 5-session "key rotated, unfixable" verdict was wrong. Static-analyzed the APK with androguard (no JVM — `/usr/bin/java` is a stub so jadx couldn't run; pip-installed androguard instead). Config importer `o3.a.<clinit>` builds the password from five base64 constants → `SecurePart1..SecurePart5` concatenated; `u3.c`/`v3.b` = BouncyCastle PKCS5S2 PBKDF2 (1000 iters, 16-byte key) + AES-GCM over salt.iv.ct. InjectX's H1 algorithm was already exactly right — only the password was stale — so adding it fixed all 6. Also mapped UDP-mode fields (udpserver→host: udpsg3/udpsg4.zivpn.com), +6 tests (48→54). First-half of session: automated APK download failed (mirror anti-bot), user supplied the XAPK.
- **Open items:** N11 — ZIV half DONE; TLS half open (same method, needs the com.tlsvpn.tlstunnel APK). N12/N13 unchanged.
- **Report:** .context/memory/reviews/2026-07-15-review-8.md

---
## 2026-07-15 — Session 16
- **Agent:** Claude Code | **Model:** claude-fable-5 (Claude Fable 5; exact ID from system prompt) | **Platform:** local macOS (Darwin 24.6.0), Python 3.9.6 | **Role:** engineer | **Core:** 0.2.0
- **Task:** Extract the current TLS Tunnel `.tls` AES-GCM key from the app APK (user supplied TLS Tunnel v8.0.6, com.tlsvpn.tlstunnel), same method as ZIVPN.
- **Commits:** 1 doc (`docs` key-extraction packer caveat) + this Phase 5 `chore(context)` + review `docs(review)`. No product code change (no key recovered).
- **Outcome:** blocked — **TLS Tunnel 8.0.6 ships DexProtector** (`libdexprotector.so`), a commercial packer that encrypts the app's own strings/classes at runtime, defeating static extraction. Enumerated every AES/GCM/SecretKeySpec reference in all 4 dex — all were unprotected ad SDKs (Digital Turbine Ignite `Lhm`, Conscrypt `Lo30`, Google Tink, Mintegral), none the config crypto; no com.tlsvpn class references the crypto directly. Brute-forced 148,232 strings (dex + all .so) × 5 key derivations against a sample — no hit. TLS's F1 algorithm is still correct; only the (runtime-only) key is missing. Path forward: dynamic Frida on a rooted device/emulator (needs the user's device; not runnable here). Contrast: ZIVPN had no packer, so it cracked; TLS is deliberately hardened.
- **Open items:** N11 (TLS) reclassified — blocked on dynamic Frida (device), not on the APK. N12/N13 unchanged.
- **Report:** .context/memory/reviews/2026-07-15-review-9.md

---
## 2026-07-16 — Session 17
- **Agent:** Claude Code | **Model:** claude-fable-5 (Claude Fable 5; exact ID from system prompt) | **Platform:** local macOS (Darwin 24.6.0), Python 3.9.6 | **Role:** engineer | **Core:** 0.2.0
- **Task:** UI refinement (user paused decode work). "Decoded page is messed up, I have to export JSON." Then: move activity log to the right + redesign the output.
- **Commits:** 2 product/docs (`6d09419` feat(ui) + changelog `docs`) + this Phase 5 `chore(context)` + review `docs(review)`.
- **Outcome:** done — Ran the app e2e to diagnose: (1) the user's app was on a STALE backend (the screenshot's EHI showed FAILED, but a fresh backend decodes EHI 6/6, HC 13/13, ZIV 6/6, DARK 4/4 — a restart fixes it); (2) even on success the detail view rendered near-empty because formats like EHI/ZIV keep their data in `raw_data._all_fields`, unmapped to IR slots (an EHI showed 1 row despite 21 fields). Shipped `feat(ui)`: activity log → 340px right dock (`.work-area` flex); output redesign — compact status strip, hero tiles (host/port/protocol), 2-col card grid, full-width "DECODED FIELDS" table (all extracted fields), notes pick up `configMessage`/`file.msg`, and fixed a latent `.hidden` bug (raw-JSON never collapsed). Verified in-browser vs real HC/EHI configs; no console errors.
- **Open items:** N9 RESOLVED (all decoded fields now visible). User should restart the app for the current backend. N10/N11/N12/N13 unchanged.
- **Report:** .context/memory/reviews/2026-07-16-review.md
