# Feature Spec — SNI Host Hunter

> **Status:** **Phase 1 (MVP) shipped** (Session 24, 2026-07-23) — Phase 2 open.
> **Added:** 2026-07-24 by Super Z (cloud, Session 23).
> **Phase 1 shipped:** Session 24 (Claude Code / Opus 4.8, local). Backend
> `backend/snihunter/` + 7 `/api/sni/*` endpoints + bundled seedlists +
> `sni` terminal commands + 37 tests, all verified. See
> `reviews/2026-07-23-feature-review.md` and ADR-6/7/8 in `plans/decisions.md`.
> Deviations from this doc, all deliberate: frontend routes through Electron
> IPC not renderer fetch (ADR-7); `dnspython` deferred to Phase 2 (stdlib DNS
> covers the MVP); no ECH stub in Phase 1 (§9 Q5 answered "defer"); feature
> ships enabled with an `INJECTX_ENABLE_SNI_HUNTER=0` kill switch (§9 Q4).
> **Scope:** comprehensive technical + product design for an in-app SNI host
> discovery and verification module. Captures the domain research, the InjectX
> integration analysis, a phased implementation plan, and every primary
> reference. Future implementation sessions read this file FIRST and pick up
> where this research left off — do not re-derive from scratch.
> **Companion artifacts:** raw web-search/page-reader JSON dumps live at
> `/home/z/my-project/scripts/sni-research/` (outside the repo, so they don't
> bloat git — see "Research provenance" at the bottom for the source URLs).

---

## 1. Why this feature, and why now

InjectX is a universal VPN tunnel config file reader. Its existing pipeline
(Detector → Scheme Router → Decryptor → Parse Engine → `NormalizedConfig`
IR) already produces, for every loaded config, a fully-decoded `sni` field
plus the surrounding `host`/`port`/`protocol`/`payload` needed to actually
tunnel. The next logical step — and the one the user keeps circling back to
across Sessions 9, 12, 14, 17 — is letting InjectX **find** those SNI hosts
itself, not just decode the ones the user already has.

Concrete reasons this fits the product:

1. **The user already imports configs whose SNI is the load-bearing
   field.** Looking at `assets/configs/`: HA Tunnel Plus (`.hat`) and HTTP
   Injector (`.ehi`) configs ship with `sni` set to a "bug host" — a
   hostname the user's ISP zero-rates. Once that host stops working, the
   whole config is dead. The user then has to find a new bug host
   out-of-band (a Telegram channel, a blog post, a Scribd PDF), hand-edit
   the config, and re-import. SNI Host Hunter collapses that loop into one
   app.

2. **The African ISP zero-rating context is the user's home turf.** The
   bundled sample configs include TelkomNet, Airtel (`.ehi`), Safaricom,
   ethiotelecom — every one of these is a real African ISP that
   zero-rates specific SNI hosts (Safaricom Free Basics, Airtel Free
   Basics, Telkom zero-rated portals; see §3.4). The user (timezone
   Africa/Nairobi) lives in exactly the market this tool targets.

3. **The state of the art has matured.** When the user provided the
   initial research context (in chat), ECH was described as a "proposal".
   As of March 2026, **RFC 9849 (TLS Encrypted Client Hello) is
   published**, OpenSSL 4.0 ships ECH support, and NGINX has landed ECH
   support — see §3.3. The SNI inspection window that ISPs exploit is
   closing, but it is not closed yet, and the bug-host ecosystem is still
   active (BugScanX, SNIbugtester, snihost.com all updated within the
   last 12 months).

4. **InjectX already has every architectural piece the feature needs.**
   FastAPI backend, Pydantic IR, Electron frontend, a terminal command
   tree, an activity log dock, a sidebar module pattern, and an
   `audit/live_log.py` that streams per-step progress to the UI. The
   feature is *additive* — no rewrite of any existing component.

---

## 2. What SNI bug-host hunting actually is (one-paragraph primer)

A TLS client sends the hostname it wants to reach in the **cleartext SNI
extension** of its `ClientHello`. ISPs that zero-rate certain hosts
(Safaricom Free Basics, Airtel Free Basics, government health/education
portals) do so by inspecting that SNI string against a whitelist and
skipping billing for matches. An **SNI bug host** is a hostname on that
whitelist (or a hostname the ISP's DPI fails to distinguish from one) that
the user can plug into a tunneling app — the app opens a TLS handshake
with that SNI, the ISP lets the bytes through unbilled, and the tunnel
then carries the user's real traffic inside the TLS session. SNI Host
Hunter is the tool that **discovers** candidate hostnames, **probes**
them to see which ones actually pass through the ISP zero-rating path,
and **exports** them in a form that drops straight back into an InjectX
config's `sni` field.

---

## 3. Domain research summary (2025–2026 state of the art)

This section is the user-provided research context, augmented with what
the web-search/page-reader pass turned up. Primary sources are listed in
§11; raw JSON dumps are at `/home/z/my-project/scripts/sni-research/`.

> **Session 24 research refresh (2026-07-23, local, WebSearch):** re-verified
> the key claims before implementing.
> - **crt.sh** JSON API (`?q=%.<domain>&output=json`) confirmed live and
>   canonical in 2026; `name_value` multi-line SANs + wildcard filtering
>   unchanged. Used as-is.
> - **RFC 9849** (TLS ECH) confirmed real via IETF Datatracker + rfc-editor.
>   **New find: RFC 9848** — "Bootstrapping TLS Encrypted ClientHello with DNS
>   Service Bindings" (SVCB/HTTPS RRs). This is the concrete mechanism a
>   Phase-2 ECH-detection probe should use: query the target's HTTPS RR and
>   look for an `ech=` parameter to flag ECH-capable hosts.
> - **BugScanX-Go** (`Ayanrajpoot10/bugscanx-go`) surfaced with a
>   **DirectNon302** mode that excludes redirect responses — independent
>   corroboration of Phase 1's redirect-vs-working verdict split (a working
>   bug host returns a real response, not a 302 to a portal).
> - Kenya/Safaricom/Airtel/Telkom seed sources (Techfoe, aimtuto, snihost.com,
>   KOFnet, TemoVision) still active; bundled seedlists curated from the
>   publicly documented zero-rated set (Free Basics / operator / education
>   portals) per ADR-8 — candidates to probe, not guaranteed working hosts.

### 3.1 Discovery — passive (Certificate Transparency)

The user's research context is accurate; the tools it lists still work.
Verified additions from the search pass:

- **crt.sh** is alive at `https://crt.sh` and exposes a JSON API at
  `https://crt.sh/?q=%25.<domain>&output=json`. The `gotr00t0day/crt.sh`
  Python tool wraps it with multiprocessing for parallel DNS resolution
  after the CT pull. **This is the single most useful endpoint for
  InjectX** — one HTTP GET returns every SAN/CN ever issued for a domain,
  which is exactly the seed list for bug-host probing.
- **certstream-python** (`pip install certstream`,
  `github.com/CaliDog/certstream-python`) is the maintained Python client
  for Cali Dog's real-time CT feed. Useful for an "watch mode" that
  streams newly-issued certificates for a target domain — but it is a
  firehose, not a query API, so it's a phase-2 feature.
