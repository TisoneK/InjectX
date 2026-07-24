# InjectX

Universal VPN tunnel config file reader — supports EHI, HC, HAT, DARK, TLS, ZIV, NPV4, NSH and more.

## Quick Start

### Prerequisites
- Python 3.8+
- Node.js 18+
- Electron

### Install

```bash
cd backend && pip install -r requirements.txt
cd .. && npm install
```

### Run

```bash
npm start  # Electron auto-spawns the Python backend
# Or debug backend separately:
cd backend && python main.py
```

### Sample Configs (assets/configs/)

Drop real VPN config files into the per-format subdirectories under
`assets/configs/` (e.g. `assets/configs/hc/myfile.hc`). The UI's
sidebar has an **IMPORT ASSETS** button that walks the tree and parses
every file in one batch — much faster than picking files one at a time.

For dev/test, set `INJECTX_AUTOIMPORT=1` to auto-import every file on
backend startup:

```bash
INJECTX_AUTOIMPORT=1 npm start
```

See `assets/configs/README.md` for the full layout.

## Supported Formats

| Format | App | Extension | Encrypted | Decryptor Available |
|--------|-----|-----------|-----------|---------------------|
| EHI | HTTP Injector | `.ehi` | Can be locked | Yes — scheme B1 (2-stage AES + field XOR) |
| HC | HTTP Custom | `.hc` | Yes | Yes — schemes A1–A4 (XOR + AES-128-ECB, 76+ keys) |
| HAT | HA Tunnel Plus | `.hat`, `.ha` | Yes | Yes — scheme E1 (AES-128-ECB) |
| DARK | DARK TUNNEL VPN | `.dark`, `.drak`, `.dt` | Can be locked | Yes — scheme I1 (base64 JSON envelope) |
| DarkTunnel | DarkTunnel | `.darktunnel` | No | N/A (in-app configs) |
| TLS | TLS Tunnel | `.tls` | Yes | Yes — scheme F1 (AES-256-GCM, key rotated) |
| ZIV | ZIVPN Tunnel | `.ziv` | Yes | Yes — scheme H1 (AES-256-GCM + PBKDF2) |
| NPV | NapsternetV | `.npv4`, `.inpv`, `.npv` | Yes | Yes — scheme C1 (subtraction cipher) |
| NSH | SocksHTTP | `.nsh` | Yes | Yes — scheme D1 (AES-128-GCM + PBKDF2) |
| VHD | V2Ray/NPV Tunnel | `.vhd` | Yes | Yes — scheme G1 (AES-128-CBC) |
| LNK | (various) | `.lnk` | Unknown | Detected only (no decryptor yet) |
| OVPN | OpenVPN | `.ovpn` | No | N/A (plain text, parser not yet implemented) |

The `/api/formats` endpoint is the authoritative, machine-readable version of this table — it reflects the v0.4 implementation exactly, including the scheme IDs (`A1`–`I1`) the decrypt router dispatches to.

## The Tunnelling App Ecosystem

### Two "Dark Tunnel" Apps (commonly confused)

| App | Package | Developer | Protocols | Config |
|-----|---------|-----------|-----------|--------|
| DarkTunnel | `net.darktunnel.app` | DarkTunnel team | SSH, DNSTT/SlowDNS, VMess, VLess, Trojan, Shadowsocks | In-app only |
| DARK TUNNEL VPN | `com.victo.dt` | Different dev | SSH, Proxy, SSL, DNS Tunnel, Xray, Hysteria | `.dark` files |

### Key Finding: Most Configs Are Encrypted

InjectX bundles its own decryptors (under `backend/decrypt/`),
researched from the open-source tools below. The current coverage:

- **HC** (`.hc`) — XOR + AES-128-ECB with 76+ known keys (schemes A1–A4).
- **EHI** (`.ehi`) — 2-stage AES + field-level XOR with custom base64 (scheme B1).
- **HAT** (`.hat`, `.ha`) — AES-128-ECB (scheme E1).
- **TLS** (`.tls`) — AES-256-GCM with `build_number:base64_payload` format (scheme F1).
- **NPV** (`.npv4`, `.inpv`, `.npv`) — subtraction cipher (scheme C1).
- **NSH** (`.nsh`) — AES-128-GCM + PBKDF2 (scheme D1).
- **VHD** (`.vhd`) — AES-128-CBC (scheme G1).
- **DARK** (`.dark`, `.drak`, `.dt`) — base64 JSON envelope with optional DRM lock (scheme I1).
- **ZIV** (`.ziv`) — AES-256-GCM + PBKDF2 (scheme H1, extracted from ZIVPN v2.1.5 APK).

### Research Sources

