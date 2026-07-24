# Feature Review — SNI Host Hunter Phase 3 (defensive mode)

- **Date:** 2026-07-24 (UTC, `date -u`) — Session 28
- **Agent:** Claude Code · **Model:** claude-opus-4-8 (Opus 4.8) · **Platform:** local macOS (Darwin 24.6.0), Python 3.9.6, Node v24.17.0 · **Role:** feature-engineer · **Core:** 0.3.0
- **Target:** Implement SNI Host Hunter Phase 3 (backlog **N16**) — defensive mode — per `features/sni-host-hunter.md` §5.2/§3.5. User: "Pull and continue phase 3."

> **Date note:** this session began late on 2026-07-23 UTC (core.lock verify
> stamped 2026-07-23) and crossed midnight into 2026-07-24. The immediately
> prior Session 27 was logged 2026-07-26 — its cloud sandbox clock ran ~2 days
> ahead of real UTC. I briefly inherited that "2026-07-26" label in ADR-9 +
> current.md before checking `date -u`, then corrected everything to the honest
> **2026-07-24**. So Session 28 (07-24) sorts *before* Session 27 (07-26) by
> date. Trust `date -u`; the cloud sessions' dates are skewed ahead.

## 1. Executive Summary

Shipped Phase 3 — the **defensive** half of SNI Host Hunter. A single probe,
`probe_fronting(sni, host)`, answers all three N16 angles: (1) SNI/Host-header
mismatch (domain-fronting) detection, (2) TLS-cert fingerprint comparison
across SNIs, (3) an enforcement verdict (`bypassable` = the ISP's SNI filter
leaks; `enforced` = it cross-checks SNI vs Host). New `backend/snihunter/
defensive.py`, `SniFrontingResult`/`FrontingVerdict` models, `POST /api/sni/
fronting`, and a `sni fronting <sni> <host>` terminal command via the existing
IPC chain. 15 new tests (suite 151 → **166**, ruff clean). Ratified ADR-9.
Also fixed pulled test-infra breakage that blocked the suite in a clean env.
Acceptance shape: *"`sni fronting` classifies a real SNI/Host mismatch and
compares certs" — verified live.*

## 2. Design Decisions

- **ADR-9** (new): the defensive probe is single-target, read-only, and
  non-exploitative — a detector, not an exploiter, and deliberately NOT wired
  into the ADR-6 scan/concurrency machinery. It observes what a server does
  with a mismatched Host; it never tunnels or relays. This keeps Phase 3 on the
  research/defensive side of the dual-use framing (§7).
- One probe covers all three angles (vs three endpoints) — the mismatch test,
  the cert comparison, and the verdict all come from the same handshakes.
- **Raw asyncio+ssl, not httpx**, for the mismatched-Host request: httpx couples
  SNI and Host to the URL; decoupling them is the whole point. The `host` header
  is sanitised (`_safe_hostname`, hostname-charset only) so it can't inject CRLF
  into the raw request line.

## 3. What Was Built (per commit)

1. `710890d` fix(test): `asyncio_mode="auto"` + pytest-asyncio — unblocks the
   pulled suite (see §6).
2. `f79c263` chore(context): ratify ADR-9.
3. `0115835` feat(snihunter): `defensive.py` + models + `/api/sni/fronting`.
4. `26aaa40` test(snihunter): 15 defensive unit tests.
5. `6c19b9d` feat(ui): `sni fronting` terminal command + IPC/preload/api.
6. `a570817` docs: README Defensive-mode section + architecture §13.8.
7. `c0124e8` docs: changelog.

(Product commits pushed `67f67d1..c0124e8`. Context commits separate.)

## 4. What Was Verified (and how)

- **Unit:** `pytest` → **166 passed** (was 151). `ruff check .` → clean. Covers
  the `classify_fronting` verdict matrix (error/indeterminate/enforced/
  bypassable), wildcard cert matching, HTTP-head parsing (incl. 421 + HTTP/2),
  and the CRLF-injection hostname guard.
- **Live backend (curl, port 8791):**
  - `example.com`/`example.com` → `bypassable`, cert covers host,
    `cert_changes_with_sni=false`, co-located ✓
  - `www.cloudflare.com`/`example.com` (real mismatch) → `indeterminate` (403
    Forbidden), `cert_changes_with_sni=true`, different IPs — Cloudflare rejected
    the fronted Host ✓
  - `www.wikipedia.org`/`en.wikipedia.org` (same tenant) → `bypassable` (301),
    `*.wikipedia.org` covers host ✓
  - invalid hostname (CRLF) → **400** ✓; DNS-dead SNI → verdict `error` ✓
- **Frontend chain:** Node harness drove the real `api.js` `API.sni.fronting`
  against the live backend — correct verdict + full field shape the
  `CMD.sni.fronting` handler consumes.
- **Syntax:** `node --check` on all four touched JS files → OK.

A clean `421 Misdirected Request` (→ `enforced`) wasn't reproduced live (it's
server-dependent), but the 421→enforced mapping is unit-tested and the live run
exercised the other three verdicts.

## 5. What Was NOT Verified (user should confirm)

- **Real Electron app** — the IPC registration + terminal DOM rendering need
  `npm start` (this machine can't launch Electron headless). Try `sni fronting
  www.cloudflare.com example.com`. IPC *payloads* are verified via the harness.
- **Packaging** — two prior confirmations are still pending from cloud sessions:
  the Phase 2 sidebar in the packaged app (Session 26), and `npm run dist` after
  the fast-uri override (Session 27).

## 6. Inherited breakage fixed (in scope — test infra I extend)

The pulled Session 26 tests (`test_portcheck.py`) use `@pytest.mark.asyncio`,
but `pytest-asyncio` was never pinned and the `asyncio` marker was unregistered
— so with `--strict-markers` the whole suite failed collection in a clean venv
(it only passed in the cloud sandbox where the plugin happened to be present).
Fixed with `asyncio_mode="auto"` in pyproject + installing pytest-asyncio (a dev
dep, unpinned like the repo's other dev tooling). Suite collects and passes
again. Advances N3.

## 7. Open Items / Backlog

- **N16 done.** New **N17**: expose the fronting probe in the sidebar UI (a
  defensive panel / per-row "FRONT?" action) — Phase 3 is terminal + API only.
- Formalize dev dependencies (pytest-asyncio, ruff, mypy) — currently unpinned;
  ties into N3/N4 (test infra + CI).
- User confirmations pending (§5).