- **CertGraph** (graph crawler, builds SAN/CN dependency graphs) and
  **Gungnir** (Go CT monitor) are still maintained but redundant with
  crt.sh for InjectX's MVP — crt.sh's REST API is enough.
- **Apify "crt.sh alternative" actors** exist (`advx/ct-domain-lookup`,
  `bgfc97/crtsh-subdomain-finder`) — they wrap the same JSON API and
  charge per-result. No reason to depend on them; the raw crt.sh API is
  free and rate-limit-friendly.

**For InjectX's MVP:** crt.sh JSON API is the only CT source that
matters. One async `httpx` GET per seed domain, parse the JSON, collect
`common_name` and every entry in `name_value` (which is `\n`-separated
SANs), dedupe, hand the list to the active prober.

### 3.2 Discovery — active probing

Two reference implementations surfaced in the research pass; both are
directly transferable to InjectX:

**BugScanX** (`github.com/pddung93/BugScanX`, `pip install bugscan-x`,
MIT license, by Ayan Rajpoot). A CLI tool with 8 menu items:
1. Subdomain scanner (probe a list of subdomains for SNI bug potential)
2. IP address scanner (probe IPs directly)
3. Subdomain finder (crt.sh-style discovery)
4. Domains hosted on same IP (reverse IP lookup)
5. Host OSINT
6. TXT toolkit (TXT DNS records — useful for SPF/_dmarc inspection)
7. Open port checker
8. DNS records fetcher (A, MX, TXT)

Dependencies: `requests`, `colorama`, `ipaddress`, `pyfiglet`, `socket`,
`ssl`, `beautifulsoup4`, `dnspython`, plus stdlib `multithreading`. This
is the **same dependency profile InjectX already has** (requests +
bs4 + dnspython are new; the rest are stdlib) — easy lift.

**SNIbugtester** (`github.com/Praveenhalder/SNIbugtester`, MIT license).
An Android app built with Python + Chaquopy — proves the model runs on
mobile too. Its UX is the **best reference for InjectX's UI**:

- Multi-file loading (`.txt` one-domain-per-line; `.json` array of
  `{domain, cloudflare: bool}` objects)
- **Range selection** — scan only `[start, end)` of the domain list
  (resume/split large scans)
- **Thread control** — concurrency knob, default 200 threads
- **Timeout control** — per-connection timeout, default 5s
- **Cloudflare-only filter** — when loading the JSON format, scan only
  entries where `cloudflare: true`
- **Live progress bar** + found counter (the activity-log dock InjectX
  already has maps perfectly onto this)
- **Results table**: domain, HTTP status code, color-coded by class
  (2xx green, 3xx orange, 4xx/5xx red)
- **IPs tab**: concurrent DNS resolution to IPv4 + IPv6, 3-column table
- **Export**: `.txt` (one host per line) or `.csv`
  (`domain, ip, status, protocol, redirect`)

This is essentially the spec InjectX should implement. The only
divergence is that InjectX doesn't need a separate "IPs tab" — its
existing detail view can host the resolved IPs.

### 3.3 ECH / Encrypted Client Hello (the closing window)

The user's research context called ECH a "proposal". **It is no longer a
proposal.** From the search pass:

- **RFC 9849 — "TLS Encrypted Client Hello"** is published (IETF
  Datatracker `datatracker.ietf.org/doc/rfc9849`). The spec is final.
- **OpenSSL 4.0** ships ECH support (post dated 2026-03-11 on
  `openssl-library.org`).
- **NGINX** has landed ECH support (`blog.nginx.org/blog/
  encrypted-client-hello-comes-to-nginx`), with broader adoption expected
  as OpenSSL 4.0 reaches spring 2026 release.
- **Cloudflare** is the dominant ECH-capable CDN; their edge already
  negotiates ECH with ECH-capable clients. ~95% of web traffic is TLS
  today (Enea insight, March 2025), and ECH adoption is the next curve.
- **Python ECH example** — Guardian Project published a working code
  example for using ECH from Python (January 2025), so when InjectX
  eventually needs an ECH-aware probe, the path exists.

**Impact on SNI Host Hunter:** For the next ~12–24 months, SNI inspection
still works against the majority of zero-rated hosts (which are
government portals, Free Basics, and educational sites — laggards in ECH
adoption). But the writing is on the wall: the feature should treat SNI
inspection as a **technique with a sunset**, not a permanent capability,
and should be designed so its **discovery** half (CT logs) is independent
of its **verification** half (active probing) — when ECH kills SNI
inspection, discovery still works and verification shifts to DNS-based
zero-rating detection (§6.4).

### 3.4 The Africa / Kenya zero-rating context

This is the user's home market. Verified facts from the search pass:

