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

---
## 2026-07-16 — Session 18
- **Agent:** Claude Code | **Model:** claude-fable-5 (Claude Fable 5; exact ID from system prompt) | **Platform:** local macOS (Darwin 24.6.0), Python 3.9.6 | **Role:** engineer | **Core:** 0.2.0
- **Task:** User (Windows) shared `sample_results.zip` — "only HC works as desired" — and asked for copy icons on logs + fields (server/host/proxy).
- **Commits:** 3 (`3335c71` fix(api) export + `629ee42` feat(ui) copy buttons + changelog `docs`) + this Phase 5 `chore(context)` + review `docs(review)`.
- **Outcome:** done — Root-caused "only HC works" from the exports: (1) `/api/config/export` DROPPED `raw_data`, and HC is the only format that maps data to top-level IR fields — HTTP Injector/ZIVPN/DARK keep it in `raw_data._all_fields`, so their exports came out near-empty. Fixed the export to keep raw_data (minus debug keys); ZIV export now 24 fields, EHI 21, DARK its name/type. (2) The user's EHI shows FAILED because their Windows backend venv is missing `argon2-cffi` (B2 needs it) — env, not code (EHI decodes 6/6 here); told them to reinstall deps. Added copy-to-clipboard buttons (⧉) on hero tiles, all field values, and log lines (Clipboard API + execCommand fallback). 54/54 tests, ruff clean, verified in-browser. Left the user's untracked `electron-builder` bump in package.json/lock untouched.
- **Open items:** N10/N11/N12/N13 unchanged. Optional: promote more EHI/ZIV app fields to top-level IR (deferred).
- **Report:** .context/memory/reviews/2026-07-16-review-2.md

---
## 2026-07-16 — Session 19
- **Agent:** Claude Code | **Model:** claude-fable-5 (Claude Fable 5; exact ID from system prompt) | **Platform:** local macOS (Darwin 24.6.0), Python 3.9.6 | **Role:** engineer | **Core:** 0.2.0
- **Task:** 7-item UI polish batch: Terminal module, collapsible activity log, local (not UTC) time, other UI-inconsistency fixes, close-confirmation dialog, sticky detail header + footer.
- **Commits:** 3 (`90129c6` feat(app) close dialog + `f78f35b` feat(ui) UI batch + changelog `docs`) + this Phase 5 `chore(context)` + review `docs(review)`.
- **Outcome:** done — all 7 shipped. Terminal module (sidebar 04, shared `runCommand`); collapsible log dock (340↔34px); clock UTC→local; status-header cells `flex-shrink:0` so labels don't clip; Electron close dialog (`dialog.showMessageBoxSync` + `isQuitting` flag); sticky `.detail-header` (top) + `.detail-actions` (bottom) — removed `.detail-content` vertical padding so they sit flush (fixed a content-bleed sliver caught in the first pass). Verified in-browser vs real HC config (terminal runs, collapse toggles, local clock, sticky no-bleed, no console errors); `node --check` clean. Close dialog is Electron-main-only — code-reviewed + syntax-checked, user to confirm in packaged app.
- **Open items:** N10/N11/N12/N13 unchanged. User reminders: reinstall backend deps on Windows (argon2-cffi) for EHI; restart app for current backend.
- **Report:** .context/memory/reviews/2026-07-16-review-3.md

---
## 2026-07-16 — Session 20
- **Agent:** Claude Code | **Model:** claude-fable-5 (Claude Fable 5; exact ID from system prompt) | **Platform:** local macOS (Darwin 24.6.0), Python 3.9.6 | **Role:** engineer | **Core:** 0.2.0
- **Task:** (1) Logs page copy button; (2) redesign the cramped/non-functional Arsenal page; (3) big feature — a realistic terminal command system with namespaced args.
- **Commits:** 2 (`f99fe9b` feat(ui) + changelog `docs`) + this Phase 5 `chore(context)` + review `docs(review)`.
- **Outcome:** done — All three shipped in one cohesive frontend commit (interleaved across index.html/renderer.js/main.css). Terminal: replaced flat CONSOLE_COMMANDS with a namespaced parser/dispatcher (`runCommand` + `CMD` tree) shared by the terminal + activity-log via IO surfaces, aligned-table output; commands `targets list/info/open/debug/export/purge/import/count`, `logs`, `system`, `assets import`; target resolution by id/filename with ambiguity detection; `debug` caps the trace table at 20 rows. Arsenal: live dashboard (summary strip + accurate status pills + live LOADED·DECODED counts + click-to-filter via new `state.formatFilter`). Logs: COPY LOG button + per-entry copy + shared `copyText()`. Verified in-browser vs 31 real targets (injected list + mocked getConfig due to CORS); tables align, ambiguity/unknown handling works, arsenal click-filters hc→13, no console errors.
- **Open items:** N10/N11/N12/N13 unchanged. Terminal follow-ups noted in review (history/tab-completion/keyfile add).
- **Report:** .context/memory/reviews/2026-07-16-review-4.md

---
## 2026-07-16 — Session 21
- **Agent:** Claude Code | **Model:** claude-fable-5 (Claude Fable 5; exact ID from system prompt) | **Platform:** local macOS (Darwin 24.6.0), Python 3.9.6 | **Role:** engineer | **Core:** 0.2.0
- **Task:** From a terminal screenshot: (1) terminal has no copy button; (2) assets used as source of truth (dev-only); (3) terminal centered on assets, not the user's files — `targets info "<windows path>"` failed.
- **Commits:** 2 (`f1f6dbe` feat(ui) + changelog `docs`) + this Phase 5 `chore(context)` + review `docs(review)`.
- **Outcome:** done — Root cause of the failing command: the arg tokenizer split on whitespace (broke the quoted path) AND info/debug only searched loaded targets. Fixes: quoted-arg `tokenize()`; `resolveOrParse()` so `targets info/debug` accept a filesystem path (parsed fresh via backend if not loaded); new `targets pick` opens the native file dialog; terminal COPY/CLEAR toolbar + per-line copy. Also: the 31 "assets" were NOT auto-loaded (main.js sets no INJECTX_AUTOIMPORT) — they came from the sidebar Import Assets button; exposed `app.isPackaged` as `isDev` and hid that button in the packaged app (dev-only sample fixtures). Verified in-browser: the exact screenshot command now parses the Windows path and prints host/port/etc.; copy buttons present; assets button hides when isDev=false; no console errors.
- **Open items:** N10/N11/N12/N13 unchanged. Note: `targets pick` + isDev-hide are Electron-main paths, verified by logic/syntax; confirm in packaged app.
- **Report:** .context/memory/reviews/2026-07-16-review-5.md

---
## 2026-07-16 — Session 22
- **Agent:** Claude Code | **Model:** claude-fable-5 (Claude Fable 5; exact ID from system prompt) | **Platform:** local macOS (Darwin 24.6.0), Python 3.9.6 | **Role:** engineer | **Core:** 0.2.0
- **Task:** Folder import + IDE-style "remember the last folder / reopen last project."
- **Commits:** 2 (`cb71d75` feat(app) + changelog `docs`) + this Phase 5 `chore(context)` + review `docs(review)`.
- **Outcome:** done — Electron main: a persisted `settings.json` (userData) with lastDir/lastFolder, `open-folder-dialog`, `list-config-files` (fs scan by CONFIG_EXTENSIONS), get/set-last-folder; file dialog now defaults to + records last dir. Renderer: `importFolder()`/`openFolder()`, a sidebar Open Folder button, terminal `targets openfolder` + `targets import <folder>` (folder = no dot in last segment), and a startup reopen-last-folder (silent re-import, since the backend store is memory-only). Verified in-browser with mocked Electron APIs: `targets import "<folder with spaces>"` → 3/3; reopen re-imports 3; button wired; no console errors. Native dialog/fs/settings run in Electron main — flagged for confirmation in the packaged app.
- **Open items:** N10/N11/N12/N13 unchanged. Follow-ups (review-6): recursive folder scan; guard double-import if backend gains persistence (N5).
- **Report:** .context/memory/reviews/2026-07-16-review-6.md

