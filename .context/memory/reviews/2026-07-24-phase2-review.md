# Feature Review — SNI Host Hunter Phase 2

- **Date:** 2026-07-24 (UTC, `date -u`) — Session 26
- **Agent:** Super Z · **Model:** unknown (GLM family; system prompt states "GLM model developed by Z.ai" without a specific version — recorded as `unknown` per the protocol's no-guess rule) · **Platform:** Z.ai cloud sandbox — Debian 13 trixie, Python 3.12.13, Node v24.18.0 · **Role:** engineer · **Core:** 0.3.0
- **Target:** Implement SNI Host Hunter Phase 2 (backlog **N15**) per the design doc `.context/memory/features/sni-host-hunter.md` §5.2/§6.5.

## 1. Executive Summary

Shipped Phase 2 of SNI Host Hunter — the sidebar UI module, "use as SNI",
CertStream watch, ECH detection (RFC 9848), reverse-IP lookup, and open-port
checker. Five new backend modules (`dns_check.py`, `sources/certstream.py`,
`reverseip.py`, `portcheck.py`, `apply.py`), five new `/api/sni/*` endpoints,
a full sidebar "05 · SNI HUNTER" view (config panel + live results table +
verdict pills + per-row action buttons), and 60 new tests (suite 91 → **151**,
all green, ruff clean). `dnspython` added to requirements for SVCB/HTTPS-RR
queries.

Every endpoint verified live via a self-contained Python script that starts
the backend, curls every endpoint (success + error paths + the
`INJECTX_ENABLE_SNI_HUNTER=0` kill switch), and tears down. The frontend
IPC chain verified via a Node harness that loads the real `api.js` and drives
`API.sni.*` against the live backend through a faithful copy of the `main.js`
IPC proxies — same pattern Session 24 used. All JS syntax-checked with
`node --check`.

The one open verification — packaged Electron app visual confirmation of the
sidebar module — is flagged for the user, same as every prior frontend change
in this cloud-sandbox environment.

## 2. What Was Built

### Backend (`backend/snihunter/`)

| Module | Purpose | Lines |
|---|---|---|
| `dns_check.py` | ECH capability detection via RFC 9848 DNS SVCB/HTTPS-RR. Queries the HTTPS RR, falls back to SVCB, extracts the `ech=` param, base64-validates it. Best-effort — DNS failures return `error` strings, never raise. | 175 |
| `sources/certstream.py` | Real-time CT watch via the `certstream` package (optional dep). Runs `listen_for_certs` in a thread, filters new hostnames to the target domain, returns `SniCandidate` list. Pure helpers (`_extract_hostnames`, `filter_to_domain`, `build_candidates`) are unit-tested. | 155 |
| `reverseip.py` | Reverse-IP lookup via HackerTarget's free API + PTR fallback. Pure `parse_hackertarget_response` handles rate-limit/error responses correctly. | 110 |
| `portcheck.py` | TCP connect probe on 80/443/8080/8443 (default). ADR-6 backstop: `MAX_PORTS_PER_HOST = 32` caps any caller-supplied list. | 80 |
| `apply.py` | "Use as SNI" — re-parses a config from disk, overrides `sni`, preserves original under `raw_data._original_sni` (idempotent), patches all SNI-alias keys in `_all_fields`, adds an audit warning. Pure `apply_sni` + `apply_sni_to_config_id` (which does the re-parse). | 95 |

### Endpoints (`backend/main.py`)

Five new POST endpoints under `/api/sni/*`, all gating on `SNI_HUNTER_ENABLED`
+ `_require_sni_enabled()`:

| Endpoint | Purpose |
|---|---|
| `POST /api/sni/watch` | CertStream watch — duration clamped to [1, 300]s. 503 if `certstream` not installed. |
| `POST /api/sni/ech` | ECH capability check — returns `{ech_capable, ech_config, https_rr_count, svcb_rr_count, error}`. |
| `POST /api/sni/reverseip` | Reverse-IP — returns `{hostnames, source, via_hackertarget, via_ptr, error}`. |
| `POST /api/sni/portcheck` | Open-port probe — returns `{ports, open, closed, error}`. |
| `POST /api/sni/apply` | "Use as SNI" — re-parses config, overrides `sni`, returns the new `ConfigInfo`. 404 if config_id missing, 400 if no SNI, 500 if re-parse fails. |

### Frontend

- **`frontend/main.js`** — 5 new `ipcMain.handle` entries (`sni-watch`,
  `sni-ech`, `sni-reverseip`, `sni-portcheck`, `sni-apply`) using the existing
  `proxyPost` pattern (ADR-7).
- **`frontend/preload.js`** — 5 new `sniWatch`/`sniEch`/`sniReverseIp`/
  `sniPortcheck`/`sniApply` bridge methods.
- **`frontend/src/scripts/api.js`** — `API.sni.{watch,ech,reverseIp,portcheck,apply}`
  namespace methods.
- **`frontend/src/scripts/renderer.js`** — 430 new lines:
  - `state.sni` block (currentJob, verdictFilter, pollTimer, etc.)
  - `renderSniHunterView()` — seeds the seedlist dropdown, renders the
    current job.
  - `sniStartScan()` / `sniPollJob()` — scan lifecycle with 1s polling.
  - `renderSniResults()` — results table with verdict pills + per-row
    action buttons (Use as SNI / ECH / PORTS / REV-IP).
  - `sniUseAsSni()` — calls `API.sni.apply`, refreshes the detail view.
  - `sniCheckEch()` / `sniCheckPorts()` / `sniReverseIp()` — per-row action
    handlers with toast feedback.
  - `sniDiscover()` / `sniWatch()` — FIND/WATCH buttons auto-start a scan.
  - `setupSniHunter()` — wires every button + Enter-key handlers + verdict
    pill click-to-filter.
- **`frontend/index.html`** — new `<section id="view-snihunter">` with the
  two-panel layout (config panel + results panel) and a new sidebar entry
  "05 · SNI HUNTER" (System bumped to 06).
- **`frontend/src/styles/main.css`** — 280 new lines: `.sni-layout`,
  `.sni-config-panel`, `.sni-results-panel`, `.sni-row`, verdict pills
  (`.sni-verdict-pill.ok/.warn/.danger/.muted`), action buttons, progress
  bar, jobs list. Uses the existing CIPHER_OPS color variables.

### Tests (`backend/tests/`)

| File | Tests | Covers |
|---|---|---|
| `test_dns_check.py` | 16 | ECH base64 validation, `extract_ech_config` (string + enum + list-valued params), `is_ech_capable`. |
| `test_certstream_source.py` | 18 | Message parsing, domain filtering (incl. suffix-attack rejection), wildcard stripping, dedupe, `build_candidates`. |
| `test_reverseip.py` | 9 | HackerTarget response parsing (multi-host, single, rate-limit, error, no-records, blank lines, lowercasing). |
| `test_portcheck.py` | 8 | Open/closed/invalid-host probes via real localhost listener, MAX_PORTS_PER_HOST cap, default port set. |
| `test_sni_apply.py` | 12 | Top-level override, `_original_sni` preservation + idempotency, all SNI-alias keys patched, warnings (set/override/same-value), empty-value rejection, lowercasing, no-raw-data case, other raw_data keys preserved. |

**Total: 60 new tests. Suite 91 → 151. All pass. Ruff clean.**

## 3. What Was Verified (and how)

- **Unit tests:** `pytest` → 151 passed (was 91). `ruff check .` → clean.
  Every new module has pure-function tests that need no network.
- **Live backend (curl, port 8791):** a self-contained Python script
  (`/home/z/my-project/scripts/verify_phase2.py`) starts the backend, then:
  - Parses a real HC config to get a `config_id`.
  - `POST /api/sni/ech` on `cloudflare.com` (not ECH-capable — apex has no
    `ech=` param) and on `crypto.cloudflare.com` (ECH-capable — confirmed
    live: `ech_capable=True`, `ech_config` populated).
  - `POST /api/sni/ech` on a nonexistent host → 200 with `ech_capable=False`
    + `error` populated (graceful, not a crash).
  - `POST /api/sni/reverseip` on `1.1.1.1` → 500 sibling hostnames via
    HackerTarget.
  - `POST /api/sni/portcheck` on `cloudflare.com` → `[80, 443, 8080, 8443]`
    all open; on a bad host → all closed; custom ports `[22, 80, 443]` →
    exactly 3 probed.
  - `POST /api/sni/apply` on the HC config → `sni` overridden to
    `test-bug-host.example.com`, `_original_sni` preserved as `None` (the HC
    config had no SNI), warning added.
  - `POST /api/sni/apply` on a real EHI config (TelkomNet.ehi) → original
    SNI `myaccount.telkom.co.ke` preserved, new SNI applied, "SNI overridden
    via Host Hunter: myaccount.telkom.co.ke → new-bug.example.com" warning.
  - Error paths: empty hostname/IP/config_id/SNI → 400; non-existent
    config_id → 404.
  - `POST /api/sni/watch` on `cloudflare.com` 8s → 503 (certstream not
    installed in the sandbox — acceptable, the endpoint surfaces a clear
    install hint).
  - **Kill switch:** restarts the backend with
    `INJECTX_ENABLE_SNI_HUNTER=0` → every new endpoint returns 403.
- **Frontend API chain (Node harness):** a Node script
  (`/home/z/my-project/scripts/verify_phase2_frontend.py`) loads the real
  `api.js`, wires `window.vpnAPI` to a faithful copy of the `main.js` IPC
  proxies, and drives every `API.sni.*` method against the live backend.
  Confirms: seedlists load, ECH returns `ech_capable`, reverseIp returns
  `hostnames`, portcheck returns `ports` with 443 open on cloudflare.com,
  apply overrides the `sni` field, watch returns a 200-or-503 shape.
- **Syntax:** `node --check` on `main.js`, `preload.js`, `api.js`,
  `renderer.js` → all OK.

## 4. What Was NOT Verified (user should confirm)

- **Real Electron app.** The sidebar SNI HUNTER module's DOM rendering, the
  IPC handler registration in `main.js`, and the per-row action button
  click handlers need a packaged/`electron .` run — this sandbox can't
  launch Electron headless (no display server; a standing env limitation
  since Session 1). The IPC *payloads* are verified (the Node harness
  exercised identical request/response shapes). Please run `npm start`,
  click the "05 · SNI HUNTER" sidebar item, pick a seedlist, START SCAN,
  and try the Use-as-SNI / ECH / PORTS / REV-IP buttons on a working host.
- **CertStream live.** The `certstream` package isn't installed in the
  cloud sandbox (the watch endpoint correctly returns 503 with the install
  hint). To enable: `pip install certstream` in the backend venv, then
  `sni watch <domain>` or the WATCH button.
- **Real-world verdict tuning.** The captive-portal indicator list
  (`data/portal_indicators.txt`) is unchanged from Phase 1 — still
  best-effort. Safaricom/Airtel/Telkom captive-portal patterns should be
  confirmed against a live SIM (§9 Q3 in the design doc).

## 5. Notable implementation details

- **ECH detection's three key shapes.** dnspython's SVCB/HTTPS RR exposes
  `.params` as a `dns.immutable.Dict` keyed by `ParamKey` enum instances.
  `str(ParamKey.ECH)` returns `"5"` (the IANA numeric value), not `"ech"`.
  The first cut of `extract_ech_config` matched on `str(k).lower() == "ech"`
  and missed every real ECH record. Fixed by iterating `params.items()` and
  matching on `k.name.lower() == "ech"` (the enum's `.name` attribute). The
  unit tests use plain-string-keyed fixture objects (which still pass via
  the `else` branch); the live `crypto.cloudflare.com` check confirms the
  enum-keyed path works. This is exactly the kind of "verified live, not
  just unit-tested" catch the protocol's "verify each fix end-to-end"
  preference is designed to surface.

- **`apply_sni` is a pure function.** The IR override logic has no I/O —
  `apply_sni(normalized, new_sni)` returns a patched copy. The I/O
  (re-parse from disk) lives in `apply_sni_to_config_id(config_store,
  config_id, new_sni)`. This split makes the override logic unit-testable
  without touching the filesystem, and means a future "revert" button can
  call `apply_sni(normalized, original_sni)` to undo.

- **CertStream as optional dep.** The `certstream` package is imported
  lazily inside `watch()`; if it's absent, `watch()` raises `ImportError`
  with a clear install hint, which the API layer catches and surfaces as
  503. This keeps the feature shippable in environments where the
  websocket-client transitive dep is unwanted.

- **Reverse-IP rate-limit handling.** HackerTarget's free API surfaces
  rate-limiting as a plain-text single-line response (e.g. "API count
  exceeded"). `parse_hackertarget_response` checks for error markers ONLY
  on single-line bodies — a multi-line body where one line happens to
  contain "error" (e.g. `error.example.com`) is correctly treated as
  hostnames. Unit-tested explicitly for this case.

- **Port checker ADR-6 backstop.** `MAX_PORTS_PER_HOST = 32` is a hard cap
  on any caller-supplied port list. The default set (80/443/8080/8443) is
  well under; the cap exists so a hostile API call can't queue 65535
  probes. Unit-tested by passing a 82-port list and asserting exactly 32
  are probed.

## 6. Commits

Two-surface discipline (ADR-4): product + docs in one set, `.context/`
memory in another.

- Product/docs:
  - `feat(snihunter): Phase 2 — ECH, certstream, reverseip, portcheck, apply`
    (backend modules + endpoints + tests)
  - `feat(ui): SNI Host Hunter sidebar module + Phase 2 actions`
    (frontend)
  - `docs: README + architecture + changelog for SNI Host Hunter Phase 2`
- `.context/` memory:
  - `chore(context): log session 26 + N15 done + Phase 2 review`
  - (design doc status update folded into the same commit)

Pushed to `main` directly per the standing push policy.

## 7. Open Items / Backlog

- **N15 → done.** Phase 2 fully shipped.
- **N16 (new): SNI Host Hunter Phase 3** — defensive mode. Per the design
  doc §5.2 deferred items + §3.5 spoofing detection: verify an ISP's
  zero-rating enforcement, nDPI-style SNI/Host-header mismatch detection,
  per-host TLS fingerprint comparison. Lower priority than N3/N4 (test
  infrastructure + CI).
- **User confirmation needed:** packaged Electron app visual verification
  of the sidebar module (§4).
- **Optional:** `pip install certstream` in the backend venv to enable the
  WATCH button / `sni watch` terminal command.
- N1-N14 unchanged (N1 architecture doc further advanced by the §13.2/§13.6
  updates this session; N3/N4 still the highest-leverage open items).

## 8. Research provenance

The four web searches that grounded the Phase 2 implementation are saved
at `/home/z/my-project/scripts/search_rfc9848.json`,
`search_dnspython_https.json`, `search_certstream_api.json`,
`search_reverseip.json`. Key findings folded into the implementation:

- **RFC 9848** (Bootstrapping ECH via DNS SVCB/HTTPS records) — verified
  real via IETF Datatracker. The `ech=` SvcParamKey is the mechanism.
- **dnspython 2.6+** has full SVCB/HTTPS RR support including the `ech`
  param (keyed by `ParamKey.ECH`, value is an `ECHParam` object with
  `.to_text()` returning the base64 string).
- **CertStream** (`CaliDog/certstream-python`) uses a blocking
  `listen_for_certs(callback)` — run in a thread, stopped via
  `client.stop()`.
- **HackerTarget** reverse-IP API at `https://api.hackertarget.com/
  reverseiplookup/?q=IP` — free, no auth, rate-limited (~50/day), returns
  plain text one-host-per-line.