- **Safaricom** (Kenya, ~69% market share) runs a zero-rated program
  called **Free Basics** (Facebook's Internet.org initiative). Free
  Basics includes Wikipedia, Facebook, BBC News, and a curated list of
  low-bandwidth sites. UNESCO's zero-rating study confirms Safaricom also
  zero-rated Longhorn and Visuasa e-learning platforms.
- **Airtel Kenya** also offers Free Basics to all subscribers (Global
  Voices Advox PDF).
- **Telkom** (South Africa, sister brand to Telkom Kenya) zero-rates
  educational URLs — Institutions of higher learning and TVET Colleges
  (`group.telkom.co.za/about-us/zero-rated-portal.html`).
- **Bug host lists circulate publicly.** `scribd.com/document/578563989`
  is a "SNI host and zero-rated websites" PDF with explicit "Kenya SNI
  Bug Host List (Airtel, Safaricom)" sections. `aimtuto.com/2021/11/
  sni-host-list.html` maintains a per-country list (MTN, Cellc, Telkom,
  Airtel, etc.) updated as recently as 2025. `snihost.com` runs a live
  "Advanced SNI Bug Host Finder" web service with a country/ISP picker.
- **Techfoe** (mentioned in the Facebook group post) publishes
  Safaricom-specific SNI hostname lists with HA Tunnel Plus config
  recipes.

**Implication for the feature:** InjectX's SNI Host Hunter should ship
with a **seed-list library** keyed by ISP — a `data/seedlists/` tree
with files like `safaricom-ke.txt`, `airtel-ke.txt`, `telkom-ke.txt`,
`mtn-za.txt`, etc. These seed lists are the "starter fuel" the user
loads to bootstrap a scan; the CT-log discovery then expands from there.
The seed lists themselves are not secret — they're publicly published
zero-rated domains.

### 3.5 SNI spoofing detection (the other side)

If InjectX is eventually used for **defensive** purposes (verifying that
an ISP's zero-rating whitelist is correctly enforced), the same probing
machinery works in reverse. From the research pass:

- **nDPI** (ntop's deep packet inspection library) has an open issue
  (#2573) for detecting SNI/SSL-tunnel/DNS mismatches and **domain
  fronting** — the technique of sending an SNI that doesn't match the
  HTTP `Host` header. nDPI's detection logic is a reference for what
  ISPs see.
- **Compass Security's March 2025 blog post** ("Bypassing Web Filters
  Part 1: SNI Spoofing") is the modern authoritative write-up of the
  attack side. Key insight: SNI spoofing bypasses *basic* web filters
  but fails against filters that cross-check SNI against DNS or the HTTP
  Host header. This matches the "Defensive Mitigations" section of the
  user's research context.
- **Reverse DNS validation + DNS consistency checks** are the two
  techniques ISP-side defenses use. SNI Host Hunter can perform the same
  checks **from the client side** to predict whether a given bug host is
  likely to work — if the SNI's forward DNS doesn't resolve to the
  destination IP, the ISP's reverse-DNS check will fail and the bug host
  won't work.

---

## 4. InjectX integration analysis

Where the feature plugs into the existing codebase. Every claim here was
verified by reading the file in this session.

### 4.1 Backend — `backend/`

| File | What it does today | What the feature adds |
|---|---|---|
| `backend/main.py` | FastAPI app, route handlers, `config_store`, `_validate_config_path` (ADR-1 + ADR-5 hardened) | New router prefix `sni/` with endpoints listed in §5.4. Reuses `_validate_config_path` for any user-supplied seed-list path. |
| `backend/ir/models.py` | `NormalizedConfig` (the canonical IR), `FormatEnum`, `SchemeEnum`, `DecryptTrace`, etc. | New Pydantic models: `SniCandidate`, `SniProbeResult`, `SniScanJob`. NOT added to `NormalizedConfig` — these are a separate IR surface (see §5.3). |
| `backend/audit/live_log.py` | In-memory log buffer polled by UI via `/api/logs?since=N` | Reused unchanged. The scan progress streams through this same channel — UI needs zero changes to display it. |
| `backend/parser/` (whole tree) | Detector + per-format parsers | Unchanged. The feature is *orthogonal* to format parsing. |
| `backend/decrypt/` (whole tree) | Format-specific decryptors | Unchanged. |
| `backend/tunnel/__init__.py` | "Future tunnel engine" placeholder (empty) | Still unchanged — SNI Host Hunter doesn't tunnel, it just probes. |

**New module: `backend/snihunter/`** — a new top-level backend package
sibling to `parser/`, `decrypt/`, `audit/`. Internal layout:

```
backend/snihunter/
├── __init__.py          # public API: discover(), probe(), scan()
├── sources/             # discovery sources (one module per source)
│   ├── __init__.py
│   ├── crtsh.py         # crt.sh JSON API client
│   ├── certstream.py    # (phase 2) real-time CT feed
│   └── seedlist.py      # load bundled per-ISP seed lists
├── probe.py             # asyncio SNI prober — TLS handshake + HTTP probe
├── dns_check.py         # forward/reverse DNS + ECH capability detection
├── models.py            # SniCandidate, SniProbeResult, SniScanJob IR
├── store.py             # in-memory job store (mirrors config_store)
└── export.py            # .txt / .csv / .json exporters
```

This mirrors the existing `parser/` + `decrypt/` split: `sources/` is
the "input" side, `probe.py` is the "transform" side, `store.py` is the
"state" side, `models.py` is the "IR" side.

### 4.2 Frontend — `frontend/`

| File | What it does today | What the feature adds |
|---|---|---|
| `frontend/main.js` | Electron main: window, IPC handlers, file/folder dialogs, settings persistence | New IPC handlers: `sni-scan-start`, `sni-scan-stop`, `sni-export`, `sni-load-seedlist`. Same pattern as existing `import-folder`. |
| `frontend/preload.js` | Context bridge | Expose new `window.injectx.sni.*` API surface. |
| `frontend/src/scripts/api.js` | Backend HTTP client | New `sni` namespace: `sni.discover(domain)`, `sni.scan(opts)`, `sni.listJobs()`, `sni.export(jobId, fmt)`. |
| `frontend/src/scripts/renderer.js` | UI rendering + terminal command tree (`CMD` tree, `runCommand`) | New sidebar module "05 · SNI HUNTER". New terminal commands: `sni find <domain>`, `sni scan <seedlist>`, `sni jobs`, `sni stop <jobId>`, `sni export <jobId> <txt|csv|json>`. |
| `frontend/index.html` | App shell, sidebar, modules | New sidebar entry + new module div. Same pattern as the Terminal module added in Session 19. |
| `frontend/src/styles/main.css` | Dark theme | New styles for the results table, progress bar, status pills — reuse the Arsenal dashboard styles from Session 20. |

### 4.3 IR — `backend/ir/models.py`

The feature does **not** pollute `NormalizedConfig` (which is the
config-file IR and must stay stable per the IR versioning rule). It adds
**parallel** Pydantic models in `backend/snihunter/models.py`:

```python
class SniCandidate(BaseModel):
    """One hostname discovered as a potential bug host."""
    hostname: str
    source: Literal["crt.sh", "seedlist", "certstream", "manual"]
    discovered_at: str  # ISO 8601 UTC
    # Optional context from the discovery source
    issuer_ca_id: Optional[int] = None       # crt.sh field
    not_before: Optional[str] = None         # crt.sh field
    not_after: Optional[str] = None          # crt.sh field

class SniProbeResult(BaseModel):
    """Result of probing one SniCandidate against a target IP."""
    hostname: str
    # What we probed
    target_ip: Optional[str] = None
    port: int = 443
    timeout_s: float = 5.0
    # Outcomes
    tls_handshake_ok: bool = False
    http_status: Optional[int] = None         # 200, 301, 302, ...
    http_redirect: Optional[str] = None       # Location header if 3xx
    server_header: Optional[str] = None       # Server: cloudflare, nginx, ...
    cert_cn: Optional[str] = None             # Subject CN from ServerHello
    cert_sans: list[str] = []
    # DNS cross-checks
    forward_dns: list[str] = []               # A/AAAA records for hostname
    reverse_dns: Optional[str] = None         # PTR for target_ip
    dns_consistent: Optional[bool] = None     # forward_dns contains target_ip?
    # Verdict
    verdict: Literal["working", "redirect", "blocked", "dead", "unknown"]
    notes: list[str] = []
    probed_at: str  # ISO 8601 UTC
    elapsed_ms: float = 0.0

class SniScanJob(BaseModel):
    """A scan in progress or completed."""
    job_id: str
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    status: Literal["queued", "running", "stopped", "done", "failed"]
    # Inputs
    seed_domain: Optional[str] = None         # for `sni find <domain>`
    seedlist_path: Optional[str] = None       # for `sni scan <seedlist>`
    candidates: list[SniCandidate] = []
    # Config
    concurrency: int = 50
    timeout_s: float = 5.0
    cloudflare_only: bool = False
    # Progress
    total: int = 0
    done: int = 0
    found: int = 0            # count of verdict=="working"
    # Results
    results: list[SniProbeResult] = []
```

**Reused existing IR fields:** the `sni` field on `NormalizedConfig`
(IR v1.0, line 265 of `models.py`) is exactly where a discovered bug
host gets written back when the user picks "use this host in my config"
— see §6.3.

### 4.4 Security & ADR compliance

The feature must respect every standing ADR:

- **ADR-1 + ADR-5 (path validation):** any user-supplied seedlist path
  goes through `_validate_config_path`'s extension allowlist + symlink
  re-check pattern. New allowed extensions for seedlists: `.txt`, `.csv`,
  `.json` — add to a separate `ALLOWED_SEEDLIST_EXTENSIONS` frozenset
  (don't pollute `ALLOWED_EXTENSIONS` which is config-file-only). Cap
  seedlist file size at 5 MiB (seedlists are kilobyte-scale; a hostile
  50 MiB list would let an attacker queue millions of probes).
- **ADR-2 (CORS):** the new endpoints sit under the same `/api/sni/*`
  prefix and inherit the existing CORS middleware — no change needed.
- **ADR-3 (GET for idempotent ops):** `GET /api/sni/jobs`,
  `GET /api/sni/jobs/{job_id}`, `GET /api/sni/seedlists` are GET.
  `POST /api/sni/scan` (mutates state — starts a job),
  `POST /api/sni/stop` (mutates state — stops a job),
  `POST /api/sni/export` (returns a file body — POST is fine).
- **ADR-4 (two surfaces):** feature code is project surface, `.context/`
  is memory surface — never mix in one commit.
- **New ADR-6 (proposed):** "SNI Host Hunter probes are bound to
  loopback egress only." The prober must not be a network-scanning tool.
  Hard-cap concurrency at 200 (SNIbugtester's default) and per-target
  rate-limit at 1 req/sec to make the tool unsuitable for abuse. See
  §7 (legal/ethical) for the rationale.

### 4.5 Test infrastructure impact

The feature should land with tests from day one — backlog item N3
(per-format parser tests) is the precedent. New test files under
`backend/tests/`:

- `test_sni_candidate.py` — IR construction + serialization
- `test_sni_probe_result.py` — verdict classification logic (the
  "redirect to captive portal" detection is the trickiest piece)
- `test_crtsh_source.py` — mocks `httpx.get` against fixture JSON,
  asserts dedupe + SAN parsing
- `test_seedlist_loader.py` — `.txt`, `.csv`, `.json` parsing +
  size-cap enforcement + extension allowlist
- `test_path_validation_seeds.py` — extends `test_path_validation.py`
  with the seedlist path cases (symlink with allowed extension, etc.)

No tests for the live prober itself (it makes real network calls) —
that's verified manually per the user's "verify each fix end-to-end"
preference.

---

## 5. Feature design — MVP and Full Vision

### 5.1 MVP (Phase 1 — single session, ~3-5 commits)

The smallest useful slice that delivers the core loop:

1. **`sni find <domain>` terminal command** — discover candidates via
   crt.sh, print them in the terminal table format.
2. **`sni scan <seedlist.txt>` terminal command** — load a seedlist,
   probe each host with a TLS handshake + HTTP GET, classify the
   result (`working` / `redirect` / `blocked` / `dead`), stream
   progress to the activity log, print results table when done.
3. **`sni jobs` / `sni stop <jobId>` / `sni export <jobId> <fmt>`** —
   job management.
4. **`backend/snihunter/`** package as described in §4.1, minus
   `certstream.py` (phase 2) and `dns_check.py` ECH detection (phase 2).
5. **Bundled seedlists** for the user's three home ISPs:
   `data/seedlists/safaricom-ke.txt`, `airtel-ke.txt`, `telkom-ke.txt`.

**MVP does NOT include:**
- A sidebar UI module (terminal-only first — same path the Terminal
  module took in Session 20)
- Real-time CertStream monitoring
- ECH capability detection
- Reverse IP lookup ("domains hosted on same IP" — BugScanX feature #4)
- Open port checker (BugScanX feature #7)
- Host OSINT (BugScanX feature #5)

The MVP's value is the closed loop: **discover → probe → export → paste
back into a config's SNI field**. Everything else is gravy.

### 5.2 Full Vision (Phase 2+ — multiple sessions)

After MVP ships and the user validates the loop:

- **Sidebar SNI HUNTER module** (mirror of the Arsenal dashboard from
  Session 20) — visual seedlist picker, scan config form (concurrency,
  timeout, cloudflare-only), live results table with verdict pills,
  "Use as SNI" button on each working host that opens a config detail
  view and patches its `sni` field.
- **CertStream watch mode** — `sni watch <domain>` subscribes to
  newly-issued certificates for that domain and auto-adds them to the
  candidate list.
- **ECH detection** — for each probed host, check whether the TLS
  handshake negotiated ECH. Mark ECH-capable hosts differently in the
  results (they're less useful as bug hosts — see §3.3).
- **Reverse IP lookup** — for a working bug host, list other domains
  hosted on the same IP (BugScanX feature #4). Useful because the ISP's
  zero-rating whitelist is often the whole IP, not just one SNI.
- **Open port checker** — quick port 80/443/8080/8443 sweep on the
  resolved IP.
- **Config patch-and-reimport** — one-click "apply this SNI to my
  HA Tunnel config" — backend re-parses the config with the new SNI
  injected, returns the updated `NormalizedConfig`.

### 5.3 IR design rationale — why parallel, not extended

`NormalizedConfig` is the **config-file** IR — it's the output of
parsing a single file on disk. A scan job is a **multi-host, multi-step
process** that produces a list of results over time — different
cardinality, different lifecycle. Forcing it into `NormalizedConfig`
would mean either (a) fake "synthetic" configs that aren't files on
disk, breaking the IR's invariant, or (b) adding a `scan_results:
Optional[list[SniProbeResult]]` field to `NormalizedConfig` that's
None for every real config. Both are worse than a parallel IR.

The bridge between the two IRs is the **`sni` field on
`NormalizedConfig`** — when the user picks "use this host", the
frontend calls a new endpoint that re-parses the config with the SNI
overridden (Phase 2 feature). No IR change needed.

### 5.4 API endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/sni/seedlists` | List bundled + user seedlists |
| GET | `/api/sni/jobs` | List scan jobs (running + recent) |
| GET | `/api/sni/jobs/{job_id}` | Get one job's state + partial results |
| POST | `/api/sni/discover` | Body: `{"domain": "..."}` → returns `list[SniCandidate]` (crt.sh pull) |
| POST | `/api/sni/scan` | Body: `{"seedlist_path": "...", "candidates": [...], "concurrency": 50, "timeout_s": 5.0, "cloudflare_only": false}` → returns `{"job_id": "..."}` |
| POST | `/api/sni/scan/stop` | Body: `{"job_id": "..."}` → stops a running scan |
| POST | `/api/sni/export` | Body: `{"job_id": "...", "format": "txt|csv|json"}` → returns file bytes |

All under the same `/api` prefix, so the existing CORS middleware
(ADR-2) covers them with no change.

### 5.5 Terminal commands (MVP)

```
sni help                          — show this list
sni find <domain>                 — discover candidates via crt.sh
sni scan <seedlist-path>          — scan a seedlist file
sni scan --cf-only <seedlist>     — scan only cloudflare:true entries (JSON format)
sni jobs                          — list scan jobs
sni stop <jobId>                  — stop a running scan
sni export <jobId> <txt|csv|json> — export results
sni seedlists                     — list bundled + user seedlists
```

These slot into the existing `CMD` tree in `renderer.js` alongside
`targets`, `logs`, `system`, `assets`. Same `runCommand` dispatcher.

---

## 6. Implementation plan (for the implementing session)

This section is a checklist a future session can follow without
re-deriving the design.

### 6.1 Dependencies to add to `backend/requirements.txt`

```
httpx>=0.27       # async HTTP client for crt.sh + probing (cleaner than requests for asyncio)
dnspython>=2.6    # DNS forward/reverse lookups (BugScanX uses this too)
```

Both are well-maintained, MIT-licensed, pure-Python (no system deps).
`httpx` over `requests` because the prober is fundamentally async —
probing 200 hosts concurrently with `requests` needs a thread pool;
`httpx.AsyncClient` does it natively. `requests` stays for the existing
synchronous detector/parser code; no rewrite needed.

`bs4` (BeautifulSoup) is NOT needed for MVP — crt.sh returns JSON, not
HTML. Add it only if a future source needs HTML scraping.

### 6.2 Backend module shapes (pseudo-code, not final)

**`backend/snihunter/sources/crtsh.py`** — the discovery source:

```python
import httpx
from ..models import SniCandidate

CRT_SH_URL = "https://crt.sh/?q=%.{domain}&output=json"

async def discover(domain: str, timeout: float = 30.0) -> list[SniCandidate]:
    """Query crt.sh for every certificate ever issued for `domain` and its subdomains.
    Returns a deduped list of SniCandidate."""
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        resp = await client.get(CRT_SH_URL.format(domain=domain))
        resp.raise_for_status()
        rows = resp.json()
    seen: set[str] = set()
    out: list[SniCandidate] = []
    for row in rows:
        # name_value is "\n"-separated SAN list
        for name in row.get("name_value", "").split("\n"):
            name = name.strip().lower().lstrip("*.")
            if not name or name in seen:
                continue
            seen.add(name)
            out.append(SniCandidate(
                hostname=name,
                source="crt.sh",
                discovered_at=datetime.now(timezone.utc).isoformat(),
                issuer_ca_id=row.get("issuer_ca_id"),
                not_before=row.get("not_before"),
                not_after=row.get("not_after"),
            ))
    return out
```

**`backend/snihunter/probe.py`** — the active prober:

```python
import asyncio
import socket
import ssl
import time
import httpx
from ..models import SniProbeResult

async def probe_one(hostname: str, port: int = 443, timeout: float = 5.0) -> SniProbeResult:
    """Probe one hostname: TLS handshake → cert extraction → HTTP GET → verdict.
    Returns SniProbeResult with all fields filled in."""
    t0 = time.monotonic()
    result = SniProbeResult(
        hostname=hostname, port=port, timeout_s=timeout,
        probed_at=datetime.now(timezone.utc).isoformat(),
    )
    try:
        # Step 1: forward DNS
        try:
            infos = await asyncio.get_event_loop().getaddrinfo(hostname, port)
            result.forward_dns = list({i[4][0] for i in infos})
            result.target_ip = result.forward_dns[0]
        except socket.gaierror:
            result.verdict = "dead"
            result.notes.append("DNS resolution failed")
            return result

        # Step 2: TLS handshake with SNI = hostname
        ctx = ssl.create_default_context()
        ctx.check_hostname = True  # we want cert validation to fail loudly
        ctx.verify_mode = ssl.CERT_REQUIRED
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(result.target_ip, port, ssl=ctx,
                                         server_hostname=hostname),
                timeout=timeout,
            )
            result.tls_handshake_ok = True
            cert = writer.get_extra_info("peercert")
            if cert:
                result.cert_cn = dict(x[0] for x in cert.get("subject", ())).get("commonName")
                result.cert_sans = [v for sub in cert.get("subjectAltName", ()) for v in (sub[1],) if sub[0] == "DNS"]
            writer.close()
            await writer.wait_closed()
        except (ssl.SSLCertVerificationError, ssl.SSLError, asyncio.TimeoutError, OSError) as e:
            result.verdict = "dead"
            result.notes.append(f"TLS handshake failed: {type(e).__name__}: {e}")
            return result

        # Step 3: HTTP GET over the same TLS session — check status + redirect
        async with httpx.AsyncClient(timeout=timeout, verify=True, follow_redirects=False) as client:
            try:
                r = await client.get(f"https://{hostname}/")
                result.http_status = r.status_code
                result.server_header = r.headers.get("server")
                if 300 <= r.status_code < 400:
                    result.http_redirect = r.headers.get("location")
                    result.verdict = "redirect"
                    # Detect ISP captive-portal redirects by host pattern
                    if result.http_redirect and _looks_like_captive_portal(result.http_redirect):
                        result.verdict = "blocked"
                        result.notes.append("Redirect looks like ISP captive portal")
                elif 200 <= r.status_code < 300:
                    result.verdict = "working"
                elif 400 <= r.status_code < 500:
                    result.verdict = "working"  # 403/404 still means we reached the real server
                else:
                    result.verdict = "dead"
            except httpx.HTTPError as e:
                result.verdict = "dead"
                result.notes.append(f"HTTP probe failed: {type(e).__name__}: {e}")

        # Step 4: DNS consistency check
        try:
            ptr = await asyncio.get_event_loop().gethostbyaddr(result.target_ip)
            result.reverse_dns = ptr[0]
            result.dns_consistent = result.target_ip in result.forward_dns
        except (socket.herror, socket.gaierror):
            pass

    finally:
        result.elapsed_ms = (time.monotonic() - t0) * 1000
    return result

def _looks_like_captive_portal(url: str) -> bool:
    """Heuristic: captive-portal redirects point at ISP infra, not the requested host."""
    low = url.lower()
    indicators = ["captive", "portal", "redirect", "no-balance", "topup",
                  "data.bundles", "internetsuppressed", "isp.", "carrier."]
    return any(ind in low for ind in indicators)

async def scan(candidates, concurrency=50, timeout=5.0, on_progress=None, stop_flag=None):
    """Probe a list of hostnames concurrently. Streams progress via on_progress callback."""
    sem = asyncio.Semaphore(concurrency)
    async def _one(host):
        async with sem:
            if stop_flag and stop_flag.is_set():
                return None
            return await probe_one(host, timeout=timeout)
    return await asyncio.gather(*[_one(c.hostname) for c in candidates])
```

This is ~80 lines of real probing logic — the rest of the module is
plumbing. The verdict classification in `_looks_like_captive_portal` is
the part that needs the most real-world tuning — keep the indicator list
in a config file (`backend/snihunter/data/portal_indicators.txt`) so
users can add their ISP's captive-portal pattern without a code change.

**`backend/snihunter/store.py`** — in-memory job store (mirrors
`config_store` pattern in `main.py`):

```python
import asyncio
from .models import SniScanJob

class SniJobStore:
    """Thread-safe in-memory store for scan jobs. Same pattern as config_store."""
    def __init__(self):
        self._jobs: dict[str, SniScanJob] = {}
        self._stop_flags: dict[str, asyncio.Event] = {}

    def add(self, job: SniScanJob) -> None: ...
    def get(self, job_id: str) -> SniScanJob | None: ...
    def list(self) -> list[SniScanJob]: ...
    def set_stop_flag(self, job_id: str) -> None: ...
    def is_stopped(self, job_id: str) -> bool: ...
    def update(self, job_id: str, **fields) -> None: ...

sni_job_store = SniJobStore()  # module-level singleton
```

### 6.3 Frontend integration

The MVP frontend change is **terminal commands only** — no sidebar
module yet. Three pieces:

1. **`api.js`** — add `sni` namespace:
   ```javascript
   const sni = {
     discover: (domain) => fetch(`${API_BASE}/api/sni/discover`, {
       method: "POST", headers: {"Content-Type": "application/json"},
       body: JSON.stringify({domain})
     }).then(r => r.json()),
     scan: (opts) => fetch(`${API_BASE}/api/sni/scan`, {
       method: "POST", headers: {"Content-Type": "application/json"},
       body: JSON.stringify(opts)
     }).then(r => r.json()),
     jobs: () => fetch(`${API_BASE}/api/sni/jobs`).then(r => r.json()),
     stop: (jobId) => fetch(`${API_BASE}/api/sni/scan/stop`, {
       method: "POST", headers: {"Content-Type": "application/json"},
       body: JSON.stringify({job_id: jobId})
     }).then(r => r.json()),
     export: (jobId, fmt) => fetch(`${API_BASE}/api/sni/export`, {
       method: "POST", headers: {"Content-Type": "application/json"},
       body: JSON.stringify({job_id: jobId, format: fmt})
     }).then(r => r.blob()),
   };
   ```

2. **`renderer.js`** — extend the `CMD` tree (added in Session 20):
   ```javascript
   CMD.sni = {
     help: () => alignedTable([["sni find <domain>", "discover candidates via crt.sh"], ...]),
     find: async (args) => { ... calls api.sni.discover ... },
     scan: async (args) => { ... calls api.sni.scan, polls /jobs/{id} ... },
     jobs: async () => { ... },
     stop: async (args) => { ... },
     export: async (args) => { ... downloads the file via blob URL ... },
     seedlists: async () => { ... },
   };
   ```

3. **`index.html`** — no change for MVP (terminal is already wired).
   The sidebar SNI HUNTER module is Phase 2.

### 6.4 ECH-aware verification (phase 2 design note)

When ECH adoption makes SNI inspection unreliable (§3.3), the
verification half of the feature shifts from "send SNI, see if it gets
through" to "see if the host's DNS resolves to an IP the ISP lets
through unbilled". The implementation:

1. **Passive baseline:** With the user's data plan active, resolve the
   candidate host's DNS. Capture the resolved IPs.
2. **Zero-rated state:** With the user's data plan exhausted (or
   airplane-mode + cellular-data-only), try to TLS-handshake to the
   same IP. If it succeeds, the IP is zero-rated.
3. **Verdict:** If both succeed, the host is a working bug host even
   under ECH.

This is a Phase 2+ technique; the MVP doesn't need it.

### 6.5 Phasing checklist

**Phase 1 — MVP (this is what a feature-engineer session should ship
first):**

- [ ] Add `httpx`, `dnspython` to `backend/requirements.txt`
- [ ] Create `backend/snihunter/` package with `__init__.py`,
      `models.py`, `sources/crtsh.py`, `sources/seedlist.py`,
      `probe.py`, `store.py`, `export.py`
- [ ] Create `backend/snihunter/data/seedlists/` with
      `safaricom-ke.txt`, `airtel-ke.txt`, `telkom-ke.txt` (curated
      from the public sources listed in §3.4 — Techfoe, aimtuto,
      snihost.com)
- [ ] Create `backend/snihunter/data/portal_indicators.txt` with the
      captive-portal redirect patterns
- [ ] Add `ALLOWED_SEEDLIST_EXTENSIONS = frozenset({".txt", ".csv", ".json"})`
      and a `_validate_seedlist_path()` helper in `main.py` (mirror of
      `_validate_config_path` with the seedlist extension set + 5 MiB
      cap)
- [ ] Add the 7 endpoints from §5.4 to `main.py`
- [ ] Add the `sni` namespace to `frontend/src/scripts/api.js`
- [ ] Add the `CMD.sni` subtree to `frontend/src/scripts/renderer.js`
- [ ] Add tests: `test_sni_candidate.py`, `test_sni_probe_result.py`,
      `test_crtsh_source.py`, `test_seedlist_loader.py`,
      `test_path_validation_seeds.py`
- [ ] Update `README.md` supported-formats table + API endpoints table
- [ ] Update `CHANGELOG.md` `[Unreleased]` → `### Added` section
- [ ] Update `docs/InjectX-Architecture.md` with the new
      `backend/snihunter/` module (also resolves backlog item N1, which
      says the architecture doc is stale)

**Phase 2 — UI module + CertStream + ECH detection:**

- [ ] Sidebar "05 · SNI HUNTER" module (mirror Arsenal dashboard)
- [ ] Live results table with verdict pills + click-to-filter
- [ ] "Use as SNI" button on working hosts → patches a config's `sni`
      field and re-parses
- [ ] `backend/snihunter/sources/certstream.py` — real-time CT monitor
- [ ] `backend/snihunter/dns_check.py` ECH capability detection
- [ ] Reverse IP lookup (BugScanX feature #4)
- [ ] Open port checker (BugScanX feature #7)

**Phase 3 — Defensive mode:**

- [ ] "Verify zero-rating enforcement" mode — given an ISP + a
      hostname, probe whether the ISP correctly blocks SNI spoofing
- [ ] nDPI-style SNI/Host-header mismatch detection
- [ ] Per-host TLS handshake-fingerprint comparison (does the cert
      chain change when SNI changes? — domain-fronting signal)

---

## 7. Legal and ethical considerations (MANDATORY READ)

This feature exists in a legally grey area. The implementing session
MUST read this section and address each point.

### 7.1 The dual-use reality

SNI bug-host hunting has two legitimate uses:

1. **Security research** — studying how ISPs implement zero-rating,
   measuring ECH adoption, verifying that ISP billing is correct.
2. **Personal free internet** — using zero-rated hosts to access the
   internet on a SIM the user already pays for, when their data plan
   is exhausted.

And one grey-area use:

3. **Bypassing paid data plans** — using zero-rated hosts to avoid
   paying for data the user would otherwise consume. This is
   ToS-violating in most jurisdictions but not criminal.

InjectX already straddles this line — its existing config decryption
pipeline (`.hc`, `.ehi`, `.hat`, etc.) is itself a dual-use tool, and
the project's existing stance (per the `README.md` "Research Sources"
section and Sessions 9/12/14/15/16) is that the user owns the
responsibility for how they use the tool. SNI Host Hunter inherits
that stance.

### 7.2 Design decisions that bias toward legitimate use

- **No bundled "exploit-ready" configs.** The feature discovers and
  probes hosts; it does not generate working VPN configs. The user
  must still take a discovered SNI and plug it into their own config.
- **Loopback-only egress.** The prober runs from the user's machine
  against the public internet — it is not a network scanner. The
  concurrency cap (200) and per-target rate limit (1 req/sec) make it
  unsuitable for DDoS or aggressive enumeration.
- **No automated captive-portal bypass.** The feature detects captive
  portals; it does not attempt to bypass them.
- **Documentation tone.** The `README.md` section for this feature
  should describe it as a "research and verification tool for SNI
  zero-rating", not as a "free internet hack".

### 7.3 What the feature explicitly does NOT do

- It does not modify the user's SIM, IMEI, or carrier account.
- It does not intercept other users' traffic.
- It does not exploit vulnerabilities in the ISP's infrastructure —
  it only sends well-formed TLS handshakes and HTTP requests to public
  hosts.
- It does not bypass DNS poisoning, GFW-style SNI blacklisting, or
  active censorship — those require different tooling (e.g., Trojan,
  V2Ray, which are already supported as config formats).

### 7.4 Documentation requirement

The `README.md` addition for this feature MUST include a
"Responsible Use" subsection linking to:

- The user's local ISP's terms of service (placeholder — the user
  fills in per their jurisdiction)
- RFC 9849 (ECH) — for context on why SNI inspection is a closing
  window
- The Compass Security SNI spoofing blog post — for the defensive
  perspective
- A clear statement that the tool is for personal research and that
  redistribution of working bug-host lists may violate ISP terms

---

## 8. Test strategy

### 8.1 Unit tests (must pass in CI without network)

- `test_sni_candidate.py` — construct from crt.sh fixture JSON, assert
  dedupe, assert wildcard stripping (`*.example.com` → `example.com`)
- `test_sni_probe_result.py` — verdict classification:
  - HTTP 200 → `working`
  - HTTP 302 to `captive.isp.com` → `blocked`
  - HTTP 302 to `other.example.com` → `redirect`
  - TLS handshake fails → `dead`
  - DNS fails → `dead`
- `test_crtsh_source.py` — mock `httpx.AsyncClient.get`, assert SAN
  parsing from multi-line `name_value`, assert issuer_ca_id
  propagation
- `test_seedlist_loader.py` — load `.txt` (one-per-line, `#`
  comments), `.csv` (with `domain` header), `.json` (array of
  `{domain, cloudflare}`); assert cloudflare_only filter; assert 5 MiB
  size cap raises 413; assert symlink-to-disallowed-extension raises
  400
- `test_path_validation_seeds.py` — extends
  `test_path_validation.py` pattern: `.txt` symlinked to `/etc/passwd`
  must reject

### 8.2 Integration tests (manual — require network)

Per the user's "verify each fix end-to-end" preference:

- `curl -X POST http://127.0.0.1:8742/api/sni/discover -d '{"domain":"example.com"}'`
  → returns at least 5 candidates (crt.sh always has results for
  well-known domains)
- `curl -X POST http://127.0.0.1:8742/api/sni/scan -d '{"seedlist_path":"/abs/path/to/test.txt","concurrency":10}'`
  → returns `job_id`, poll `/api/sni/jobs/{id}` until status=done,
  assert at least one `working` result
- `sni find cloudflare.com` in the terminal → prints a table
- `sni scan data/seedlists/safaricom-ke.txt` → progress streams to
  activity log, results table at end

### 8.3 Performance test (manual)

- 1000-host seedlist, concurrency=200, timeout=5s — should complete
  in under 60 seconds on a residential connection. If it doesn't,
  tune the asyncio event loop or drop concurrency.

---

## 9. Open questions for the user

These are flagged for the user to answer when an implementation
session starts. They are NOT blockers for the research itself.

1. **Seed list provenance.** Should the bundled `safaricom-ke.txt` /
   `airtel-ke.txt` / `telkom-ke.txt` lists be curated from public
   sources (Techfoe, aimtuto, snihost.com) and committed to git, or
   should they live in a separate `injectx-seedlists` repo the user
   pulls from? Committing them to the main repo means they ship with
   every release; a separate repo means the user can update them
   without an InjectX release.
2. **Default concurrency.** SNIbugtester defaults to 200; BugScanX
   doesn't expose a knob. Is 200 right for InjectX's typical user
   (residential connection, ~10 Mbps uplink), or should it be lower
   (say 50) to avoid tripping ISP rate-limiters?
3. **Captive-portal indicator list.** The initial list in
   `portal_indicators.txt` is best-effort. The user (who knows the
   Kenyan ISPs) should review and add patterns specific to Safaricom
   / Airtel / Telkom captive portals.
4. **Should the feature be in the main app or a separate "Pro" mode?**
   The decrypt pipeline is already grey-area; adding bug-host
   discovery on top may make the project more visibly dual-use. The
   user may prefer to gate it behind an env var (`INJECTX_ENABLE_SNI_HUNTER=1`)
   for the first few releases.
5. **ECH detection priority.** Given ECH adoption is accelerating
   (RFC 9849 published March 2026), should Phase 1 ship with a
   no-op ECH detection stub that just records whether the probed
   host advertised ECH support? This would future-proof the result
   data without adding implementation cost.

---

## 10. ADR-6 (proposed — for the implementing session to ratify)

> **Status:** proposed (not yet accepted — ratify in the implementing
> session's `plans/decisions.md` entry).

**ADR-6: SNI Host Hunter is a loopback-bound research tool, not a
network scanner (2026-07-24)**

- **Context:** The SNI Host Hunter feature (this spec) introduces an
  async prober that can issue hundreds of TLS handshakes per second.
  Without constraints, the same machinery could be used as a network
  scanner or for low-grade DDoS. The project's existing security
  stance (ADRs 1, 2, 5) is "loopback-only backend, extension
  allowlist, path validation" — the prober must inherit that stance.
- **Decision:**
  1. The prober runs only from the user's machine against the public
     internet. It is not a LAN scanner.
  2. Concurrency is hard-capped at 200 (SNIbugtester's default;
     matches the upper bound of residential connection capacity).
  3. Per-target rate limit: 1 request per second per hostname. A
     hostname probed twice in one second is rejected at the job
     store level.
  4. The prober does not support IP-range enumeration in MVP — only
     explicit hostname lists. (Reverse IP lookup, which takes one
     IP and lists its hostnames, is Phase 2 and uses public APIs
     like `https://api.hackertarget.com/reverseiplookup/?q=IP`,
     not active scanning.)
  5. The feature's `README.md` section documents these constraints
     and the rationale.
- **Consequences:**
  - The tool is unsuitable for abuse (concurrency cap, per-target
    rate limit, no IP-range mode) while remaining useful for its
    intended purpose (200 concurrent probes is plenty for a 1000-host
    seedlist).
  - Future agents MUST NOT raise the concurrency cap above 200
    without an explicit user decision recorded as a new ADR
    superseding this one.
  - Future agents MUST NOT add IP-range scanning without an explicit
    user decision — the feature's "research tool" framing depends on
    this.

---

## 11. References (primary sources, all verified 2026-07-24)

### 11.1 Standards & RFCs

- **RFC 9849 — TLS Encrypted Client Hello** (March 2026).
  https://datatracker.ietf.org/doc/rfc9849
- **RFC 6066 — TLS Extensions: Extension Definitions** (SNI
  specification). https://datatracker.ietf.org/doc/rfc6066
- **RFC 8701 — TLS GREASE** (compatibility testing). Not directly
  relevant to the feature but cited in the user's research context.

### 11.2 Reference tools (open-source)

- **BugScanX** — `pddung93/BugScanX` on GitHub;
  `pip install bugscan-x`. MIT license. The closest existing
  competitor; its 8-feature menu is the reference for the feature's
  scope. https://github.com/pddung93/BugScanX
- **SNIbugtester** — `Praveenhalder/SNIbugtester` on GitHub. MIT
  license. Android app with the best reference UX (live progress,
  thread control, results table, .csv export).
  https://github.com/Praveenhalder/SNIbugtester
- **certstream-python** — `CaliDog/certstream-python`. The maintained
  Python client for real-time CT log monitoring.
  https://github.com/CaliDog/certstream-python
- **crt.sh** (Sectigo's CT log search). JSON API at
  `https://crt.sh/?q=%.<domain>&output=json`. No auth, no rate limit
  in practice for reasonable use.
- **gotr00t0day/crt.sh** — Python wrapper around crt.sh with
  multiprocessing DNS resolution.
  https://github.com/gotr00t0day/crt.sh
- **HCTools/hcdecryptor** and **PANCHO7532/HCDecryptor** — already
  cited in `README.md` as InjectX's research sources for the
  existing decrypt pipeline. Not directly relevant to SNI Host
  Hunter but listed for completeness.

### 11.3 Defensive / ISP-side references

- **nDPI issue #2573** — "Adding support to detection: SNI Injection /
  SSL Tunnel / DNS". ntop's deep packet inspection library; the issue
  thread is a reference for what ISPs see when SNI spoofing happens.
  https://github.com/ntop/nDPI/issues/2573
- **Compass Security blog (March 2025)** — "Bypassing Web Filters
  Part 1: SNI Spoofing". Modern authoritative write-up of the attack
  side. https://blog.compass-security.com/2025/03/bypassing-web-filters-part-1-sni-spoofing
- **Enea insight (March 2025)** — "TLS 1.3 ECH — How to Preserve
  Visibility into Encrypted Traffic". Enterprise/ISP perspective on
  the ECH transition.

### 11.4 ECH deployment status (verified 2026-07-24)

- **OpenSSL post (2026-03-11)** — "The OpenSSL Library now supports
  Encrypted Client Hello (ECH)". https://openssl-library.org/post/2026-03-11-ech
- **NGINX blog** — "Encrypted Client Hello Comes to NGINX".
  https://blog.nginx.org/blog/encrypted-client-hello-comes-to-nginx
- **CDT (Center for Democracy & Technology) insight** — "Encrypted
  Client Hello: Closing the SNI Metadata Gap".
  https://cdt.org/insights/encrypted-client-hello-closing-the-sni-metadata-gap
- **Guardian Project (January 2025)** — "Using TLS ECH from Python".
  Working code example. https://guardianproject.info/2025/01/10/using-tls-ech-from-python

### 11.5 Africa / Kenya zero-rating context

- **Aimtuto** — "SNI Bug Host List & Zero-Rated Websites for All
  Countries" (updated 2025). Per-country lists including MTN, Cellc,
  Telkom, Airtel, Safaricom.
  https://www.aimtuto.com/2021/11/sni-host-list.html
- **Scribd** — "SNI host and Zero-Rated Websites" PDF, includes
  "Kenya SNI Bug Host List (Airtel, Safaricom)".
  https://www.scribd.com/document/578563989/Zero-Rated-Websites
- **snihost.com** — Live "Advanced SNI Bug Host Finder" web service
  with country/ISP picker. https://snihost.com
- **UNESCO zero-rating report (PDF)** — Confirms Safaricom zero-rated
  Longhorn and Visuasa e-learning platforms.
  https://media.unesco.org/sites/default/files/webform/gec003/zero-rating.pdf
- **Global Voices Advox — Free Basics in Kenya (PDF)** — Airtel
  offers Free Basics to all subscribers; Safaricom at 69% market
  share. https://advox.globalvoices.org/wp-content/uploads/2017/07/KENYA.pdf
- **Telkom South Africa zero-rated portal** — Confirms Telkom
  zero-rates educational URLs (TVET colleges, higher learning).
  https://group.telkom.co.za/about-us/zero-rated-portal.html
- **zerorating.wordpress.com/kenya** — Tracks Kenyan zero-rating
  offerings by operator.

### 11.6 Python ecosystem (libraries the feature depends on)

- **httpx** — async HTTP client. https://www.python-httpx.org
- **dnspython** — DNS resolution. https://www.dnspython.org
- **Python `ssl` module docs** — built-in TLS support.
  https://docs.python.org/3/library/ssl.html

---

## 12. Research provenance (raw artifacts)

The web-search and page-reader JSON dumps that produced this spec are
saved outside the repo at `/home/z/my-project/scripts/sni-research/`:

- `search_snitch.json` — searches for "SNItch SNI host discovery tool
  github" — found BugScanX and SNIbugtester instead (SNItch from the
  user's research context appears defunct).
- `search_crtsh.json` — crt.sh API + Python usage.
- `search_ech.json` — ECH deployment status; surfaced RFC 9849 +
  OpenSSL + NGINX references.
- `search_kenya_zerorating.json` — African ISP zero-rating context.
- `search_python_sni.json` — Python asyncio TLS probing patterns.
- `search_certstream.json` — certstream-python library confirmation.
- `search_sni_bypass.json` — modern SNI spoofing references; surfaced
  Compass Security blog + nDPI issue.
- `read_bugscanx.json` / `read_bugscanx_gh.json` — BugScanX PyPI +
  GitHub pages.
- `read_snibugtester.json` — SNIbugtester GitHub page.

A future implementation session that needs to re-verify any of these
findings can re-run the same searches (the queries are documented
above) and diff against these JSON dumps.

---

## 13. What this session did NOT do

To set expectations clearly:

- **No code was written.** The user's chat request was "do more
  research and save the context" — this spec is the saved context.
  The implementation is a separate session's job (see §6.5 phasing
  checklist).
- **No seedlist files were created.** The bundled `safaricom-ke.txt`
  etc. are described but not seeded — curating them is part of the
  implementing session (§9 question 1).
- **No ADR was ratified.** ADR-6 is proposed (§10) but not accepted;
  the implementing session must ratify it.
- **No tests were written.** The test plan is in §8.
- **No frontend code was touched.** The terminal command design is
  in §6.3 but not implemented.

The next session that picks this up should:

1. Read this file in full.
2. Read §6.5 (phasing checklist) and execute Phase 1.
3. Ratify ADR-6 (§10) by appending it to
   `.context/memory/plans/decisions.md`.
4. Answer the open questions in §9 (or proceed with the proposed
   defaults if the user is silent).
5. Use the seedlist-provenance question (§9.1) to decide whether to
   ship seedlists in-tree or in a sibling repo.
6. After Phase 1 ships, log the session in
   `.context/memory/agents/sessions.md` and update this file's status
   line at the top from "research + design" to "Phase 1 shipped,
   Phase 2 open".
