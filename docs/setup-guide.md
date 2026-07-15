# InjectX — Setup & Running Guide

Complete guide for setting up, running, and developing InjectX on your local machine (Windows).

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Project Setup](#2-project-setup)
3. [Running the App](#3-running-the-app)
4. [Running Backend Only (for debugging)](#4-running-backend-only-for-debugging)
5. [Project Structure](#5-project-structure)
6. [How the App Works](#6-how-the-app-works)
7. [Adding a New Config Format Parser](#7-adding-a-new-config-format-parser)
8. [Integrating Decryptors for Encrypted Files](#8-integrating-decryptors-for-encrypted-files)
9. [Using the API Directly](#9-using-the-api-directly)
10. [Building for Distribution](#10-building-for-distribution)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. Prerequisites

You need these installed on your Windows machine:

| Tool | Minimum Version | Download | How to Verify |
|------|----------------|----------|---------------|
| **Python** | 3.8+ | [python.org](https://www.python.org/downloads/) | `python --version` |
| **Node.js** | 18+ | [nodejs.org](https://nodejs.org/) | `node --version` |
| **npm** | Comes with Node | Included | `npm --version` |
| **Git** | Any recent | [git-scm.com](https://git-scm.com/) | `git --version` |

### Python Installation Tips (Windows)

When installing Python on Windows:
- **Check "Add Python to PATH"** during installation — this is critical
- If you forgot, you can add it manually: `C:\Users\YourName\AppData\Local\Programs\Python\Python3xx\`
- Verify in Command Prompt or PowerShell:
  ```
  python --version
  pip --version
  ```

---

## 2. Project Setup

### Step 1: Create Your Project Folder

```powershell
mkdir C:\Projects\injectx
cd C:\Projects\injectx
```

### Step 2: Extract the Zip

Extract `injectx.zip` into that folder. Your structure should look like:

```
C:\Projects\injectx\
├── backend\
│   ├── parser\
│   │   ├── __init__.py
│   │   ├── detector.py
│   │   ├── ehi_parser.py
│   │   ├── hc_parser.py
│   │   ├── hat_parser.py
│   │   ├── dark_parser.py
│   │   ├── tls_parser.py
│   │   ├── npv_parser.py
│   │   └── nsh_parser.py
│   ├── tunnel\
│   │   └── __init__.py
│   ├── main.py
│   └── requirements.txt
├── frontend\
│   ├── main.js
│   ├── preload.js
│   ├── index.html
│   └── src\
│       ├── styles\main.css
│       └── scripts\
│           ├── api.js
│           └── renderer.js
├── docs\
│   └── setup-guide.md
├── package.json
└── README.md
```

### Step 3: Install Python Dependencies

```powershell
cd backend
pip install -r requirements.txt
```

This installs:
- `fastapi` — the web framework for the API server
- `uvicorn` — the ASGI server that runs FastAPI
- `python-multipart` — required for file uploads
- `pydantic` — data validation

Verify it worked:
```powershell
python -c "from parser import detect_format; print('OK')"
```

### Step 4: Install Electron and Node Dependencies

```powershell
cd C:\Projects\injectx
npm install
```

This downloads Electron (~80MB). It may take a few minutes on first install.

Verify it worked:
```powershell
npx electron --version
```

### Step 5: Initialize Git (Optional but Recommended)

```powershell
cd C:\Projects\injectx
git init
git add .
git commit -m "Initial commit - InjectX v0.3.0"
```

---

## 3. Running the App

### One-Command Start

```powershell
cd C:\Projects\injectx
npm start
```

What happens when you run this:
1. Electron starts and creates the app window
2. Electron spawns the Python backend as a child process (`python backend/main.py`)
3. Electron waits for the backend to be ready (checks port 8742)
4. The UI loads and connects to the backend automatically
5. You can now open config files via the "Open Config" button or `Ctrl+O`

### Opening Config Files

1. Click **"Open Config"** in the sidebar, or press `Ctrl+O`
2. Select one or more `.ehi`, `.hc`, `.hat`, `.dark`, `.tls`, `.npv4`, `.nsh` files
3. The app detects the format, parses what it can, and shows the results
4. Click any config card to see full details
5. Encrypted configs will show a warning with limited data

### Shutting Down

- Close the window normally — Electron automatically kills the Python backend on exit
- If the backend stays running (rare), kill it manually:
  ```powershell
  tasklist | findstr python
  taskkill /PID <pid> /F
  ```

---

## 4. Running Backend Only (for Debugging)

If you want to test the Python API separately from Electron:

### Terminal 1: Start the backend

```powershell
cd C:\Projects\injectx\backend
python main.py
```

You should see:
```
[InjectX] Backend starting...
[InjectX] Config upload directory: C:\Users\YourName\.injectx\configs
INFO:     Uvicorn running on http://127.0.0.1:8742
```

### Terminal 2: Test the API

```powershell
# Health check
curl http://127.0.0.1:8742/api/health

# List supported formats
curl http://127.0.0.1:8742/api/formats

# Parse a config file
curl "http://127.0.0.1:8742/api/config/parse?filepath=C:\path\to\config.ehi"
```

### Using the API Docs

Once the backend is running, open your browser:
- **Swagger UI**: http://127.0.0.1:8742/docs
- **ReDoc**: http://127.0.0.1:8742/redoc

These are auto-generated interactive API documentation pages.

---

## 5. Project Structure

```
injectx/
├── backend/                        # Python FastAPI backend
│   ├── parser/                     # Config file parsers
│   │   ├── __init__.py             #   Exports all parsers
│   │   ├── detector.py             #   Auto-detects file format
│   │   ├── ehi_parser.py           #   HTTP Injector (.ehi)
│   │   ├── hc_parser.py            #   HTTP Custom (.hc) — encrypted
│   │   ├── hat_parser.py           #   HA Tunnel Plus (.hat) — encrypted
│   │   ├── dark_parser.py          #   DARK TUNNEL VPN (.dark) — encrypted
│   │   ├── tls_parser.py           #   TLS Tunnel (.tls) — encrypted
│   │   ├── npv_parser.py           #   NapsternetV (.npv4) — encrypted
│   │   └── nsh_parser.py           #   SocksHTTP (.nsh) — encrypted
│   ├── tunnel/                     # Tunnel engine (future)
│   │   └── __init__.py
│   ├── main.py                     # FastAPI server entry point
│   └── requirements.txt            # Python dependencies
├── frontend/                       # Electron frontend
│   ├── main.js                     #   Main process (spawns Python, creates window)
│   ├── preload.js                  #   Context bridge (secure IPC)
│   ├── index.html                  #   App shell / entry page
│   └── src/
│       ├── styles/main.css         #   Dark theme stylesheet
│       ├── scripts/api.js          #   API client (talks to main process)
│       └── scripts/renderer.js     #   UI logic (views, interactions)
├── docs/                           # Documentation
│   └── setup-guide.md              #   This file
├── package.json                    # Node/Electron config
└── README.md                       # Project overview
```

---

## 6. How the App Works

### Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Electron App                      │
│                                                      │
│  ┌──────────────┐     IPC      ┌──────────────────┐ │
│  │   Renderer    │◄───────────►│   Main Process    │ │
│  │  (UI / HTML)  │   preload   │   (main.js)       │ │
│  │               │   .js       │                   │ │
│  │  renderer.js  │             │  Spawns Python    │ │
│  │  api.js       │             │  Proxies HTTP     │ │
│  └──────────────┘              └────────┬──────────┘ │
│                                          │            │
└──────────────────────────────────────────┼────────────┘
                                           │ HTTP
                                           │ (localhost:8742)
                                           ▼
                                ┌──────────────────────┐
                                │   Python Backend      │
                                │   (FastAPI/uvicorn)   │
                                │                       │
                                │   main.py             │
                                │   parser/             │
                                │     detector.py       │
                                │     ehi_parser.py     │
                                │     hc_parser.py      │
                                │     ...               │
                                └──────────────────────┘
```

### Data Flow

1. **User clicks "Open Config"** — Electron opens native file dialog
2. **User selects file(s)** — File path sent via IPC to main process
3. **Main process calls FastAPI** — `POST /api/config/parse?filepath=...`
4. **Backend detects format** — `detector.py` inspects extension + content
5. **Backend parses config** — Appropriate parser extracts and normalizes fields
6. **Result returned** — Normalized config data sent back to renderer
7. **UI displays result** — Config card appears in list, detail view shows fields

---

## 7. Adding a New Config Format Parser

Say you want to add support for a new format like `.xyz` (SomeNewApp):

### Step 1: Create the parser file

Create `backend/parser/xyz_parser.py`:

```python
"""XYZ (SomeNewApp) config parser."""
from pathlib import Path

def parse_xyz(filepath: str) -> dict:
    path = Path(filepath)
    raw = path.read_bytes()
    normalized = {
        "host": None, "port": None, "payload": None,
        "protocol": None, "_encryption_info": None, "raw_data": None,
    }
    # parsing logic here
    return normalized
```

### Step 2: Register in detector.py

Add the extension to `EXTENSION_MAP`, validation in `_validate_format()`, and the parser call in `detect_and_read()`.

### Step 3: Export from `__init__.py`

### Step 4: Register in FastAPI `/api/formats` endpoint

---

## 8. Integrating Decryptors for Encrypted Files

### What Can Be Decrypted

| Format | HCTools/hcdecryptor | Pancho7532/HCDecryptor |
|--------|--------------------|-----------------------|
| .hc (HTTP Custom) | Yes | Yes |
| .ehi (HTTP Injector) | No | Yes |
| .npv4 (NapsternetV) | No | Yes |
| .nsh (SocksHTTP) | No | Yes |
| .hat (HA Tunnel Plus) | No | **No** |
| .dark (DARK TUNNEL VPN) | No | **No** |
| .tls (TLS Tunnel) | No | **No** |

**Important**: .hat, .dark, and .tls have no public decryptor. The only way to read these is from within the respective apps.

### Option A: Python Version (HCTools) — .hc files only

```powershell
cd backend
pip install git+https://github.com/HCTools/hcdecryptor.git
```

Then replace the `_try_hc_decrypt` stub in `hc_parser.py`:

```python
def _try_hc_decrypt(raw: bytes) -> Optional[bytes]:
    try:
        from hcdecryptor import decrypt
        return decrypt(raw)
    except Exception:
        return None
```

### Option B: JavaScript Version (PANCHO7532) — Multi-format

Supports .hc, .ehi, .npv4, .nsh, eProxy:

```powershell
cd C:\Projects\injectx
npm install git+https://gitlab.com/PANCHO7532/HCDecryptor.git
```

Then call from Electron's main process.

### Important Notes

- Newer app versions (HTTP Custom v233+) may not be supported yet
- Always test with real config files from your device
- The decryptors are community-maintained and may break when apps update their encryption

---

## 9. Using the API Directly

### Health Check

```powershell
curl http://127.0.0.1:8742/api/health
```
```json
{"status": "ok", "version": "0.3.0"}
```

### Detect Format

```powershell
curl "http://127.0.0.1:8742/api/config/detect?filepath=C:\configs\myfile.ehi"
```

### Parse a Config

```powershell
curl "http://127.0.0.1:8742/api/config/parse?filepath=C:\configs\myfile.ehi"
```

### Upload a Config File

```powershell
curl -X POST -F "file=@C:\configs\myfile.hc" http://127.0.0.1:8742/api/config/upload
```

---

## 10. Building for Distribution

To package InjectX as a standalone `.exe` installer for Windows:

```powershell
npm install --save-dev electron-builder
```

Add a `"build"` section to `package.json`, then:

```powershell
npx electron-builder --win
```

**Important**: Electron-builder packages the Node/Electron app, but **not Python**. You need to either:
1. Use PyInstaller to compile `main.py` into a standalone `.exe`
2. Or require Python to be installed on the target machine

---

## 11. Troubleshooting

### "python" is not recognized
Python isn't in your PATH. Reinstall and check "Add to PATH".

### Backend doesn't start
1. Run backend manually: `cd backend && python main.py`
2. Install dependencies: `pip install -r requirements.txt`
3. Kill stuck process: `netstat -ano | findstr :8742` then `taskkill /PID <pid> /F`

### Config shows as "encrypted_unable_to_decrypt"
This is expected for `.hc`, `.hat`, `.dark`, `.tls`, `.npv4`, `.nsh` files. These formats use proprietary encryption. Only .hc, .ehi, .npv4, and .nsh have known decryptors.

### npm install fails
```powershell
npm config set electron_mirror https://npmmirror.com/mirrors/electron/
npm install
```

---

## Quick Reference Card

| Task | Command |
|------|---------|
| Install Python deps | `cd backend && pip install -r requirements.txt` |
| Install Node deps | `npm install` |
| Run the full app | `npm start` |
| Run backend only | `cd backend && python main.py` |
| Run in dev mode | `npm run start:dev` (opens DevTools) |
| API docs | http://127.0.0.1:8742/docs |
| Health check | `curl http://127.0.0.1:8742/api/health` |
| Kill stuck backend | `tasklist \| findstr python` then `taskkill /PID <pid> /F` |