**HCTools/hcdecryptor** ([GitHub](https://github.com/HCTools/hcdecryptor)) — Python:
- HTTP Custom (`.hc`) only

**PANCHO7532/HCDecryptor** ([GitLab](https://gitlab.com/PANCHO7532/HCDecryptor)) — JavaScript, multi-format:
- HTTP Custom (`.hc`), HTTP Injector (`.ehi`), NapsternetV (`.npv4`, `.inpv`),
  SocksHTTP (`.nsh`), eProxy configs

Neither upstream tool supports `.hat`, `.dark`, or `.tls` files. InjectX's
HAT (E1), DARK (I1), and TLS (F1) decryptors are native implementations written
for this project. ZIV (H1) was reverse-engineered from the ZIVPN app APK
(Session 15). TLS remains blocked on a rotated key gated behind DexProtector
(Session 16 — dynamic Frida needed).

Note: Newer app versions may not be supported yet (see
[HCTools issue #4](https://github.com/HCTools/hcdecryptor/issues/4)).

## Project Structure

```
injectx/
├── assets/
│   └── configs/                 # Sample configs for batch import
│       ├── hc/                  # .hc files (HTTP Custom)
│       ├── ehi/                 # .ehi files (HTTP Injector)
│       ├── hat/                 # .hat / .ha files (HA Tunnel Plus)
│       ├── tls/                 # .tls files (TLS Tunnel)
│       ├── npv/                 # .npv4 / .inpv / .npv files (NapsternetV)
│       ├── nsh/                 # .nsh files (SocksHTTP)
│       ├── vhd/                 # .vhd files (V2Ray Tunnel)
│       ├── dark/                # .dark / .drak / .dt files (DARK TUNNEL)
│       ├── ziv/                 # .ziv files (ZIVPN)
│       ├── lnk/                 # .lnk files (various, detected only)
│       ├── ovpn/                # .ovpn files (OpenVPN)
│       └── README.md            # Layout docs
├── backend/
│   ├── parser/
│   │   ├── __init__.py          # Package exports
│   │   ├── detector.py          # Format detection (extension + content)
│   │   ├── ehi_parser.py        # HTTP Injector (.ehi)
│   │   ├── hc_parser.py         # HTTP Custom (.hc) — encrypted
│   │   ├── hat_parser.py        # HA Tunnel Plus (.hat) — encrypted
│   │   ├── tls_parser.py        # TLS Tunnel (.tls) — encrypted
│   │   ├── npv_parser.py        # NapsternetV (.npv4) — encrypted
│   │   ├── nsh_parser.py        # SocksHTTP (.nsh) — encrypted
│   │   ├── ziv_parser.py        # ZIVPN (.ziv) — encrypted
│   │   └── parse_engine.py      # Generic field mapping + normalization
│   ├── decrypt/
│   │   ├── hc_decrypt.py        # HC legacy A1-A4 (XOR + AES-128-ECB)
│   │   ├── hc_v27_decrypt.py    # HC v2.7+ A5 (ChaCha20 + RST + JKL)
│   │   ├── ehi_decrypt.py       # EHI B1 (2-stage AES + field XOR)
│   │   ├── ehi_v2_decrypt.py    # EHI v2 B2 (Argon2id + XXTEA + ChaCha20)
│   │   ├── hat_decrypt.py       # HAT E1 (AES-128-ECB)
│   │   ├── dark_decrypt.py      # DARK I1 (base64 JSON envelope)
│   │   ├── tls_decrypt.py       # TLS F1 (AES-256-GCM)
│   │   ├── ziv_decrypt.py       # ZIV H1 (AES-256-GCM + PBKDF2)
│   │   ├── npv_decrypt.py       # NPV C1 (subtraction cipher)
│   │   ├── nsh_decrypt.py       # NSH D1 (AES-128-GCM + PBKDF2)
│   │   ├── vhd_decrypt.py       # VHD G1 (AES-128-CBC)
│   │   ├── keys.py              # KeyStore (default keys + keyfile loading)
│   │   └── router.py            # Scheme dispatch router
│   ├── audit/
│   │   ├── trace.py             # Audit trail persistence
│   │   └── live_log.py          # In-memory live log buffer (polled by UI)
│   ├── snihunter/               # SNI Host Hunter (discover + probe bug hosts)
│   │   ├── models.py            # Parallel IR (SniCandidate/ProbeResult/ScanJob)
│   │   ├── sources/             # Discovery: crt.sh + seed lists
│   │   ├── probe.py             # Async TLS+HTTP+DNS prober + verdict logic
│   │   ├── store.py             # In-memory scan-job store
│   │   ├── export.py            # txt / csv / json exporters
│   │   └── data/seedlists/      # Bundled per-ISP seed lists (public hosts)
│   ├── tunnel/
│   │   └── __init__.py          # Future tunnel engine
│   ├── main.py                  # FastAPI server
│   └── requirements.txt
├── frontend/
│   ├── main.js                  # Electron main process
│   ├── preload.js               # Secure context bridge
│   ├── index.html               # App shell
│   └── src/
│       ├── styles/main.css      # Dark-themed UI
│       ├── scripts/api.js       # Backend communication
│       └── scripts/renderer.js  # UI logic
├── docs/
│   └── setup-guide.md           # Setup and running guide
├── package.json
└── README.md
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Check backend status |
| POST | `/api/config/upload` | Upload & parse a config file |
| GET | `/api/config/parse?filepath=` | Parse config from local path |
| GET | `/api/config/{id}` | Get parsed config by ID |
| GET | `/api/configs` | List all parsed configs |
| DELETE | `/api/config/{id}` | Delete a config |
| GET | `/api/config/detect?filepath=` | Detect format only |
| GET | `/api/config/export?config_id=` | Export normalized config |
| GET | `/api/config/{id}/trace` | Get the decrypt audit trace |
| GET | `/api/formats` | List supported formats |
| GET | `/api/logs?since=N` | Live log stream (poll for entries with id > N) |
| GET | `/api/configs/assets` | List files in `assets/configs/` (preview before import) |
| POST | `/api/configs/import-assets` | Batch-import every file in `assets/configs/` |
| POST | `/api/sni/discover` | Discover candidate SNI hosts for a domain (crt.sh) |
| POST | `/api/sni/scan` | Start a scan job over a seedlist and/or host list |
| POST | `/api/sni/scan/stop` | Stop a running scan job |
| GET | `/api/sni/jobs` | List scan jobs |
| GET | `/api/sni/jobs/{id}` | Get one job's state + results |
| GET | `/api/sni/seedlists` | List bundled per-ISP seed lists |
| POST | `/api/sni/export` | Export a job's results (txt / csv / json) |
| POST | `/api/sni/watch` | Watch the CertStream feed for new hosts (Phase 2) |
| POST | `/api/sni/ech` | Check a host's ECH capability via DNS HTTPS-RR (RFC 9848) |
| POST | `/api/sni/reverseip` | Reverse-IP lookup — sibling hostnames on an IP |
| POST | `/api/sni/portcheck` | Probe a small fixed set of common web ports on a host |
| POST | `/api/sni/apply` | Apply a discovered bug host to a parsed config ("use as SNI") |
| POST | `/api/sni/fronting` | Defensive: is SNI/Host zero-rating bypassable by domain fronting? (Phase 3) |

> **Note on `GET` vs `POST`:** `parse`, `detect`, and `export` are `GET`
> because they are idempotent (no server state mutation). The frontend's
> IPC handlers call them with default-fetch `GET`. See ADR-3 in
> `.context/memory/plans/decisions.md` for the rationale.

## SNI Host Hunter

The existing pipeline decodes the `sni` "bug host" out of a config you already
have. **SNI Host Hunter** finds those hosts for you and verifies which ones
actually work — closing the discover → probe → use loop.

- **Discover** candidate hostnames from **Certificate Transparency** logs
  (crt.sh) for a domain, or from bundled **per-ISP seed lists**
  (`backend/snihunter/data/seedlists/` — Safaricom / Airtel / Telkom Kenya to
  start).
- **Probe** each candidate: a real TLS handshake with the hostname as SNI, an
  HTTP request, and forward/reverse DNS cross-checks. Each result is classified
  `working` / `redirect` / `blocked` (ISP captive portal) / `dead`.
- **Export** the working hosts as `.txt` (one per line — drop straight into a
  config's `sni` field), `.csv`, or `.json`.

### Using it (terminal)

Open the **Terminal** module and run:

```
sni help                          # command reference
sni seedlists                     # list bundled per-ISP seed lists
sni find cloudflare.com           # discover candidates via crt.sh
sni scan safaricom-ke.txt         # probe a bundled seed list
sni scan example.com bbc.com      # probe hosts inline
sni scan /path/to/hosts.txt       # probe a seed list on disk (.txt/.csv/.json)
sni jobs                          # list scan jobs
sni stop <jobId>                  # stop a running scan
sni export <jobId> txt            # download working hosts
sni fronting <sni> <host>         # defensive: is SNI/Host zero-rating bypassable?
```

### Using it (sidebar UI)

The sidebar's **05 · SNI Hunter** module is the visual companion — it mirrors
the Arsenal dashboard pattern: a scan-config panel on the left, a live results
table on the right with verdict pills for click-to-filter. Three input modes:

1. **Seedlist dropdown** — pick one of the bundled per-ISP lists and START SCAN.
2. **FIND** — discover candidates via crt.sh, then auto-scan them.
3. **WATCH** — subscribe to the live CertStream feed for 60s and scan whatever
   new hostnames appear for the domain.

Each result row has four action buttons (working hosts only get the first):

- **Use as SNI** — apply this hostname to the currently-selected target config.
  The original SNI is preserved under `raw_data._original_sni` for revert, and
  a warning is added to the config's audit trail.
- **ECH** — check whether the host advertises ECH via its DNS HTTPS-RR (RFC
  9848). ECH-capable hosts are flagged as *less useful* bug-host candidates
  (the ISP can't see the SNI to whitelist-match it).
- **PORTS** — quick TCP probe of 80/443/8080/8443.
- **REV-IP** — reverse-IP lookup of sibling hostnames on the same IP
  (HackerTarget's free API, falling back to PTR).

Progress streams to the activity log while a scan runs. Concurrency is
hard-capped at 200 and each host is probed once per job (ADR-6) — it is a
research/verification tool, **not** a network scanner.

Set `INJECTX_ENABLE_SNI_HUNTER=0` to disable the feature wholesale (every
`/api/sni/*` endpoint then returns `403`).

### Defensive mode (Phase 3)

The offensive half finds hosts whose *SNI* an ISP zero-rates. The defensive half
asks the mirror question: **is that zero-rating bypassable by domain fronting?**
`sni fronting <sni> <host>` (or `POST /api/sni/fronting`, or the **DEFENSIVE
PROBE — FRONTING** panel at the bottom of the sidebar SNI Hunter module) opens a
TLS handshake with `sni` in the SNI extension but sends a mismatched
`Host: host` HTTP header, and reports:

- **verdict** — `enforced` (the server/CDN cross-checks SNI vs Host — e.g. a
  `421 Misdirected Request`), `bypassable` (the mismatch was served — the filter
  leaks), `indeterminate`, or `error`.
- **TLS fingerprint comparison** — whether the cert served changes when the SNI
  changes (SNI-based virtual hosting, harder to front) or stays a single default
  cert (fronting-friendly), plus whether the SNI's cert already covers the host.
- **DNS consistency** — whether `sni` and `host` resolve to a shared IP.

The sidebar panel renders the verdict as a color-coded banner (green = enforced,
red = bypassable) with a detail grid showing every field the backend captured
plus the backend's plain-language notes. The terminal command prints the same
fields as a table.

It is single-target, read-only, and non-exploitative (ADR-9) — a detector that
observes what the server does with a mismatched Host; it never tunnels or relays
traffic. References: nDPI issue #2573 (SNI/Host mismatch + domain fronting),
Compass Security's SNI-spoofing write-up.

### Responsible Use

SNI Host Hunter is a research and verification tool for SNI-based zero-rating.
Probing public hosts is legitimate; using a discovered zero-rated host to avoid
paying for data you would otherwise consume may violate your ISP's terms of
service, depending on your jurisdiction — that decision, and its consequences,
are yours. The bundled seed lists contain only **publicly documented** hosts
(Free Basics / operator / education portals); redistributing working bug-host
lists may itself violate ISP terms.

Context worth knowing: SNI inspection is a **closing window**.
[RFC 9849 (TLS Encrypted Client Hello)](https://datatracker.ietf.org/doc/rfc9849/)
and [RFC 9848 (bootstrapping ECH via DNS)](https://datatracker.ietf.org/doc/rfc9848/)
were published in 2026, and OpenSSL 4.0 / NGINX have landed ECH support — as ECH
adoption grows, the cleartext SNI that this technique depends on disappears. See
the defensive perspective in
[Compass Security: SNI Spoofing](https://blog.compass-security.com/2025/03/bypassing-web-filters-part-1-sni-spoofing/).

## Next Steps

1. **SNI Host Hunter** — Phase 1 (terminal MVP), Phase 2 (sidebar UI + CertStream
   + ECH + reverse-IP + port checks + "use as SNI"), and Phase 3 (defensive
   fronting probe, with sidebar UI) are all shipped — the feature is
   feature-complete. Follow-on: tune the captive-portal indicator list against
   live ISP portals. See `.context/memory/features/sni-host-hunter.md`.
2. **Parser coverage for `.ovpn`** — the detector recognises OpenVPN files but the parser is a stub; add a real OpenVPN config parser.
3. **Test infrastructure** — extend per-format parser/decryptor tests with sample files (see backlog item N3 in `.context/memory/tasks/backlog.md`).
4. **Build the tunnel engine** — add SSH, WebSocket, V2Ray/Xray, Hysteria tunneling support (currently `backend/tunnel/` is an empty package).
5. **Package for distribution** — use electron-builder to create Windows/macOS/Linux installers.
