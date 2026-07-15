# InjectX

Universal VPN tunnel config file reader — supports EHI, HC, HAT, DARK, TLS, NPV4, NSH and more.

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
| DARK | DARK TUNNEL VPN | `.dark`, `.drak`, `.dt` | Yes | **None** (proprietary) |
| DarkTunnel | DarkTunnel | `.darktunnel` | No | N/A (in-app configs) |
| TLS | TLS Tunnel | `.tls` | Yes | Yes — scheme F1 (AES-256-GCM) |
| NPV | NapsternetV | `.npv4`, `.inpv`, `.npv` | Yes | Yes — scheme C1 (subtraction cipher) |
| NSH | SocksHTTP | `.nsh` | Yes | Yes — scheme D1 (AES-128-GCM + PBKDF2) |
| VHD | V2Ray/NPV Tunnel | `.vhd` | Yes | Yes — scheme G1 (AES-128-CBC) |
| OVPN | OpenVPN | `.ovpn` | No | N/A (plain text, parser not yet implemented) |

The `/api/formats` endpoint is the authoritative, machine-readable version of this table — it reflects the v0.4 implementation exactly, including the scheme IDs (`A1`–`G1`) the decrypt router dispatches to.

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
- **DARK** (`.dark`, `.drak`, `.dt`) — proprietary encryption, no public decryptor.

### Research Sources

**HCTools/hcdecryptor** ([GitHub](https://github.com/HCTools/hcdecryptor)) — Python:
- HTTP Custom (`.hc`) only

**PANCHO7532/HCDecryptor** ([GitLab](https://gitlab.com/PANCHO7532/HCDecryptor)) — JavaScript, multi-format:
- HTTP Custom (`.hc`), HTTP Injector (`.ehi`), NapsternetV (`.npv4`, `.inpv`),
  SocksHTTP (`.nsh`), eProxy configs

Neither upstream tool supports `.hat`, `.dark`, or `.tls` files. InjectX's
HAT (E1) and TLS (F1) decryptors are native implementations written
for this project; DARK remains unsupported (proprietary encryption with
no known public algorithm).

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
│       ├── ovpn/                # .ovpn files (OpenVPN)
│       └── README.md            # Layout docs
├── backend/
│   ├── parser/
│   │   ├── __init__.py          # Package exports
│   │   ├── detector.py          # Format detection (extension + content)
│   │   ├── ehi_parser.py        # HTTP Injector (.ehi)
│   │   ├── hc_parser.py         # HTTP Custom (.hc) — encrypted
│   │   ├── hat_parser.py        # HA Tunnel Plus (.hat) — encrypted
│   │   ├── dark_parser.py       # DARK TUNNEL VPN (.dark) — encrypted
│   │   ├── tls_parser.py        # TLS Tunnel (.tls) — encrypted
│   │   ├── npv_parser.py        # NapsternetV (.npv4) — encrypted
│   │   └── nsh_parser.py        # SocksHTTP (.nsh) — encrypted
│   ├── decrypt/
│   │   ├── hc_decrypt.py        # HC legacy A1-A4 (XOR + AES-128-ECB)
│   │   ├── hc_v27_decrypt.py    # HC v2.7+ A5 (ChaCha20 + RST + JKL)
│   │   └── ...                  # Other format decryptors
│   ├── audit/
│   │   ├── trace.py             # Audit trail persistence
│   │   └── live_log.py          # In-memory live log buffer (polled by UI)
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

> **Note on `GET` vs `POST`:** `parse`, `detect`, and `export` are `GET`
> because they are idempotent (no server state mutation). The frontend's
> IPC handlers call them with default-fetch `GET`. See ADR-3 in
> `.context/memory/plans/decisions.md` for the rationale.

## Next Steps

1. **Parser coverage for `.ovpn`** — the detector recognises OpenVPN files but the parser is a stub; add a real OpenVPN config parser.
2. **Test infrastructure** — add per-format parser/decryptor tests with sample files (see backlog item N3 in `.context/memory/tasks/backlog.md`).
3. **Build the tunnel engine** — add SSH, WebSocket, V2Ray/Xray, Hysteria tunneling support (currently `backend/tunnel/` is an empty package).
4. **Package for distribution** — use electron-builder to create Windows/macOS/Linux installers.
