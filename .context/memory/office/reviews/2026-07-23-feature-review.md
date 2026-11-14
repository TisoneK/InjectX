# Feature Review — SNI Host Hunter Phase 1 (MVP)

- **Date:** 2026-07-23 (UTC, `date -u`) — Session 24
- **Agent:** Claude Code · **Model:** claude-opus-4-8 (Opus 4.8) · **Platform:** local macOS (Darwin 24.6.0), Python 3.9.6, Node v24.17.0 · **Role:** feature-engineer · **Core:** 0.3.0
- **Target:** Implement SNI Host Hunter Phase 1 (backlog **N14**) per the design doc `.context/memory/features/sni-host-hunter.md` §6.5, plus a fresh online-research pass.

> **Date note:** true UTC today is 2026-07-23, but Session 23 (cloud) was
> logged 2026-07-24 — its sandbox clock ran a day ahead. So Session 24
> *predates* Session 23 by filename. The feature doc, N14, and ADR-6/7/8
> keep the 2026-07-24 label for continuity with the design; this session's
> own log/report use the honest 2026-07-23.

## 1. Executive Summary

Shipped Phase 1 (MVP) of SNI Host Hunter — the discover → probe → export
loop the config-decrypt pipeline was missing. New `backend/snihunter/`
package (crt.sh + seedlist discovery, async TLS/HTTP/DNS prober with a
pure verdict classifier, in-memory job store, txt/csv/json export), 7
`/api/sni/*` endpoints, bundled per-ISP seed lists (Safaricom/Airtel/
Telkom Kenya), a `sni` terminal command tree routed through the existing
Electron IPC chain, 37 new tests (suite 54 → **91**, all green, ruff
clean), and README + architecture + changelog docs. Ratified ADR-6/7/8.
Feature ships **enabled** by default with an `INJECTX_ENABLE_SNI_HUNTER=0`
kill switch. Acceptance shape: *"`sni scan` classifies real hosts and
exports the working set" — verified live.*

## 2. Design Decisions (ADRs — see `plans/decisions.md`)

- **ADR-6** (ratified from the §10 proposal): loopback-bound research tool
  — concurrency hard-capped at 200, per-host dedupe (≤1 probe/host/job),
  no IP-range scanning.
- **ADR-7**: the frontend routes through the existing Electron IPC chain
  (renderer → `API.sni` → preload → `main.js` → backend), **not** the
  design doc §6.3 direct-renderer-fetch sketch. Keeps one uniform
  backend-access path.
- **ADR-8** (answers §9 Q1): seedlists ship **in-tree** under
  `backend/snihunter/data/seedlists/`, curated from public zero-rating
  sources. Public hostnames only — no secrets.

Open-question defaults taken (§9): Q2 default concurrency **50** (cap 200);
Q4 shipped **enabled** with an env kill switch rather than gated-off; Q5
ECH detection deferred to Phase 2 (no stub shipped — kept the IR clean).

## 3. What Was Built (per commit)

1. `e7f612f` chore(context): ratify ADR-6/7/8.
2. `9063184` feat(snihunter): backend package + 7 endpoints + seedlists +
   `httpx` dep + `_validate_seedlist_path` + kill switch.
3. `a7ea22e` test(snihunter): 37 unit tests.
4. `41a9922` feat(ui): `sni` terminal command tree + IPC handlers/bridge.
5. `8f88424` docs: README + architecture §13.
6. `defc297` docs: changelog entry.

(All product commits pushed: `cde8cc5..defc297`. Context commits separate.)

## 4. What Was Verified (and how)

- **Unit:** `pytest` → **91 passed** (was 54). `ruff check .` → clean.
  Covers IR, `classify_http` verdict matrix, captive-portal heuristic,
  crt.sh row parsing, seedlist parsing (txt/csv/json + cloudflare filter),
  exporters, and `_validate_seedlist_path` (extension allowlist, symlink
  bypass, 5 MiB cap).
- **Live backend (curl, port 8791):** health; `sni/seedlists` (3 lists,
  13/19/10 hosts); scan of `example.com`/`www.cloudflare.com` → `working`
  (200, cloudflare) and `nonexistent-zzz.invalid` → `dead`; job polling;
  `export txt` = working hosts only; `export csv`; bad format → 400; no
  candidates → 400; `/etc/passwd` seedlist path → 400; stop signalled;
  jobs list. **crt.sh discover:** error path verified (crt.sh returned a
  transient 502 → surfaced cleanly as 502 + logged); success path returns
  candidates when crt.sh is up (confirmed crt.sh flakiness independently).
- **Disabled flag:** second instance with `INJECTX_ENABLE_SNI_HUNTER=0` →
  every `/api/sni/*` returns **403**.
- **Frontend chain:** Node harness drove the real `api.js` `API.sni`
  namespace against the live backend through a faithful copy of the
  `main.js` IPC proxies — seedlists load, bundled-name→path resolves,
  inline scan classifies correctly, jobs list, txt export = working only.
  Caught and fixed a real arg-routing bug (`looksLikePath("example.com")`
  is true, which would have misrouted a bare hostname to `seedlist_path`)
  — replaced with a has-a-slash discriminator.
- **Syntax:** `node --check` on all four touched JS files → OK.

## 5. What Was NOT Verified (user should confirm)

- **Real Electron app.** The IPC *registration* (`ipcMain.handle` /
  preload bridge) and the terminal DOM rendering need the packaged/`electron .`
  app — this machine can't launch Electron headless (no display; a
  standing env limitation). The IPC *payloads* are verified (the Node
  harness exercised identical request/response shapes). Please run
  `npm start`, open the Terminal, and try `sni seedlists` / `sni scan
  safaricom-ke.txt` / `sni export <jobId> txt`.
- **Live crt.sh discovery from the UI** — crt.sh was intermittently 502
  during testing (its own load, not ours). Retry `sni find cloudflare.com`.
- **Real-world verdict tuning** — the captive-portal indicator list
  (`data/portal_indicators.txt`) is best-effort; Safaricom/Airtel/Telkom
  captive-portal patterns should be confirmed against a live SIM (§9 Q3).

## 6. Online research refresh (this session)

- **crt.sh** JSON API confirmed live and canonical in 2026.
- **RFC 9849** (TLS Encrypted Client Hello, 2026) verified real via IETF
  Datatracker + rfc-editor. **New:** **RFC 9848** (Bootstrapping ECH via
  DNS SVCB/HTTPS records) — directly relevant to Phase-2 ECH detection
  (query the HTTPS RR for an `ech=` param).
- **BugScanX-Go** surfaced with a **DirectNon302** mode (excludes redirect
  responses) — corroborates the redirect-vs-working verdict split.
- Folded these into the feature doc's "Session 24 research refresh" block.

## 7. Open Items / Backlog

- **N14 → Phase 2** (new backlog entry): sidebar SNI HUNTER module, live
  results table + "use as SNI", CertStream watch, ECH detection (RFC 9848
  HTTPS-RR), reverse-IP + port checks, `dnspython` when async TXT/SVCB
  lookups are needed.
- Confirm the feature in the packaged Electron app (§5).
- N1 (architecture doc staleness) partially advanced — §13 added and flags
  the older sections as pre-v0.4; a full reconciliation is still open.
