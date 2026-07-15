# InjectX Sample Configs

Drop real VPN config files into the per-format subdirectories here.
The "IMPORT ASSETS" button in the UI walks this tree and parses every
file in one shot — no need to use the file picker one file at a time.

## Layout

```
assets/configs/
├── hc/      ← HTTP Custom (.hc)
├── ehi/     ← HTTP Injector (.ehi)
├── hat/     ← HA Tunnel Plus (.hat, .ha)
├── tls/     ← TLS Tunnel (.tls)
├── npv/     ← NapsternetV (.npv4, .inpv, .npv)
├── nsh/     ← SocksHTTP (.nsh)
├── vhd/     ← V2Ray/NPV Tunnel (.vhd)
├── dark/    ← DARK TUNNEL VPN (.dark, .drak, .dt)
└── ovpn/    ← OpenVPN (.ovpn)
```

## Usage

1. Copy your config files into the matching subdirectory.
2. Open the InjectX UI.
3. Click **IMPORT ASSETS** (next to ACQUIRE TARGET in the sidebar).
4. All files in `assets/configs/**` are parsed in one batch and show
   up as target cards in the Targets view.

## Auto-import on startup

Set the environment variable `INJECTX_AUTOIMPORT=1` to have the backend
auto-import every file in `assets/configs/` on startup — useful for
development/testing so you don't have to click the button every time.

```bash
INJECTX_AUTOIMPORT=1 npm start
```

## Git tracking

The `.gitkeep` files in each subdirectory are tracked so the tree
structure is preserved when the repo is cloned. The actual config
files are **not** ignored by default — if you want to keep your
personal configs out of git, add this to your `.git/info/exclude`:

```
assets/configs/**/*
!assets/configs/**/.gitkeep
```

Or commit a `.gitignore` inside each subdirectory. The bundled sample
`.hc` files in `hc/` are committed on purpose so the next clone has
real test data to verify the decryptor works.