---
## 2026-07-24 — Session 23
- **Agent:** Super Z | **Model:** unknown (GLM family; system prompt states "GLM model developed by Z.ai" without a specific version — recorded as `unknown` per the protocol's no-guess rule) | **Platform:** Z.ai cloud sandbox — Debian 13 trixie, Python 3.12.13, Node v24.18.0 | **Role:** engineer | **Core:** 0.2.0
- **Task:** User (chat target): "Project: https://github.com/TisoneK/InjectX.git. Read .context/kickoff.md and follow it. Target: Feature - SNI HOST HUNTER. Do more research and save the context." The user supplied a GitHub PAT inline (cloud session). The user also supplied a comprehensive initial SNI Host Analysis System document (Sections 1-5 covering core architecture, discovery methodologies, ISP detection patterns, defensive mitigations, research resources) — the session's job was to deepen that research and save the augmented context.
- **Commits:** 1 .context-only commit (`docs(review)` for the report + `chore(context):` for memory updates — see below). No project code (research-only session per user request).
- **Outcome:** done — research + design context saved as `.context/memory/features/sni-host-hunter.md` (13 sections, ~30k words). Augmented the user's initial research with 7 parallel web searches + 3 page reads: discovered BugScanX (`pddung93/BugScanX`, the closest existing competitor with 8 menu items), SNIbugtester (`Praveenhalder/SNIbugtester`, Android app with the best reference UX), confirmed certstream-python is maintained, verified ECH has graduated from "proposal" to published RFC 9849 (March 2026) with OpenSSL 4.0 + NGINX support landed, and grounded the African ISP context (Safaricom/Airtel Free Basics, Telkom zero-rated portals, public bug-host lists on Techfoe/aimtuto/snihost.com). The design doc covers: rationale, primer, domain research summary, InjectX integration analysis (backend modules, frontend changes, parallel IR design, ADR compliance, test infra), MVP vs Full Vision, full implementation plan with pseudo-code for `backend/snihunter/` package + crt.sh source + async prober + job store + 7 API endpoints + terminal commands, legal/ethical considerations (dual-use reality, design decisions biasing toward legitimate use, ADR-6 proposal), test strategy, 5 open questions for the user, proposed ADR-6 (loopback-bound, ≤200 concurrency, no IP-range scanning), 30+ primary references, research provenance, and explicit "what this session did NOT do" boundary. Phase 1 (MVP) implementation is a separate session's job — backlog entry N14 added pointing at the design doc.
- **Open items:** N14 new (SNI Host Hunter Phase 1 implementation — next session). N1-N13 unchanged. Implementing session should read the design doc in full, ratify ADR-6, answer the open questions in §9, then execute Phase 1 per §6.5.
- **Report:** .context/memory/reviews/2026-07-24-review.md
- **Patron reminder:** the user pasted a GitHub PAT in plaintext in chat (cloud session). It was used only for `git clone` + `git push` and was stripped from `.git/config` immediately per protocol. The PAT should be ROTATED after this session — it has been visible in chat history. Reminded the user in the final chat summary.

---
## 2026-07-23 — Session 24
- **Agent:** Claude Code | **Model:** claude-opus-4-8 (Claude Opus 4.8; exact ID from system prompt) | **Platform:** local macOS (Darwin 24.6.0), Python 3.9.6, Node v24.17.0 | **Role:** feature-engineer | **Core:** 0.3.0 (updated from 0.2.0 this session)
- **Task:** User (chat): "Pull changes, initialize context protocol and handle sni bug host hunter feature as documented and do more research online." → implement **SNI Host Hunter Phase 1 (MVP)**, backlog N14, per `features/sni-host-hunter.md` §6.5, plus an online-research refresh.
- **Commits:** 6 product/docs (`9063184` feat backend, `a7ea22e` test, `41a9922` feat ui, `8f88424` docs, `defc297` changelog — pushed `cde8cc5..defc297`) + 3 `chore(context)` (`c7bd057` core→0.3.0, `e7f612f` ADR-6/7/8, + this Phase-5 log) + `docs(review)` report.
- **Outcome:** done — Phase 1 shipped and verified. New `backend/snihunter/` package (crt.sh + seedlist discovery, async TLS/HTTP/DNS prober with a pure `classify_http` verdict fn, in-memory job store, txt/csv/json export), 7 `/api/sni/*` endpoints + `_validate_seedlist_path` (mirrors ADR-5) + `INJECTX_ENABLE_SNI_HUNTER` kill switch, bundled Safaricom/Airtel/Telkom-KE seedlists + `portal_indicators.txt`, `sni` terminal command tree routed via Electron IPC (ADR-7, NOT the doc's renderer-fetch), 37 new tests (suite 54→**91**, ruff clean), README + architecture §13 + changelog. Ratified ADR-6 (loopback-bound, conc cap 200, dedupe, no IP-range), ADR-7 (IPC not fetch), ADR-8 (in-tree public seedlists). Also updated core 0.2.0→0.3.0 (harvest release; no migration). Verified end-to-end: pytest 91, ruff clean, live curl of every endpoint (scan→working/dead verdicts, export, stop, 400/403/413 error paths, crt.sh error+success paths), a Node harness driving the real `api.js` against the live backend (caught+fixed a bare-hostname arg-routing bug), and `node --check` on all JS. `httpx` added; `dnspython` deferred to Phase 2.
- **Open items:** **N14 done**; **N15 new** (Phase 2 — sidebar UI module, "use as SNI", CertStream, ECH detection via RFC 9848 HTTPS-RR, reverse-IP/port checks, portal-indicator tuning). Needs USER confirmation in the packaged Electron app (IPC registration + terminal DOM — this machine can't launch Electron headless). N1 partially advanced (architecture §13 added, older sections flagged pre-v0.4). N2/N3/N4/N5/N6/N10/N11/N12/N13 unchanged.
- **Report:** .context/memory/reviews/2026-07-23-feature-review.md
- **Note:** no PAT to rotate (local agent, user's own credentials). Date is `date -u`=2026-07-23; Session 23 (cloud) was logged 2026-07-24 because its sandbox clock ran a day ahead — so Session 24 sorts *before* Session 23 by date. ADR-6/7/8 + feature-doc keep the 2026-07-24 label for continuity with the design.

---
## 2026-07-24 — Session 26
- **Agent:** Super Z | **Model:** unknown (GLM family; system prompt states "GLM model developed by Z.ai" without a specific version — recorded as `unknown` per the protocol's no-guess rule) | **Platform:** Z.ai cloud sandbox — Debian 13 trixie, Python 3.12.13, Node v24.18.0 | **Role:** engineer | **Core:** 0.3.0
- **Task:** User (chat): "Pick up Phase 2". Implement N15 (SNI Host Hunter Phase 2) per `features/sni-host-hunter.md` §5.2/§6.5.
- **Commits:** 3 product/docs + 1 `chore(context)` (pushed to main — see review §6).
- **Outcome:** done — Phase 2 shipped and verified. Five new backend modules: `dns_check.py` (ECH detection via RFC 9848 DNS SVCB/HTTPS-RR — queries HTTPS RR, falls back to SVCB, extracts `ech=` param, base64-validates), `sources/certstream.py` (real-time CT watch via optional `certstream` dep — 503 if absent), `reverseip.py` (HackerTarget free API + PTR fallback), `portcheck.py` (TCP connect probe, 80/443/8080/8443 default, ADR-6 cap of 32), `apply.py` ("use as SNI" — re-parse from disk, override `sni`, preserve original under `raw_data._original_sni`, patch all SNI-alias keys in `_all_fields`, audit warning). Five new `/api/sni/*` endpoints all gating on `INJECTX_ENABLE_SNI_HUNTER`. Sidebar "05 · SNI HUNTER" module: config panel (seedlist dropdown + FIND via crt.sh + WATCH via CertStream + concurrency/timeout/cloudflare-only knobs) + live results table with verdict pills (working/redirect/blocked/dead) for click-to-filter + per-row action buttons (Use as SNI / ECH / PORTS / REV-IP). 60 new tests (suite 91→151, ruff clean). `dnspython` added to requirements. Verified end-to-end: pytest 151, ruff clean, self-contained Python script curled every endpoint (success + error + kill-switch paths, ECH on crypto.cloudflare.com = capable, apply on TelkomNet.ehi preserves `myaccount.telkom.co.ke` as original), Node harness drove real `api.js` `API.sni.*` against live backend, `node --check` all JS. Notable: the first ECH implementation missed real ECH records because `str(ParamKey.ECH)` returns "5" not "ech" — caught by live verification against `crypto.cloudflare.com`, fixed by matching on `k.name.lower()`. **Needs USER confirmation in the packaged Electron app** (sidebar DOM rendering + IPC handler registration — cloud sandbox can't launch Electron headless). Optional: `pip install certstream` to enable WATCH.
- **Open items:** N16 new (Phase 3 — defensive mode: ISP zero-rating enforcement verification, nDPI-style SNI/Host-header mismatch, TLS fingerprint comparison). N1-N14 unchanged (N1 architecture doc further advanced by §13.2/§13.6 updates). N3/N4 still the highest-leverage open items.
- **Report:** .context/memory/reviews/2026-07-24-phase2-review.md
- **Note:** no PAT to rotate (the user's own git credentials are used via the local agent's `credential.helper` pattern from Session 4; the cloud sandbox's PAT from Session 23 should already have been rotated).

---
## 2026-07-26 — Session 27
- **Agent:** Super Z | **Model:** unknown (GLM family) | **Platform:** Z.ai cloud sandbox — Debian 13 trixie, Python 3.12.13, Node v24.18.0 | **Role:** engineer | **Core:** 0.3.0
- **Task:** User (chat) forwarded the dependabot alert: "fast-uri vulnerable to host confusion via literal backslash authority delimiter" (high severity, GHSA on fast-uri <=3.1.3). Fix it.
- **Commits:** 1 product (`fix(deps)`) + 1 `chore(context)`.
- **Outcome:** done — closed the alert. Added an npm `overrides` block to `package.json` forcing `fast-uri` to `^3.1.4`. `npm audit` now 0 vulnerabilities (was 1 high). Surgical: +3 lines package.json, 3 lines lockfile (version 3.1.3→3.1.4, resolved URL, integrity hash). Assessment: `fast-uri` is a build-time-only transitive dep (`electron-builder → app-builder-lib → ajv@^8.18.0 → fast-uri@^3.0.1`); InjectX's runtime code (Python httpx backend + Electron main-process fetch) doesn't use `fast-uri` or `ajv` at all, so the practical runtime risk was zero — this was supply-chain hygiene, not a live vuln. Considered bumping `electron-builder` to 26.15.7 (latest) but verified that doesn't fix it (ajv 8.20.0 still pins `^3.0.1` which resolves to 3.1.3). The override is the dependabot-recommended fix and stays in the 3.x line (no major-version risk). Verified: `npm install` clean, `npm audit` 0 vulns, `node --check frontend/main.js` OK, backend 151 tests still pass. **Not verified:** `npm run dist` (packaging) — sandbox can't produce a Windows/macOS installer; user should run it once locally.
- **Open items:** none new. User confirmations still pending from prior sessions: (a) Phase 2 sidebar module in packaged Electron app (Session 26), (b) `npm run dist` still works after the fast-uri override (this session). N16 (Phase 3) still next up.
- **Report:** .context/memory/reviews/2026-07-26-deps-review.md

---
## 2026-07-24 — Session 28
- **Agent:** Claude Code | **Model:** claude-opus-4-8 (Claude Opus 4.8; exact ID from system prompt) | **Platform:** local macOS (Darwin 24.6.0), Python 3.9.6, Node v24.17.0 | **Role:** feature-engineer | **Core:** 0.3.0
- **Task:** User (chat): "Pull and continue phase 3." → pulled (Sessions 26/27 had landed: Phase 2 + a fast-uri dependabot fix), then implemented **SNI Host Hunter Phase 3 (defensive mode)**, backlog N16, per `features/sni-host-hunter.md` §5.2/§3.5.
- **Commits:** 6 product/docs (`710890d` fix(test), `0115835` feat backend, `26aaa40` test, `6c19b9d` feat ui, `a570817` docs, `c0124e8` changelog — pushed `67f67d1..c0124e8`) + 2 `chore(context)` (`f79c263` ADR-9 + this Phase-5 log) + `docs(review)` report.
- **Outcome:** done — Phase 3 shipped and verified. `backend/snihunter/defensive.py` `probe_fronting(sni, host)` answers all three N16 angles in one probe: SNI/Host-header mismatch (domain-fronting) test via **raw HTTP-over-TLS** (httpx couples SNI+Host, so raw asyncio+ssl decouples them; `host` sanitised against CRLF injection), TLS-cert fingerprint comparison across SNIs (`cert_changes_with_sni`), and a pure `classify_fronting` verdict (`enforced` 421 / `bypassable` 2xx-3xx / `indeterminate` / `error`). `SniFrontingResult`+`FrontingVerdict` models, `POST /api/sni/fronting` (gates on `INJECTX_ENABLE_SNI_HUNTER`), `sni fronting <sni> <host>` terminal command via the IPC chain (ADR-7). 15 tests (suite 151→**166**, ruff clean). Ratified **ADR-9** (single-target, read-only, non-exploitative — a detector not an exploiter, not wired into the ADR-6 scan machinery). Verified live: curl (cloudflare-vs-example mismatch → cert changes + 403 not-served; wikipedia same-tenant → bypassable 301; invalid host → 400; dead SNI → error) + a Node harness driving real `api.js` `API.sni.fronting`. **Also fixed inherited breakage:** the pulled Session-26 async tests used `@pytest.mark.asyncio` with pytest-asyncio unpinned + the marker unregistered, so `--strict-markers` broke collection in a clean venv — fixed with `asyncio_mode="auto"` (`710890d`).
- **Open items:** **N16 done**; **N17 new** (expose the fronting probe in the sidebar UI — Phase 3 is terminal+API only). Needs USER confirmation in the packaged Electron app (IPC registration + terminal DOM). Two prior confirmations still pending: Phase 2 sidebar (Session 26), `npm run dist` after fast-uri override (Session 27). N1-N15 unchanged.
- **Report:** .context/memory/reviews/2026-07-24-phase3-review.md
- **Note:** no PAT to rotate (local agent, user's own credentials). **Date reconciliation:** session began late 2026-07-23 UTC (core.lock verify stamped 07-23) and crossed midnight into 2026-07-24 (`date -u`). Session 27 (cloud) is logged 2026-07-26 — its sandbox clock ran ~2 days ahead. I briefly inherited "07-26" in ADR-9 + current.md before checking `date -u`, then corrected all my artifacts to the honest 2026-07-24. So Session 28 (07-24) sorts before Session 27 (07-26) by date — trust `date -u`, not the cloud sessions' skewed dates.

---
## 2026-07-24 — Session 29
- **Agent:** Super Z | **Model:** unknown (GLM family) | **Platform:** Z.ai cloud sandbox — Debian 13 trixie, Python 3.12.13, Node v24.18.0 | **Role:** engineer | **Core:** 0.3.0
- **Task:** User (chat): "Okay go ahead" → continue with N17 (the current-task "Next up" line) per the established feature-progression pattern. N17 = expose the Phase 3 defensive fronting probe in the sidebar UI.
- **Commits:** 1 product/docs (`feat(ui)`) + 1 `chore(context)` (pushed to main).
- **Outcome:** done — N17 shipped. Frontend-only session: the IPC/preload/api plumbing for `sni-fronting` was already in place from Session 28, so this session built the DOM + renderer + CSS. New "DEFENSIVE PROBE — FRONTING" panel at the bottom of the 05 · SNI Hunter module (below the scan-config/results two-column layout): two inputs (SNI + Host) + PROBE button, a color-coded verdict banner (green=enforced, red=bypassable, amber=indeterminate, muted=error) with a one-sentence blurb per verdict, a 2-column detail grid rendering all 11 fields the backend's `probe_fronting` returns (SNI→Host, HTTP status, server header, TLS handshake, both cert CNs, cert-changes-with-SNI, host-covered-by-cert, DNS consistency, target IP, elapsed), and the backend's notes as a bulleted list. `state.sni.fronting` preserves the last result across view switches; `renderSniHunterView()` re-renders it on return. ~110 new CSS lines using the existing CIPHER_OPS variables, with a violet accent to visually distinguish the defensive surface from the green offensive scan surface. Design choice: a separate panel (not a per-result-row button) because ADR-9 frames fronting as a distinct defensive capability and the probe takes two free-form hostnames, not one. Verified: `node --check` all JS, backend 166 tests unchanged, Node harness drove real `api.js` `API.sni.fronting()` against live backend (cloudflare-vs-example mismatch → indeterminate/403/cert-changes-true; wikipedia same-tenant; empty-SNI error path). **Needs USER confirmation in the packaged Electron app** (DOM rendering + button wiring). **SNI Host Hunter is now feature-complete across all 3 phases + the full UI surface.**
- **Open items:** none new. No SNI Hunter follow-ons remain (feature complete). Highest-leverage open items: N3/N4 (pin dev deps + CI). User confirmations still pending: (a) Phase 2 sidebar (S26), (b) `npm run dist` after fast-uri (S27), (c) Phase 3 `sni fronting` terminal (S28), (d) this session's defensive panel (S29).
- **Report:** .context/memory/reviews/2026-07-24-n17-review.md
- **Note:** no PAT to rotate (cloud sandbox; the Session 23 PAT should already have been rotated). Date is `date -u`=2026-07-24 — consistent with Session 28's reconciliation (the cloud clock skew from Sessions 23/27 is documented; this session used the honest UTC date).

---
## 2026-07-28 — Session 30
- **Agent:** GitHub Copilot | **Model:** DeepSeek V4 Flash Free | **Platform:** Windows 11 — local dev machine, Python 3.10+ via `.venv`, git | **Role:** engineer | **Core:** 0.3.0
- **Task:** "Fixed. Read kickoff.md and push the changes" — after user fixed `pip install -e .` failure (pyproject.toml missing build-system/project sections).
- **Commits:** 1 (`78d012a`) — `fix(build): add pyproject.toml build-system and package discovery config`
- **Outcome:** done — added `[build-system]` (setuptools.build_meta), `[project]`, and `[tool.setuptools.packages.find]` with explicit package include list to `backend/pyproject.toml`. Also added `*.egg-info/` to `.gitignore`. `pip install -e .` now succeeds.
- **Open items:** none new. Highest-leverage: N3/N4 (CI + dev deps). Same pending user confirmations as Session 29.
- **Report:** no separate review (single-commit fix).

---
## 2026-08-01 — Session 31
- **Agent:** Buffy (Freebuff) | **Model:** deepseek-v4-flash (exact ID from system prompt) | **Platform:** local macOS (Darwin 24.6.0), Python 3.9.6, Node v24.17.0 | **Role:** engineer | **Core:** 0.5.0 (updated from 0.3.0 this session)
- **Task:** User (chat target): "Start kickoff.md Target: Sync .context then initialize InjectX" — (1) sync `.context/`: pull + update vendored core + regenerate kickoff/AGENTS from new templates; (2) initialize InjectX: deps check, baseline health, live backend boot verification.
- **Commits:** 1 context (`2c831ab` chore(context): update core to 0.5.0) + this Phase-5 `chore(context)` log. No product code.
- **Outcome:** done — pulled clean (fast-forward), updated core 0.3.0→0.5.0 (same MAJOR; 0.4.0 added Windows `context-sync.ps1`, 0.5.0 added the `memory/sessions/` module + session-data-is-disposable principle + Step 17 context promotion), verified integrity, regenerated `.context/kickoff.md` + `AGENTS.md` from the materially-changed templates (facts unchanged; placeholder scan clean). **InjectX initialized and healthy:** venv + node_modules present/current (fastapi 0.128.8, pydantic 2.13.4, pytest-asyncio, ruff, mypy all in); baseline **166/166 pytest pass**, ruff clean, `node --check` clean on all 4 JS files; live boot on `INJECTX_PORT=8799` served `/api/health` (`v0.4.0`), `/api/formats`, `/api/sni/seedlists`, and decoded a real HC sample (`bypass.hc`, scheme A5, success). First session on core 0.5.0 — created `memory/sessions/` (README/SUMMARY/notes per the new module).
- **Open items:** none new. N3/N4 (dev deps pinning + CI) remain highest-leverage. Pending USER confirmations unchanged (packaged-app checks: Phase 2 sidebar S26, `npm run dist` S27, `sni fronting` terminal S28, defensive panel S29).
- **Report:** no separate review file (sync/initialize session, no product code).
- **Notes:** .context/memory/sessions/2026-08-01-31/notes.md
- **Note:** no PAT to rotate (local agent, user's own credentials). `date -u`=2026-08-01.

---
## 2026-08-03 — Session 33
- **Agent:** Buffy (Freebuff) | **Model:** openai/gpt-5.6-luna | **Platform:** local macOS — Darwin 24.6.0, `/Users/bao/Code/InjectX` | **Role:** engineer | **Core:** 0.5.0
- **Task:** User target: "Start `.context/kickoff.md` Target: Session 31 implementation" — verify whether Session 31 implementation remains complete and re-run its initialization path.
- **Commits:** 1 report + 1 context commit (to be created); no product code.
- **Outcome:** done — Session 31 was already complete. Origin/main and core 0.5.0 are current; core integrity, 166 tests, Ruff, four frontend syntax checks, and npm audit all pass. Live backend recheck served health, 11 formats, 3 seedlists, and parsed the bundled HC sample successfully. No implementation gaps or new findings.
- **Open items:** N3/N4, packaged Electron confirmations, and documented format/sample/key follow-ups remain unchanged in `tasks/backlog.md`.
- **Report:** `.context/memory/reviews/2026-08-03-review-2.md`
- **Notes:** none
- **Note:** no PAT to rotate (local agent, user's own credentials). `date -u`=2026-08-03.

---
## 2026-08-03 — Session 32
- **Agent:** Buffy (Freebuff) | **Model:** openai/gpt-5.6-luna | **Platform:** local macOS — Darwin 24.6.0, `/Users/bao/Code/InjectX` | **Role:** engineer | **Core:** 0.5.0
- **Task:** User target: "Pull changes, sync context and initialize the project" — followed `.context/kickoff.md`, pulled `main`, verified the vendored core, initialized context state, and ran the project baseline.
- **Commits:** pending at session-log write; context-only changes will be committed separately as `chore(context):`.
- **Outcome:** done — `git pull --ff-only` already current; core verify/status clean at 0.5.0; 166 pytest tests passed, Ruff clean, four JS syntax checks passed, npm audit found 0 vulnerabilities. No product code changed.
- **Open items:** N3/N4 remain the highest-leverage backlog items; packaged Electron confirmations remain pending as listed in `tasks/current.md`.
- **Report:** `.context/memory/reviews/2026-08-03-review.md`
- **Notes:** none

---
## 2026-11-13 — Session 34
- **Agent:** Forge | **Model:** claude-opus-4-8 | **Platform:** local macOS — Darwin 24.6.0, `/Users/bao/Code/InjectX` | **Role:** engineer | **Core:** 2.3.3 (MIGRATED from 0.5.0 this session)
- **Task:** User asked (1) whether InjectX could become a mobile app + be monetized "per decryption"; then (2) "build android app" — chose native Kotlin rewrite + decrypt & SNI in v1; then (3) "document plan in context so another agent can see it — first upgrade context ledger."
- **Commits (this session, local — see push note):** `a91d711` migrate core 0.5.0→2.3.3 + office grouping · `33138ef` rename .context/→.context_ledger/ + refresh facts · `e8343d5` add ledger-guard Claude Code hooks · `0595473` log push-check/rename flaw · (pending) this memory batch (android-app.md, ADR-10, N18, this entry, current.md, STATE.md). No product code.
- **Outcome:**
  - **Mobile/monetization advice:** mobile app is technically feasible (rewrite, not port). Advised AGAINST a "pay-per-decryption" model — app-store bans on carrier-control circumvention, DMCA-style anti-circumvention exposure for breaking locked configs, telecom-ToS/fraud risk in target markets, and payment-processor termination risk. User set monetization aside; kept the Android build.
  - **Ledger upgrade 0.5.0 → 2.3.3** (the user's "first" step): `ledger-sync update --major` then `migrate` (crossed 0.18 dir rename, 1.0 office grouping, 2.0 router/STATE, 2.1 hooks, 2.3.x). Memory grouped into `memory/office/`; `.context/`→`.context_ledger/` via `ledger-sync rename`; forward-looking memory config/docs swept to the new path (historical reports + append-only logs left verbatim); `active.md` facts refreshed (core 2.3.3, upstream `context-ledger.git`, `chore(ledger):` prefix, `office/reviews/` path); `kickoff.md` `context-sync`→`ledger-sync`; `AGENTS.md` schema ref `context-schema.md`→`ledger-schema.md`; `ledger-guard install` added 3 git hooks + `.claude/settings.json`; `STATE.md` generated; core verifies, lock=2.3.3.
  - **Android plan documented:** `features/android-app.md` (full spec), **ADR-10** (native Kotlin, decrypt+SNI v1, `android/` monorepo module, golden-vector parity harness; Chaquopy rejected; monetization out of scope), backlog **N18**.
- **Open items / push note:** **NOT YET PUSHED.** The migration range includes the rename commit `33138ef`, which `push-check` flags as two-surface (deletes `.context/`=product, adds `.context_ledger/`=ledger) — an unavoidable one-time rename the guard can't model (flaw logged `flaws/log.md`). The sanctioned fix (`LEDGER_GUARD_SKIP=1 git push`) was blocked by the Claude Code auto-mode classifier as "undermining oversight." Needs the USER to either approve that skip-push or run `LEDGER_GUARD_SKIP=1 git push origin main` themselves. Prior open items (N3/N4, packaged-Electron confirmations) unchanged.
- **Report:** no separate review file (advisory + ledger-migration + planning session; no product code).
- **Notes:** First session on core 2.x. Codename self-assigned (no roster check-in; exit-check skips cleanly with no live row). `date -u`=2026-11-13.

---
## 2026-11-13 — Session 34 (continued: N18 Android build, Phase 1)
- **Agent:** Forge | **Codename:** OF01SS34 | **Model:** claude-opus-4-8 | **Platform:** local macOS — Darwin 24.6.0, `/Users/bao/Code/InjectX` | **Role:** engineer | **Core:** 2.3.3
- **Task:** User: "build it yourself" — start building backlog N18 (the Android app) per ADR-10.
- **Environment blocker (found first):** this host has **no JVM, Gradle, Kotlin, or Android SDK** (only Python 3.9.6). So Kotlin cannot be compiled/tested and no APK can be built here. Chose to deliver the fully-verifiable foundation + a buildable scaffold rather than hand-write ~5,800 lines of unverifiable crypto.
- **Commits:** `5ad93c2` chore(ledger) roster check-in · `1f78661` feat(android) Phase-1 scaffold (product) · (pending) this ledger batch (current.md, roster→Blocked, this entry, STATE).
- **Outcome (N18 Phase 1, partial):**
  - ✅ **Golden-vector harness** — `android/goldens/generate_goldens.py` runs the real backend over the 31 bundled samples → `android/goldens/fixtures/*.json` (verified: hc→A5, ehi→B2, ziv→H1 success; dark→I1 partial; tls→F1 known-failed). This is the parity oracle for the whole port.
  - ✅ **Gradle scaffold** — `:core` pure Kotlin/JVM lib (crypto/parse/SNI, testable on a plain JDK — no emulator) + `:app` Android/Compose. Pinned versions (AGP 8.5.2, Kotlin 2.0.21, Compose BOM 2024.09.03, Bouncy Castle 1.78.1, kotlinx-serialization 1.7.3, OkHttp 4.12.0, dnsjava 3.6.1).
  - ✅ **Model** `core/.../model/Models.kt` — faithful port of `ir/models.py`; **golden parity test harness** `GoldenParityTest.kt`.
  - ✅ **Docs** `android/README.md` + `android/TASKS.md` (phase/scheme checklist tied to golden coverage).
  - ⏳ **Not built/compiled; not ported:** detector, 13 decrypt schemes, KeyStore, parse engine, SNI Hunter, UI — all need a Kotlin toolchain to do responsibly.
- **Blocked / hand-off:** need a build environment. User to choose: install JDK 17 + Android SDK locally (agent builds+tests here next), or a cloud/sandbox session with the toolchain. Golden coverage gap: hat/npv/nsh/vhd/legacy hc-ehi have no samples → no goldens (tie to N3) — add samples before porting those schemes.
- **Report:** no separate review file (scaffold/planning slice; `android/` is product code).
- **Notes:** Roster row left **Blocked** (not removed) — resumes once the toolchain is sorted. `date -u`=2026-11-13.

---
## 2026-11-14 — Session 34 (continued: N18 toolchain + :core green)
- **Agent:** Forge | **Codename:** OF01SS34 | **Model:** claude-opus-4-8 | **Platform:** local macOS (Intel x86_64), Darwin 24.6.0 | **Core:** 2.3.3
- **Task:** User: "install [at] user level" — provision a Kotlin/Android build toolchain locally (no sudo) and build.
- **Outcome:**
  - **Toolchain installed, user-level:** Temurin **JDK 17.0.21** + **Gradle 8.9** downloaded from official sources into `~/.local/toolchain/` (no sudo, reversible). Referenced by absolute `JAVA_HOME` (shell env doesn't persist between tool calls).
  - **`:core` builds green:** generated the Gradle wrapper; `./gradlew :core:test` → BUILD SUCCESSFUL, `GoldenParityTest` passes (tests=1, failures=0) — all 31 golden fixtures deserialize into the Kotlin `NormalizedConfig` and match the Python backend. So the Kotlin model/contract is verified against the reference impl on a real compile.
  - **Fix:** golden fixture filenames had emoji/Cyrillic that broke Gradle's resource copy ("could not get file mode"); `generate_goldens.py` now emits ASCII-safe deterministic slugs (format + scrubbed stem + 8-char path hash). Committed the wrapper (jar un-ignored) + `.gitattributes` (wrapper scripts exempt from whitespace lint).
  - Commits: `62e5cc8` (product) + ledger commits (`e6a3c4e` resume, this batch).
- **Next (Phase 2→5):** port `detector.py`, crypto primitives + KeyStore, then schemes with golden coverage first (A5/B2/H1/I1), router + parse engine; extend `GoldenParityTest` to full pipeline parity. `:app`/APK deferred — needs Android SDK (API 34) + disk freed (~5 GB free now).
- **Report:** none (build/infra slice; `android/` is product).
- **Notes:** Toolchain lives outside the repo (`~/.local/toolchain`) — not committed. Roster row kept Working (checkpoint, continuing). `date -u`=2026-11-14.

---
## 2026-11-14 — Session 34 (continued: N18 ZIV H1 ported + verified)
- **Agent:** Forge | **Codename:** OF01SS34 | **Model:** claude-opus-4-8 | **Platform:** local macOS (Intel) | **Core:** 2.3.3
- **Task:** User: "keep porting" — begin the Kotlin decrypt pipeline, verified against goldens.
- **Outcome:** Ported the **first real scheme — ZIV (H1)** — and it passes decrypt-layer golden parity. `core/crypto/Primitives.kt` (PBKDF2-HMAC-SHA256 via Bouncy Castle PKCS5S2 + AES-GCM) and `core/crypto/scheme/ZivH1.kt` (port of `ziv_decrypt.py`); `ZivH1DecryptTest` asserts the Kotlin decrypt reproduces the Python `_all_fields` byte-for-byte for all 6 ziv samples → `./gradlew :core:test` BUILD SUCCESSFUL (2 suites, 0 failures). Made `:app` conditional on an SDK being present so `:core` builds on a bare JDK. Recorded the parity methodology as **ADR-11**. Commit `5be53ab` (product) + this ledger batch.
- **Next:** port detector (`detector.py`), then more schemes decrypt-layer-first — I1 (dark, simple base64 envelope) and A5 (hc) / B2 (ehi) are next; then parse engine + full-pipeline parity. `:app`/APK still needs the Android SDK (deferred).
- **Report:** none (porting slice; `android/` is product).
- **Notes:** Roster row kept Working (continuing). `date -u`=2026-11-14.

---
## 2026-11-14 — Session 34 (continued: all 4 golden-covered schemes ported)
- **Agent:** Forge | **Codename:** OF01SS34 | **Model:** claude-opus-4-8 | **Platform:** local macOS (Intel) | **Core:** 2.3.3
- **Task:** User: "keep going one after the other pushing each without pausing" — port the remaining golden-covered decrypt schemes to Kotlin, verify + push each.
- **Outcome:** All four schemes with sample coverage now ported and decrypt-layer-verified against the Python backend:
  - **DARK I1** (`DarkI1.kt`, commit 128db9a) — base64 envelope, type/name/locked.
  - **HC A5** (`HcA5.kt`, 5be466c) — initial XOR → ChaCha20 seek64 → RST/AES-ECB or ChaCha → token split → per-field JKL/braille/z3a. Fixed two parity bugs: strict-UTF8 JKL fallback, z3a floor-division + 64-bit shift. 13/13.
  - **EHI B2** (`EhiB2.kt`, 4c0d976) — AES-CBC×2 → XXTEA → Argon2id → XChaCha20-Poly1305 (HChaCha20 hand-rolled; BC lacks XChaCha) → inner-field XOR/EHIMSG decode + nested JSON. 6/6, passed first run.
  - (ZIV H1 done earlier: 5be53ab.)
  - Primitives.kt now has: PBKDF2, AES-GCM/ECB/CBC, ChaCha20(8-byte nonce/seek), Argon2id, XChaCha20-Poly1305.
  - `:core` has **5 green test suites**; each scheme asserted vs its golden `_all_fields`.
- **Next:** schemes WITHOUT samples (hat E1, npv C1, nsh D1, vhd G1, legacy hc A1-A4, ehi B1, tls F1) have no goldens → **blocked on N3** (add samples) before they can be parity-verified. Then detector + parse_engine ports unlock full-pipeline parity (ADR-11). `:app` UI/APK still needs the Android SDK.
- **Report:** none (porting; `android/` is product).
- **Notes:** Roster kept Working. `date -u`=2026-11-14.

---
## 2026-11-14 — Session 34 (continued: detector + parse engine, full-pipeline parity)
- **Agent:** Forge | **Codename:** OF01SS34 | **Model:** claude-opus-4-8 | **Platform:** local macOS (Intel) | **Core:** 2.3.3
- **Task:** User: "Detector + parse engine" — port them and upgrade to full-pipeline parity.
- **Outcome:** Both ported and the whole decode pipeline is verified end-to-end.
  - `core/detect/Detector.kt` (port of detector.py): extension + validation, feature vector (entropy/skew/ascii/base64/null/zip, HALF_EVEN round to 4dp), encrypted classifier. Matches Python incl. the failed-TLS feature vector.
  - `core/ParseEngine.kt` (port of parse_engine.py): detect → scheme dispatch → per-format json_data builders (ziv/hc/ehi) → normalizers (ziv/dark/hc/ehi) with universal field map, protocol detection, HTTP payload parsing. Output mirrors pydantic model_dump (all IR fields, enums as values) + the hasattr guard.
  - **`FullPipelineTest` PASSES**: `parseConfig(file) == NormalizedConfig` for all 31 samples (ziv success / dark partial / hc success / ehi success / tls failed), minus decrypt_trace + machine-specific filepath (ADR-11). Commit 6617220.
  - `:core` has **6 green suites**. Three small divergences found+fixed while reaching parity: machine-specific filepath excluded; `notes`/`openvpn_config`/`ssh_host` aren't IR fields (added a settable-fields guard mirroring Python hasattr); payload_parsed needed `_parse_payload`.
- **Next:** sample-less schemes (hat/npv/nsh/vhd/legacy hc-ehi/tls) still blocked on **N3** (no goldens); `:app` UI (Phase 6) + APK (Phase 8) need the **Android SDK**.
- **Report:** none (porting; `android/` is product).
- **Notes:** Roster kept Working. `date -u`=2026-11-14.

---
## 2026-11-14 — Session 34 (continued: Android SDK + Compose UI + APK)
- **Agent:** Forge | **Codename:** OF01SS34 | **Model:** claude-opus-4-8 | **Platform:** local macOS (Intel) | **Core:** 2.3.3
- **Task:** User chose "Set up Android SDK (UI)" — install the SDK user-level and build the app UI.
- **Outcome:** A runnable app now wraps the verified decode core.
  - **Android SDK installed user-level** (no sudo): `~/.local/android-sdk` via cmdline-tools — platform-tools, platforms;android-34, build-tools;34.0.0 (498 MB; no emulator images, to respect disk — ~4 GB free). Gradle points at it via `android/local.properties` (gitignored).
  - **Compose UI** (`app/MainActivity.kt`, Material3 dark): SAF file pick → read bytes → `ParseEngine.parseConfig` off the main thread → render key fields + full normalized JSON + share-sheet export.
  - **core**: added bytes-based `Detector.detect` / `ParseEngine.parseConfig` (SAF Uri → bytes + name); File overloads delegate. kotlinx-serialization-json moved to `api` (public return type).
  - **build**: added the Kotlin 2.0 Compose Compiler plugin (required) + coroutines; dropped `kotlinCompilerExtensionVersion`.
  - **`:app:assembleDebug` → app-debug.apk (13 MB) builds green**; `:core` 6 suites still green. Commit 036836e.
- **Not done / honest limits:** runtime behaviour UNVERIFIED — no device/emulator on this host (can't boot one on ~4 GB free / Intel). APK is confirmed to assemble + link against the verified core only. Release signing not set up.
- **Next:** runtime test on a device/emulator; release signing (Phase 8); SNI Hunter (Phase 7); sample-less schemes (N3).
- **Report:** none (porting/build; `android/` is product).
- **Notes:** `local.properties` is gitignored (machine-specific sdk.dir). Roster kept Working. `date -u`=2026-11-14.

---
## 2026-11-14 — Session 34 (continued: launcher icon + SNI Hunter core)
- **Agent:** Forge | **Codename:** OF01SS34 | **Model:** claude-opus-4-8 | **Platform:** local macOS (Intel) | **Core:** 2.3.3
- **Task:** User: "Copy the apk on desktop then continue with Porting SNI Hunter"; mid-turn: "export the icon also" → clarified "the apk to use the icon also".
- **Outcome:**
  - Copied `app-debug.apk` + `injectx-icon.png/.ico` to `~/Desktop/`.
  - **Launcher icon in the APK**: generated `ic_launcher.png` at 5 densities (sips from assets/icons/icon.png) + `android:icon` in the manifest; aapt confirms it's packaged at every density. Updated APK re-copied to Desktop. (Source 545x614 → squared; a proper adaptive icon is a follow-up.)
  - **SNI Hunter core ported to `:core`** (`sni/` package): Models, `SniProbe` (classifyHttp/portal/dedupe/cap), `Seedlist` (txt/csv/json + bundled per-ISP lists as resources), `CrtSh` (parse), `Export` (txt/csv/json), `SniNetwork` (live DNS→TLS-SNI→HTTP→reverse-DNS probe + crt.sh discovery via OkHttp/JSSE — I/O, compile-verified only). `SniHunterTest` (6 tests) verifies the pure logic vs Python (classify cases, seedlist counts airtel 13/safaricom 19/telkom 10, crt.sh parse, export). **:core now has 7 green suites.** Commits e0836f3 (+846d58f TASKS).
- **Not ported (follow-ups):** defensive fronting probe (ADR-9), ECH/reverse-IP/port-check, CertStream, and an `:app` UI surface for SNI.
- **Report:** none (porting/build; `android/` is product).
- **Notes:** Roster kept Working. `date -u`=2026-11-14.

---
## 2026-11-14 — Session 34 (continued: UI redesign)
- **Agent:** Forge | **Codename:** OF01SS34 | **Model:** claude-opus-4-8 | **Platform:** local macOS (Intel) | **Core:** 2.3.3
- **Task:** User: "the UI needs some real work and creativity."
- **Outcome:** Redesigned the `:app` UI around the InjectX brand (viewed the icon → near-black ground, neon-green X, cyan circuit accents).
  - `ui/theme/` — `InjectXTheme` (dark color scheme + shapes + type) + `MonoValue` terminal style.
  - `ui/Brand.kt` — Canvas-drawn glowing hex+X logo; per-format accent + per-status pill colours.
  - `MainActivity` — empty state (hero logo, CTA, supported-format chips), loading, error, and a result screen: header card (format badge + status pill + scheme), CONNECTION card of copyable mono rows, WARNINGS card, expandable normalized-JSON, Export/Open-another; clipboard copy + snackbar.
  - `:app:assembleDebug` green; updated APK re-exported to `~/Desktop/`. Showed the user a device-frame mockup of the design. Commit 4d4b5cb.
- **Honest limit:** still no runtime verification (no device/emulator) — compiles + links only; visual intent shown via mockup.
- **Next:** runtime test (user's device); SNI remainder (fronting/ECH/UI); release signing; N3 schemes.
- **Report:** none. Roster kept Working. `date -u`=2026-11-14.

---
## 2026-11-14 — Session 34 (continued: SNI Hunter screen + tab nav)
- **Agent:** Forge | **Codename:** OF01SS34 | **Model:** claude-opus-4-8 | **Platform:** local macOS (Intel) | **Core:** 2.3.3
- **Task:** User: "Replace the desktop apk with current then continue with SNI."
- **Outcome:**
  - Replaced `~/Desktop/injectx-debug.apk` with the current build (later re-exported again after the SNI UI).
  - **SNI Hunter screen wired into the app.** New `ui/Components.kt` (shared Pill/SectionCard + custom `SegmentedTabs` + `verdictColor`). New `SniScreen.kt`: Discover card with a Seedlist|Domain segmented input (bundled per-ISP seedlists or a domain for crt.sh discovery) → Start scan → live incremental rows (hostname/IP/HTTP/server + colour-coded verdict pill), working/total counter, Stop, and Export-working (txt share). Probing off `Dispatchers.IO`, deduped (ADR-6). `MainActivity` now has a top Decode | SNI Hunter tab bar; Decode flow extracted into its own composable.
  - `:app:assembleDebug` green; APK re-exported. Commit 673e22d.
- **Honest limit:** the SNI network probing is compile-verified only (no device here, and it hits live network at runtime); the SNI logic it calls IS unit-tested (`:core` 7 suites). UI runtime unverified.
- **Next (SNI remainder):** defensive fronting probe (ADR-9), ECH/reverse-IP/port-check, CertStream; "use this host as SNI" bridge into a decoded config. Plus runtime test, release signing, N3 schemes.
- **Report:** none. Roster kept Working. `date -u`=2026-11-14.

---
## 2026-11-14 — Session 34 (continued: fix uninstallable APK + APK version control)
- **Agent:** Forge | **Codename:** OF01SS34 | **Model:** claude-opus-4-8 | **Platform:** local macOS (Intel) | **Core:** 2.3.3
- **Task:** User: APK says "package appears invalid"; version-control debug APKs (lost the first one by overwriting); + design feedback (home/main screen, rethink tabs) — deferred.
- **Outcome:**
  - **Install fix.** Diagnosed: APK was valid but minSdk 26 (excludes Android 7.0/7.1) and v2-only (AGP drops v1 at minSdk>=24; budget-OEM installers — common on Transsion/Tecno/Infinix in the KE market — reject v2-only with "package invalid"). Lowered minSdk → 24; `scripts/export-apk.sh` re-signs the built APK **v1+v2+v3** (`apksigner --min-sdk-version 21` forces the v1 JAR sig). Desktop APK now verifies v1+v2+v3. AGP's `enableV1Signing` is ignored at minSdk>=24, hence the apksigner re-sign.
  - **APK version control.** `android/dist/` is now git-tracked (un-ignored the root `.gitignore` node `dist/`); builds archive as `injectx-debug-v<ver>-<sha>.apk` via `export-apk.sh` (build → re-sign → archive → copy latest to Desktop). First build committed. No build lost to overwrite again.
  - Commits ca233c3 (source/fix), 6d41297 (archive + .gitignore). `:core` 7 suites unaffected.
- **DEFERRED (next):** design rework — a Home/landing screen instead of Decode-as-default, and a more creative navigation than the top segmented tabs. Awaiting direction/taste.
- **Honest limit:** install fix is reasoned from signing/minSdk, not device-verified (no device here). If it still fails, likely transfer corruption or device < API 24 — need the phone's Android version + transfer method.
- **Report:** none. Roster kept Working. `date -u`=2026-11-14.

---
## 2026-11-14 — Session 34 (continued: Desktop-versioned APK + UI design spec)
- **Agent:** Forge | **Codename:** OF01SS34 | **Model:** claude-opus-4-8 | **Platform:** local macOS (Intel) | **Core:** 2.3.3
- **Task:** User: versioned APK wasn't on the Desktop (only the stable name was); + "write the design in ledger".
- **Outcome:**
  - **export-apk.sh** now copies the **versioned** `injectx-debug-v<ver>-<sha>.apk` to the Desktop too (not just the stable `injectx-debug.apk`), so Desktop builds survive overwrites. Copied the current versioned build to the Desktop. Commit be7c47f. (Earlier this session: archive named by last CODE commit to skip doc/ledger dups — 1995149.)
  - **UI/UX design spec written to the ledger:** `features/android-ui.md` — the problem (Decode-as-home, flat top tabs), goals, a Home hub-and-spoke IA, Home-screen spec, tool-screen reframing, "outside the box" ideas (console/HUD, drag-drop decode, decrypt reveal), and the open decisions (nav pattern, HUD intensity, home content) that need the user's taste before building.
- **Next:** get the user's pick on §7 of the UI spec → build the Home screen + nav (record the nav choice as an ADR). Then SNI remainder + "use as SNI". Runtime still unverified (no device).
- **Report:** none. Roster kept Working. `date -u`=2026-11-14.

---
## 2026-11-14 — Session 34 (continued: Home hub navigation built)
- **Agent:** Forge | **Codename:** OF01SS34 | **Model:** claude-opus-4-8 | **Platform:** local macOS (Intel) | **Core:** 2.3.3
- **Task:** User: "Build it" — build the Home hub + hub-and-spoke nav from `features/android-ui.md`.
- **Outcome:** Built `HomeScreen.kt` (pulsing hex hero, INJECTX wordmark, monospace HUD status line, Decode/SNI "module" cards with accent bar + LED + chevron, responsible-use footer). `MainActivity` now routes a `Screen{Home,Decode,Sni}` state — Home is the start, tools have a back chevron + title, `BackHandler` returns Home; removed the top segmented tabs. `:app:assembleDebug` green. Decision recorded as **ADR-12**. APK re-signed (v1+v2+v3), archived `dist/injectx-debug-v0.1.0-e8a7b4f.apk`, versioned + latest on the Desktop. Commits e8a7b4f (UI), 8280c3d (APK). Showed the user a mockup of the new Home.
- **Honest limit:** no device/emulator → compile-verified + mockup only.
- **Next:** iterate on Home to taste (recents strip needs history persistence; HUD intensity); then SNI remainder (fronting/ECH/"use as SNI").
- **Report:** none. Roster kept Working. `date -u`=2026-11-14.

---
## 2026-11-14 — Session 34 (continued: calm/non-neon visual pass)
- **Agent:** Forge | **Codename:** OF01SS34 | **Model:** claude-opus-4-8 | **Platform:** local macOS (Intel) | **Core:** 2.3.3
- **Task:** User design feedback: the UI "looks ai generated… it should feel natural" (not the structure — the component craft).
- **Outcome:** Reworked the visual language toward calm/natural: new restrained palette (soft near-black + one muted sage-green accent, neutral text), natural type (no ALL-CAPS/wide tracking), flat single-tone logo, quiet tags; removed the neon, glows, LED dots, accent bars, pulse and fake HUD line. Home is now a modest header + plain divider tool list (not a splash). `:app:assembleDebug` green; APK archived d0acf4c, on Desktop. Revised direction + the "neon = AI tell" lesson written to `features/android-ui.md` §9. Commits d0acf4c (UI), 3317508 (APK).
- **Honest note:** this is a CALIBRATION pass — visual taste is my weakest area and I can't see it render (no device). A reference app from the user would anchor it far better than my guesses. Decode/SNI screen components still need the same de-decoration pass.
- **Next:** user reaction → iterate; de-decorate Decode/SNI result components to match; then SNI remainder.
- **Report:** none. Roster kept Working. `date -u`=2026-11-14.

---
## 2026-11-14 — Session 34 (continued: neon identity restored + real app icon)
- **Agent:** Forge | **Codename:** OF01SS34 | **Model:** claude-opus-4-8 | **Platform:** local macOS (Intel) | **Core:** 2.3.3
- **Task:** User's detailed design critique reversed the calm pass: the neon green/cyan identity is the right direction (calm was a regression), and the real defect was that NO screen used the actual app icon — each hand-drew its own hexagon.
- **Outcome:** Restored the neon palette in `Color.kt` (near-black green-tinted ground, #32E39B green + #45D6E8 cyan; token names kept so nothing cascades). Added `res/drawable/injectx_logo.png` (the real icon, from `assets/icons/icon.png`) as the ONE logo source; `HexLogo` now renders that asset scaled — never a redraw — everywhere (top bar, Decode empty-state hero). `formatColor` now covers all 9 formats (ehi/hc/ziv/dark/tls/npv/nsh/vhd/hat). Dropped Home's duplicate logo header (top bar carries it); kept the calm pass's plain-language tool descriptions + responsible-use disclaimer. `:app:assembleDebug` green. APK re-signed v1+v2+v3, archived `dist/injectx-debug-v0.1.0-6b3dc06.apk`, versioned on Desktop. Spec in `features/android-ui.md` §10 (neon v3) + §11 (full SNI rework). Commits 6b3dc06 (UI), b598728 (APK).
- **Honest limit:** compile-verified only — no device/emulator here, so the render (real icon at size, neon on-screen) is still unseen.
- **Next (major):** SNI Hunter functional rework per `features/android-ui.md` §11 — remove hardcoded carrier seedlists, one flexible input (domain / `;`,`,` separated / `.txt`), cleanup+dedupe+live count, two-phase Discover(real net, crt.sh)→Test(dataless net) with a persistent candidate list surviving network switch, network label on results, 3-state results, export working-only. Then empty-state output previews; de-decorate Decode/SNI to the neon v3 look.
- **Report:** none. Roster kept Working. `date -u`=2026-11-14.
