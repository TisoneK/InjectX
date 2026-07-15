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

## Supported Formats

| Format | App | Extension | Encrypted | Decryptor Available |
|--------|-----|-----------|-----------|---------------------|
| EHI | HTTP Injector | `.ehi` | Can be locked | HCDecryptor, Pancho7532 |
| HC | HTTP Custom | `.hc` | Yes | HCDecryptor, Pancho7532 |
| HAT | HA Tunnel Plus | `.hat`, `.ha` | Yes | **None** (proprietary) |
| DARK | DARK TUNNEL VPN | `.dark`, `.drak`, `.dt` | Yes | **None** (proprietary) |
| DarkTunnel | DarkTunnel | `.darktunnel` | No | N/A (in-app configs) |
| TLS | TLS Tunnel | `.tls` | Yes | **None** (proprietary) |
| NPV | NapsternetV | `.npv4`, `.inpv`, `.npv` | Yes | Pancho7532 |
| NSH | SocksHTTP | `.nsh` | Yes | Pancho7532 |
| OVPN | OpenVPN | `.ovpn` | No | N/A (plain text, not yet implemented) |

## The Tunnelling App Ecosystem

### Two "Dark Tunnel" Apps (commonly confused)

| App | Package | Developer | Protocols | Config |
|-----|---------|-----------|-----------|--------|
| DarkTunnel | `net.darktunnel.app` | DarkTunnel team | SSH, DNSTT/SlowDNS, VMess, VLess, Trojan, Shadowsocks | In-app only |
| DARK TUNNEL VPN | `com.victo.dt` | Different dev | SSH, Proxy, SSL, DNS Tunnel, Xray, Hysteria | `.dark` files |

### Key Finding: Most Configs Are Encrypted

Research revealed that most tunneling apps encrypt their config files:
- **HC files** use the HCUST encryption format. Decryptor: [HCTools/hcdecryptor](https://github.com/HCTools/hcdecryptor)
- **HAT files** are "encrypted text files" (per Play Store description) — no public decryptor exists
- **DARK/TLS files** use proprietary encryption — no public decryptor exists
- **NPV4/NSH files** are encrypted — Pancho7532/HCDecryptor supports both

### Decryptor Tools

**HCTools/hcdecryptor** ([GitHub](https://github.com/HCTools/hcdecryptor)) — Python:
- HTTP Custom (`.hc`) only

**PANCHO7532/HCDecryptor** ([GitLab](https://gitlab.com/PANCHO7532/HCDecryptor)) — JavaScript, multi-format:
- HTTP Custom (`.hc`)
- HTTP Injector (`.ehi`)
- NapsternetV (`.npv4`, `.inpv`)
- SocksHTTP (`.nsh`)
- eProxy configs

**Important**: Neither decryptor supports `.hat`, `.dark`, or `.tls` files. Those formats use proprietary encryption with no known public decryption method.

Note: Newer app versions may not be supported yet (see [HCTools issue #4](https://github.com/HCTools/hcdecryptor/issues/4)).

## Project Structure

```
injectx/
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
| POST | `/api/config/parse?filepath=` | Parse config from local path |
| GET | `/api/config/{id}` | Get parsed config by ID |
| GET | `/api/configs` | List all parsed configs |
| DELETE | `/api/config/{id}` | Delete a config |
| POST | `/api/config/detect?filepath=` | Detect format only |
| POST | `/api/config/export?config_id=` | Export normalized config |
| GET | `/api/formats` | List supported formats |

## Next Steps

1. **Integrate HCDecryptor** — Add hcdecryptor as a dependency for encrypted .hc files
2. **Integrate Pancho7532/HCDecryptor** — Add support for .ehi, .npv4, .nsh decryption
3. **Test with real configs** — Validate parsers against actual config files from each app
4. **Build tunnel engine** — Add SSH, WebSocket, V2Ray/Xray, Hysteria tunneling support
5. **Package for distribution** — Use electron-builder to create Windows/macOS/Linux installers
