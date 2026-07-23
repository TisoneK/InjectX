# InjectX — Architecture Document

**Version:** 1.0 (Proposed Redesign)
**Status:** Draft
**Date:** 2026-05-16

---

## 1. Overview

InjectX is a desktop application for inspecting, decrypting, and normalizing VPN tunnel configuration files produced by Android tunneling apps. The primary user is someone who has received a `.ehi`, `.hc`, `.hat`, `.dark`, `.tls`, `.npv4`, or `.nsh` config file and wants to read its contents on a PC — without needing to import it into the original Android app.

The current v0.3.0 codebase has a working skeleton: Electron frontend + FastAPI backend + per-format parsers. However the backend parsers are mostly stubs, the decryption logic is not implemented, the UI is generic, and there is no tunnel engine. This document describes the full redesigned architecture.

---

## 2. Goals

| Goal | Description |
|------|-------------|
| **Decrypt** | Actually decrypt `.hc`, `.npv4`, `.nsh`, and `.ehi` files using known keys and algorithms |
| **Inspect** | Display all normalized config fields clearly: server, port, protocol, payload, credentials |
| **Detect** | Auto-detect file format from extension and content/magic bytes |
| **Export** | Export normalized config as clean JSON or plain text |
| **Inform** | Clearly flag encrypted formats where no public decryptor exists (`.hat`, `.dark`, `.tls`) |
| **Extend** | Provide a plugin-ready parser architecture for future format support |

### Out of Scope (v1)

- Actual tunnel/VPN connectivity (connecting through a config) — that is v2 work
- HAT, DARK, TLS decryption — no public algorithm is available
- Mobile client

---

## 3. Ecosystem Research Summary

### 3.1 Tunneling App Landscape

The supported file formats come from a family of Android tunneling apps popular in Africa, Southeast Asia, and South America, primarily used for ISP "free browsing tricks" via HTTP injection and SSH/V2Ray tunneling.

| App | Package | Config Format | Protocols | Encryption |
|-----|---------|---------------|-----------|------------|
| HTTP Injector | `com.evozi.injector` | `.ehi` | SSH, SSL, V2Ray/Xray, Hysteria, WireGuard, Shadowsocks | ZIP archive; payload optionally obfuscated |
| HTTP Custom | `com.httpcustom` | `.hc` | SSH, WebSocket, V2Ray | AES-ECB, key = MD5(known password) |
| HA Tunnel Plus | `com.artoftech.hatunnel` | `.hat`, `.ha` | SSH, WebSocket, V2Ray, SSL | Proprietary — no public decryptor |
| DARK TUNNEL VPN | `com.victo.dt` | `.dark`, `.drak`, `.dt` | SSH, Proxy, SSL, Xray, Hysteria | Proprietary — no public decryptor |
| DarkTunnel | `net.darktunnel.app` | `.darktunnel` | SSH, DNSTT, VMess, VLess, Trojan, Shadowsocks | In-app only; no exportable file |
| TLS Tunnel | `com.tlsvpn.tlstunnel` | `.tls` | TLS-based tunnel | Proprietary — no public decryptor |
| NapsternetV / NPV Tunnel | `com.napsternetv` | `.npv4`, `.inpv`, `.npv` | V2Ray (VMess/VLess), SSH, SlowDNS | Encrypted; Pancho7532 decryptor supports this |
| SocksHTTP | `com.sockshttp` | `.nsh` | SOCKS, HTTP proxy | Encrypted; Pancho7532 decryptor supports this |
| OpenVPN | various | `.ovpn` | OpenVPN | Plain text |

> **Note:** HTTP Injector v3 (2025) now natively supports V2Ray/Xray, Hysteria v2, WireGuard, and Shadowsocks directly inside `.ehi` files.

### 3.2 Known Decryption Algorithms

#### HTTP Custom (`.hc`) — HCTools/hcdecryptor

Reverse-engineered algorithm published at [github.com/HCTools/hcdecryptor](https://github.com/HCTools/hcdecryptor):

- **Type 0 (older versions):** Raw AES-ECB. Key = `MD5(password)`. Known passwords: `keY_secReaT_hc`, `hc_reborn1` through `hc_reborn10`.
- **Type 1 (reborn versions):** XOR obfuscation on a base64 string, then base64-decode, then AES-ECB. XOR key = `NAPmhZCCFV6PLmdb`. Passwords: `hc_reborn_1` through `hc_reborn___7`.
- Latest working key (as of 2025): `hc_reborn_4` (Play Store release), `hc_reborn___7` (public beta).
- Dependency: `pycryptodome`.

#### HTTP Injector (`.ehi`) — ZIP + optional obfuscation

- Standard `.ehi` is a renamed ZIP archive containing `HttpInjector.json` (or similar).
- "Locked" EHI files use a simple base64 obfuscation layer over the JSON.
- Pancho7532/HCDecryptor (GitLab) supports locked EHI files.

#### NapsternetV (`.npv4`, `.inpv`) — Pancho7532/HCDecryptor

- NPV4 files are encrypted; the algorithm was reverse-engineered by Pancho7532.
- Also supported: `.nsh` (SocksHTTP), `.ehi` (locked), eProxy configs.
- Source: [gitlab.com/PANCHO7532/HCDecryptor](https://gitlab.com/PANCHO7532/HCDecryptor)

#### No Public Decryptor

The following formats use **proprietary encryption with no known public algorithm**:

- `.hat` / `.ha` — HA Tunnel Plus (ArtOfTech)
- `.dark` / `.drak` / `.dt` — DARK TUNNEL VPN
- `.tls` — TLS Tunnel

InjectX will report these as "encrypted — no decryptor available" and show hex/entropy metadata only.

---

## 4. System Architecture

```
┌─────────────────────────────────────────────────┐
│                  Electron Shell                  │
│  ┌───────────────┐     ┌────────────────────┐   │
│  │  Renderer     │     │  Main Process      │   │
│  │  (index.html  │◄────│  (main.js)         │   │
│  │   renderer.js │     │  - spawns backend  │   │
│  │   api.js      │     │  - file dialogs    │   │
│  │   main.css)   │     │  - IPC bridge      │   │
│  └──────┬────────┘     └────────────────────┘   │
│         │ HTTP (localhost:8742)                  │
└─────────┼───────────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────────┐
│              Python Backend (FastAPI)            │
│                   main.py                        │
│                                                  │
│  ┌──────────────┐   ┌──────────────────────┐    │
│  │   Detector   │   │   Config Store       │    │
│  │  detector.py │   │   (in-memory dict)   │    │
│  └──────┬───────┘   └──────────────────────┘    │
│         │                                        │
│  ┌──────▼─────────────────────────────────────┐ │
│  │              Parser Registry               │ │
│  │                                            │ │
│  │  ehi_parser  hc_parser  hat_parser         │ │
│  │  dark_parser tls_parser npv_parser         │ │
│  │  nsh_parser  ovpn_parser                   │ │
│  └──────┬─────────────────────────────────────┘ │
│         │                                        │
│  ┌──────▼─────────────────────────────────────┐ │
│  │           Decryption Layer                 │ │
│  │                                            │ │
│  │  hc_decrypt.py   — AES-ECB + XOR (HCTools) │ │
│  │  ehi_decrypt.py  — base64 unlock           │ │
│  │  npv_decrypt.py  — Pancho7532 algorithm    │ │
│  │  nsh_decrypt.py  — Pancho7532 algorithm    │ │
│  └────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

### 4.1 Process Model

InjectX runs two OS processes:

| Process | Runtime | Role |
|---------|---------|------|
| Electron main | Node.js | Window management, file system dialogs, spawns Python, IPC bridge via `preload.js` |
| Python backend | Python 3.8+ | All parsing, decryption, format detection, config storage |

The Electron renderer communicates with the Python backend exclusively over HTTP on `localhost:8742`. There is no direct Node → Python IPC; the REST API is the contract boundary.

### 4.2 Security Model

- `contextIsolation: true` in Electron (already implemented via `preload.js`)
- CORS set to `allow_origins=["*"]` — acceptable since backend only binds to `127.0.0.1`
- No internet traffic; the app is entirely local
- Config files are copied to `~/.injectx/configs/` on upload and never sent anywhere

---

## 5. Backend

### 5.1 Directory Structure

```
backend/
├── main.py                   # FastAPI app, endpoints, lifespan
├── requirements.txt          # pycryptodome, fastapi, uvicorn, python-magic
├── parser/
│   ├── __init__.py           # exports: detect_format, detect_and_read
│   ├── detector.py           # format detection (extension + magic bytes + entropy)
│   ├── ehi_parser.py         # HTTP Injector (.ehi)
│   ├── hc_parser.py          # HTTP Custom (.hc) — calls hc_decrypt
│   ├── hat_parser.py         # HA Tunnel Plus (.hat) — encrypted, best-effort
│   ├── dark_parser.py        # DARK TUNNEL VPN (.dark) — encrypted, best-effort
│   ├── tls_parser.py         # TLS Tunnel (.tls) — encrypted, best-effort
│   ├── npv_parser.py         # NapsternetV (.npv4, .inpv) — calls npv_decrypt
│   ├── nsh_parser.py         # SocksHTTP (.nsh) — calls nsh_decrypt
│   └── ovpn_parser.py        # OpenVPN (.ovpn) — plain text (not yet implemented)
├── decrypt/
│   ├── __init__.py
│   ├── hc_decrypt.py         # AES-ECB with known key list (HCTools algorithm)
│   ├── ehi_decrypt.py        # base64 unlock for locked EHI files
│   ├── npv_decrypt.py        # NapsternetV decryption (Pancho7532 algorithm)
│   └── nsh_decrypt.py        # SocksHTTP decryption (Pancho7532 algorithm)
└── tunnel/
    └── __init__.py           # Stub — future tunnel engine
```

### 5.2 Decryption Module: `hc_decrypt.py`

The HC decryption algorithm, from HCTools/hcdecryptor:

```
Input: raw bytes of .hc file
Output: decrypted bytes (JSON), or None if all keys fail

For each (type, password) in KNOWN_KEYS:
  key = MD5(password.encode('utf-8'))     # 16-byte AES key
  if type == 0:
    plaintext = AES_ECB_decrypt(raw, key)
  elif type == 1:
    xored = XOR(raw, XOR_LIST)            # XOR_LIST = "NAPmhZCCFV6PLmdb"
    decoded = base64_decode(xored)
    plaintext = AES_ECB_decrypt(decoded, key)
  if plaintext is valid JSON:
    return plaintext
return None
```

Known key list (newest first, from `keylist.txt`):

```
Type 1: hc_reborn___7, hc_reborn_tester, hc_reborn_tester_5, hc_reborn_7,
        hc_reborn_6, hc_reborn_5, hc_reborn_4, hc_reborn_3, hc_reborn_2, hc_reborn_1
Type 0: hc_reborn10, hc_reborn9, hc_reborn8, hc_reborn7, keY_secReaT_hc,
        keY_secReaT_hc1, keY_secReaT_hc2, keY_secReaT_hc_reborn,
        keY_secReaT_hc_reborn1, keY_secReaT_hc_2, keY_secReaT_hc_reborn3,
        keY_secReaT_hc_reborn4, keY_secReaT_hc_reborn5
```

> **Limitation:** Newer HC versions (v233+) may use an updated key not yet in the public list. InjectX will report partial failure and show hex metadata in this case.

### 5.3 Format Detection: `detector.py`

Detection runs in two passes:

**Pass 1 — Extension lookup** (`EXTENSION_MAP`)

Maps `.ehi → ehi`, `.hc → hc`, `.hat → hat`, `.dark → dark`, `.npv4 → npv`, `.nsh → nsh`, etc.

**Pass 2 — Content validation**

After extension lookup, the detector validates the file content matches the expected format:

| Format | Validation method |
|--------|-------------------|
| `ehi` | `zipfile.is_zipfile()` must return True |
| `hc` | File exists and size > 0; check for `HCUST` magic header if present |
| `hat`, `dark`, `tls` | File exists and size > 0 (encrypted, can't validate content) |
| `npv` | File exists; try base64 decode as JSON, or VMess/VLess URI prefix |
| `ovpn` | Decoded text contains `client` or `dev tun` or `remote` |
| unknown | Entropy check: >180 unique bytes in first 512 → `encrypted_unknown` |

**Fallback — Content-only detection** (for files with missing/wrong extension)

Checks for ZIP magic bytes, JSON structure, base64→JSON, OpenVPN keywords, and high-entropy binary.

### 5.4 Normalized Config Schema

Every parser returns the same normalized dict regardless of source format:

```python
{
  # Identity
  "filepath": str,
  "filename": str,
  "format": str,             # "ehi" | "hc" | "hat" | "dark" | "tls" | "npv" | "nsh" | "ovpn"
  "encrypted": bool,
  "decryption_status": str,  # "success" | "failed" | "not_encrypted" | "no_decryptor"

  # Connection
  "host": str | None,
  "port": int | None,
  "protocol": str | None,   # "ssh" | "ssl" | "v2ray" | "vless" | "vmess" | "websocket" | "hysteria" | ...

  # SSH
  "ssh_server": str | None,
  "ssh_port": int | None,
  "ssh_user": str | None,
  "ssh_pass": str | None,
  "ssh_key": str | None,

  # Proxy
  "proxy_host": str | None,
  "proxy_port": int | None,

  # HTTP injection
  "payload": str | None,
  "payload_parsed": list,    # parsed HTTP header lines
  "custom_headers": dict,
  "sni": str | None,
  "bug_host": str | None,

  # DNS
  "dns": str | None,
  "remote_dns": str | None,

  # V2Ray / Xray
  "v2ray": dict | None,      # uuid, network, path, tls, etc.
  "vmess_config": dict | None,
  "vless_config": dict | None,
  "websocket": dict | None,

  # Metadata
  "errors": list[str],
  "warnings": list[str],
  "raw_data": dict | None,   # included when decryption fails
}
```

### 5.5 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Backend liveness check |
| `POST` | `/api/config/upload` | Upload a file (multipart), parse, and store |
| `POST` | `/api/config/parse` | Parse a file by local path |
| `GET` | `/api/config/{id}` | Retrieve parsed config by ID |
| `GET` | `/api/configs` | List all parsed configs (summary) |
| `DELETE` | `/api/config/{id}` | Remove config from store |
| `POST` | `/api/config/detect` | Detect format only, no parse |
| `POST` | `/api/config/export` | Export normalized config as JSON |
| `GET` | `/api/formats` | List all supported formats with metadata |

### 5.6 Dependencies (`requirements.txt`)

```
fastapi>=0.110.0
uvicorn>=0.29.0
python-multipart>=0.0.9
pycryptodome>=3.20.0        # AES-ECB decryption for .hc files
python-magic>=0.4.27        # MIME type detection from magic bytes
```

---

## 6. Frontend

### 6.1 Directory Structure

```
frontend/
├── main.js           # Electron main process: window, tray, backend spawn, file dialog
├── preload.js        # Context bridge (exposes safe API to renderer)
├── index.html        # App shell: sidebar + main content area
└── src/
    ├── styles/
    │   └── main.css  # Dark theme, sidebar, config cards, detail view, toast
    └── scripts/
        ├── api.js       # All fetch() calls to localhost:8742; wraps every endpoint
        └── renderer.js  # UI logic: views, drag-drop, config list, detail panel
```

### 6.2 View Structure

The frontend is a single-page app with four views, switched via sidebar navigation:

```
┌─────────────┬──────────────────────────────────────────┐
│  Sidebar    │  Main Content                            │
│             │                                          │
│  [logo]     │  view-home        Config list + dropzone │
│             │  view-detail      Single config fields   │
│  Configs    │  view-formats     Format reference table │
│  Formats    │  view-settings    Backend URL, tools     │
│  Settings   │                                          │
│             │                                          │
│  [Open]     │                                          │
└─────────────┴──────────────────────────────────────────┘
```

### 6.3 Context Bridge (`preload.js`)

The preload script exposes a minimal safe API on `window.injectx`:

```javascript
window.injectx = {
  openFile: ()   => ipcRenderer.invoke('open-file-dialog'),
  getPath: (key) => ipcRenderer.invoke('get-path', key),
  platform: process.platform,
}
```

File drag-and-drop is handled in the renderer via `dragover`/`drop` events on the drop zone. Dropped files are read as `File` objects and POSTed to `/api/config/upload` via `FormData`.

### 6.4 Config Detail View

When a config is selected, the detail view renders:

1. **Header bar** — filename, format badge, encrypted/decrypted badge, delete button
2. **Decryption status banner** — green (success), amber (partial), red (failed / no decryptor)
3. **Connection section** — host, port, protocol pill
4. **SSH section** — server, port, user, password (masked), key (truncated)
5. **Proxy section** — proxy host/port
6. **HTTP Injection section** — payload (monospace), SNI, bug host, custom headers table
7. **V2Ray section** — UUID, network type, path, TLS, WebSocket settings
8. **DNS section** — DNS server, remote DNS
9. **Raw data accordion** — hex preview and file size, shown only when decryption failed
10. **Export button** — downloads normalized JSON

### 6.5 Drag-and-Drop Flow

```
User drops file onto drop zone
  → renderer.js: handleFileDrop(file)
  → api.js: uploadConfig(file)           POST /api/config/upload
  → FastAPI: saves file, detects format, parses/decrypts
  → response: ConfigInfo JSON
  → renderer.js: addConfigCard(configInfo)
  → User clicks card
  → api.js: getConfig(id)               GET /api/config/{id}
  → renderer.js: renderDetailView(config)
```

---

## 7. Data Flow Diagram

```
File on disk (.ehi / .hc / .npv4 / ...)
        │
        ▼
  [Detector]  ─────────────────────────────────────┐
  Extension map + content validation                │
  → returns format string                           │
        │                                           │
        ▼                                           ▼
  [Parser]                               [Encrypted Unknown]
  calls format-specific parser           returns hex preview
        │                                + entropy metadata
        ▼
  [Decrypt layer]  (if format is encrypted)
  ├── .hc  → hc_decrypt.py   (AES-ECB + XOR, 23 known keys)
  ├── .ehi → ehi_decrypt.py  (base64 unlock)
  ├── .npv4 → npv_decrypt.py (Pancho7532 algorithm)
  ├── .nsh → nsh_decrypt.py  (Pancho7532 algorithm)
  └── .hat / .dark / .tls → None (no public decryptor)
        │
        ▼
  [Normalizer]
  Maps raw JSON fields → standard schema
  Detects protocol, parses payload headers
        │
        ▼
  Normalized config dict
  stored in config_store[id]
        │
        ▼
  REST response → Electron renderer → Detail view
```

---

## 8. Encryption Support Matrix

| Format | Extension(s) | Decryptable | Method | Key Source |
|--------|-------------|-------------|--------|------------|
| HTTP Injector | `.ehi` | ✅ Yes (standard) | ZIP + JSON | No key needed |
| HTTP Injector (locked) | `.ehi` | ✅ Yes | base64 unlock | No key needed |
| HTTP Custom | `.hc` | ✅ Yes (most versions) | AES-ECB + XOR | 23 known passwords |
| NapsternetV | `.npv4`, `.inpv`, `.npv` | ✅ Yes | Pancho7532 | Embedded in algorithm |
| SocksHTTP | `.nsh` | ✅ Yes | Pancho7532 | Embedded in algorithm |
| HA Tunnel Plus | `.hat`, `.ha` | ❌ No | Proprietary | Unknown |
| DARK TUNNEL VPN | `.dark`, `.drak`, `.dt` | ❌ No | Proprietary | Unknown |
| TLS Tunnel | `.tls` | ❌ No | Proprietary | Unknown |
| OpenVPN | `.ovpn` | ✅ Plain text | None needed | N/A |

---

## 9. File Format Reference

### EHI (HTTP Injector)

- **Container:** ZIP archive renamed to `.ehi`
- **Contents:** `HttpInjector.json` or similar JSON file
- **Fields of interest:** `payload`, `sshServer`, `sshPort`, `sshUser`, `sshPass`, `proxyIp`, `proxyPort`, `dns`, `remoteDns`, `sni`, V2Ray config object
- **Locked variant:** JSON is base64-encoded inside the ZIP entry
- **Modern (v3.x):** Supports V2Ray/Xray JSON config nested inside the EHI JSON

### HC (HTTP Custom)

- **Container:** Binary encrypted file
- **Magic:** May start with `HCUST` bytes (version-dependent)
- **Encryption:** AES-ECB, 16-byte key = MD5 of known password string
- **Type 1 variant:** Additionally XOR-obfuscated before base64 encoding
- **Decrypted payload:** JSON with fields like `connectionType`, `bugHost`, `sslFile`, `payload`, `customHeader`

### HAT (HA Tunnel Plus)

- **Container:** Encrypted binary
- **Note:** Play Store explicitly describes it as "an encrypted text file containing all the information that was defined before exporting it"
- **No public decryptor exists**

### DARK (DARK TUNNEL VPN)

- **Container:** Encrypted binary
- **App package:** `com.victo.dt` (different from DarkTunnel `net.darktunnel.app`)
- **Supports:** Xray, Hysteria, SSH, custom payload
- **No public decryptor exists**

### NPV4 (NapsternetV)

- **Container:** Encrypted binary
- **Changelog note:** "Changed config encryption algorithm. The app now uses npv4 configs" (v9.6)
- **Supports:** VMess, VLess, Shadowsocks, Trojan, SSH
- **Decryptable** via Pancho7532/HCDecryptor

### NSH (SocksHTTP)

- **Container:** Encrypted binary
- **Supports:** SOCKS proxy + HTTP tunnel
- **Decryptable** via Pancho7532/HCDecryptor

---

## 10. Future Work (v2+)

### 10.1 Tunnel Engine (`backend/tunnel/`)

The tunnel module is currently a stub. v2 will add a native tunnel engine:

| Protocol | Library | Priority |
|----------|---------|----------|
| SSH tunneling | `paramiko` | High |
| WebSocket proxy | `websockets` | High |
| V2Ray / Xray | subprocess (xray binary) | High |
| Shadowsocks | `shadowsocks-libev` subprocess | Medium |
| Hysteria | subprocess (hysteria binary) | Medium |
| WireGuard | `wireguard-tools` | Low |
| SlowDNS / DNSTT | subprocess | Low |

### 10.2 Persistent Config Storage

Replace in-memory `config_store` dict with SQLite via SQLAlchemy or raw `sqlite3`. This allows configs to persist across app restarts.

### 10.3 HAT / DARK / TLS Decryption

These formats remain closed. If a community reverse-engineer publishes an algorithm (similar to how HCTools reverse-engineered HC), the decrypt layer is designed to accept new modules without changing the parser interface.

### 10.4 OpenVPN Parser

The `.ovpn` format is plain text. The parser stub needs to be completed to extract: `remote`, `proto`, `port`, embedded `<ca>`, `<cert>`, `<key>` blocks, and connection flags.

### 10.5 Packaging

Use `electron-builder` for distribution:
- Windows: `.exe` installer (NSIS)
- macOS: `.dmg`
- Linux: `.AppImage`

Python backend should be bundled using `PyInstaller` and embedded in the Electron package so users do not need a Python installation.

---

## 11. Development Setup

```bash
# Clone and install
git clone https://github.com/yourname/injectx.git
cd injectx

# Backend
cd backend
pip install -r requirements.txt
python main.py          # starts on localhost:8742

# Frontend (separate terminal)
cd ..
npm install
npm start               # Electron auto-spawns backend via main.js
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `INJECTX_PORT` | `8742` | Backend port |
| `INJECTX_HOST` | `127.0.0.1` | Backend bind address |
| `INJECTX_UPLOAD_DIR` | `~/.injectx/configs` | Config upload directory |
| `NODE_ENV` | `production` | Set to `development` to enable DevTools |

---

## 12. Known Limitations

| Limitation | Affected Formats | Mitigation |
|-----------|-----------------|------------|
| No decryptor for proprietary formats | `.hat`, `.dark`, `.tls` | Show hex preview + entropy; direct user to community tools |
| HC newer versions (v233+) may use unknown key | `.hc` | Report partial failure; allow user to supply key manually (v2) |
| NPV4 encryption may have changed in very recent versions | `.npv4` | Best-effort; report failure clearly |
| No persistent storage | All | In-memory only; configs lost on restart (SQLite in v2) |
| EHI V2Ray configs not fully normalized | `.ehi` | V2Ray sub-object returned raw; full field mapping in v2 |
| No format support for eProxy, KTR, STK, TNL | — | Out of scope for v1 |

---

## 13. SNI Host Hunter (`backend/snihunter/`)

> Added 2026-07-24 (Phase 1). Design + rationale:
> `.context/memory/features/sni-host-hunter.md`; constraints: ADR-6/7/8 in
> `.context/memory/plans/decisions.md`.
>
> **Note:** the rest of this document predates several v0.4 changes and is
> being reconciled with the implementation (backlog N1). This section is
> written against the shipped Phase 1 code.

SNI Host Hunter is an **additive** module — a sibling to `parser/`,
`decrypt/`, and `audit/`. It reuses the FastAPI app, the live-log channel,
and the terminal command tree; it does not touch the config-parsing
pipeline or the `NormalizedConfig` IR.

### 13.1 Purpose

The parse pipeline decodes the `sni` bug host *out of* a config the user
already has. SNI Host Hunter **finds** such hosts and verifies which ones
pass an ISP's SNI-based zero-rating: discover → probe → export → paste back
into a config's `sni` field.

### 13.2 Module layout

```
backend/snihunter/
├── models.py          # SniCandidate / SniProbeResult / SniScanJob (parallel IR)
├── sources/
│   ├── crtsh.py       # crt.sh Certificate Transparency JSON API client
│   └── seedlist.py    # load bundled/user seed lists (.txt/.csv/.json)
├── probe.py           # async TLS+HTTP+DNS prober; pure classify_http() verdict
├── store.py           # in-memory scan-job store (mirrors config_store)
├── export.py          # txt / csv / json exporters
└── data/
    ├── seedlists/     # bundled per-ISP seed lists (public hosts, ADR-8)
    └── portal_indicators.txt  # captive-portal redirect substrings
```

`sources/` is the input side, `probe.py` the transform side, `store.py` the
state side, `models.py` the IR — the same split as `parser/` + `decrypt/`.

### 13.3 Parallel IR (why not extend `NormalizedConfig`)

A scan produces a list of per-host results over time — different cardinality
and lifecycle from a single parsed file. Folding it into `NormalizedConfig`
would break that IR's "one file on disk" invariant, so the scan models live
in `snihunter/models.py` instead. The only bridge is the existing `sni`
field on `NormalizedConfig` (Phase 2 "use this host").

### 13.4 Probe + verdict

For each candidate: forward DNS → TLS handshake (SNI = hostname, cert
captured) → HTTP GET → reverse-DNS consistency. `classify_http()` is a pure
function (unit-tested): `2xx`/`4xx` → `working`, `3xx` to a captive/top-up
portal → `blocked`, other `3xx` → `redirect`, DNS/TLS failure or `5xx` →
`dead`.

### 13.5 Security / abuse constraints (ADR-6)

- Concurrency hard-capped at `SNI_MAX_CONCURRENCY = 200`; each hostname is
  probed at most once per job (dedupe).
- No IP-range enumeration — only explicit hostname lists / crt.sh results.
- Seedlist paths go through `_validate_seedlist_path` — a mirror of
  `_validate_config_path` with a `.txt/.csv/.json` allowlist, the resolved-
  extension symlink re-check (ADR-5), and a 5 MiB cap.
- `INJECTX_ENABLE_SNI_HUNTER=0` disables every `/api/sni/*` endpoint (403).

### 13.6 Frontend

Terminal-only in Phase 1 (`sni find/scan/jobs/stop/export/seedlists/help`),
routed through the existing Electron IPC chain (renderer → `API.sni` →
preload → `main.js` → backend) — no direct renderer fetch (ADR-7). Progress
streams through the existing live-log channel, so the activity console shows
scan progress with no UI change. A sidebar module is Phase 2.

### 13.7 ECH — the sunset

This technique depends on the cleartext SNI extension. RFC 9849 (TLS
Encrypted Client Hello) and RFC 9848 (bootstrapping ECH via DNS) were
published in 2026, with OpenSSL 4.0 / NGINX support landing. The module is
built so its **discovery** half (CT logs) stays useful even after ECH makes
the **verification** half (active SNI probing) unreliable — see the feature
doc §3.3/§6.4.

---

*InjectX is a config inspection tool only. It does not facilitate unauthorized access to networks or circumvent carrier policies. All decryption algorithms are based on publicly available open-source reverse-engineering research. SNI Host Hunter probes public hosts for research and verification; see the README "Responsible Use" section.*
