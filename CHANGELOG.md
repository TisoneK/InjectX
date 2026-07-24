# Changelog

All notable changes to InjectX are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **SNI Host Hunter Phase 2** — the SNI Hunter is now a full sidebar module
  (05 · SNI HUNTER), not just terminal commands. A scan-config panel on the
  left, a live results table on the right with verdict pills (working /
  redirect / blocked / dead) for click-to-filter. Three input modes: pick a
  bundled seedlist, discover via crt.sh (FIND), or watch the live CertStream
  feed for 60s (WATCH). Each result row has four actions: **Use as SNI**
  (apply the host to your currently-selected config — the original SNI is
  preserved for revert), **ECH** (check whether the host advertises Encrypted
  Client Hello via its DNS HTTPS-RR per RFC 9848 — ECH-capable hosts are less
  useful as bug hosts), **PORTS** (quick 80/443/8080/8443 probe), and
  **REV-IP** (sibling hostnames on the same IP via HackerTarget). New
  backend modules: `snihunter/dns_check.py` (ECH detection), `sources/certstream.py`
  (real-time CT watch), `reverseip.py`, `portcheck.py`, `apply.py` ("use as
  SNI"). Five new `/api/sni/*` endpoints. 60 new tests (suite 91→151).
  `dnspython` added to requirements for SVCB/HTTPS-RR queries.
- **SNI Host Hunter** — InjectX can now *find* working bug hosts, not just
  read the ones you already have. From the Terminal, `sni find <domain>`
  looks up candidate hosts for a domain, and `sni scan` checks a list of
  hosts to see which ones actually work — testing each and labelling it
  working, redirected, blocked, or dead, with progress in the activity log.
  It comes with starter host lists for Safaricom, Airtel, and Telkom Kenya,
  and you can export the working hosts to a file to drop into your config.
  It is a research and verification tool — please read the "Responsible
  Use" note in the README. Type `sni help` for the full command list.
- Open a whole folder of configs at once (new "Open Folder" button, or
  `targets openfolder` / `targets import <folder>` in the terminal), and
  the app remembers it — the pickers reopen where you last were, and your
  last folder is reloaded automatically the next time you launch, like an
  IDE reopening your last project.
- The Terminal can point at files anywhere on your machine, not just
  loaded ones: `targets info`/`targets debug` accept a file path, quoted
  paths with spaces work, and `targets pick` opens the file picker. The
  Terminal also gained Copy/Clear buttons and a copy button per line.
- The **Terminal** now understands real commands with arguments —
  `targets list`, `targets debug <id|name>`, `targets purge <id|name|all>`,
  `targets info/open/export/import/count`, plus `logs`, `system`, and
  `assets import`. Type `help` (or `targets help`) for the full list.
- The **Arsenal** page is now a live dashboard: a summary of formats and
  decode counts, an accurate status for every format, and per-format
  counts of how many of your loaded configs decoded — click a format to
  jump to those targets.
- The **Logs** page can now copy the whole log, and each line has its own
  copy button.
- A **Terminal** module in the sidebar — a full-size command console.
- The activity log can now be **collapsed** to a thin rail (toggle in its
  header), giving the output the full window width.
- A confirmation dialog when you close the app, so an accidental close
  doesn't discard your decoded configs.
- On the decoded page, the header and the Export/Purge buttons now stay
  pinned to the top and bottom while you scroll through the output.
- Copy buttons throughout the decoded view. Hover any key value — the
  server/host, proxy, SSH credentials, SNI, or any decoded field — and a
  copy icon appears to put it on your clipboard in one click. Activity-log
  lines are copyable too.

### Fixed
- The header clock now shows your local time instead of UTC.
- Header labels no longer get clipped on a narrow window.
- Exporting a config now includes everything that was decoded. Previously
  only HTTP Custom configs exported fully; HTTP Injector, ZIVPN, and DARK
  Tunnel exports came out nearly empty because their fields were dropped.
  Now every decoded field is in the exported JSON.

### Changed
- The "Import Assets" button (which loads bundled sample configs) is now
  hidden in the packaged app — those are development samples, so the app
  works only from your own file selections. It still appears when running
  from source.
- Redesigned the decoded-config view. The activity log now sits in a
  panel on the right instead of across the bottom, giving results the
  full height of the window. Decoded configs now lead with big tiles for
  the key details (server, port, protocol), lay the sections out in two
  columns to use the space, and show a complete "Decoded Fields" table —
  so you can read everything a config contains without exporting JSON.
  Author notes (including HTTP Injector and ZIVPN messages) now display
  in-place, and the raw-JSON viewer collapses again by default.

### Added
- ZIVPN (`.ziv`) configs now decode again. Newer ZIVPN builds changed the
  secret password used to lock config files, which had left every `.ziv`
  file unreadable. The current password was recovered and all bundled
  ZIVPN configs now decrypt, showing the server (e.g. `udpsg3.zivpn.com`)
  and their settings.
- DARK Tunnel (`.dark`) configs are now readable. They were previously
  written off as using "proprietary encryption," but the file is really
  a wrapped, plainly-encoded package: the app type (VLESS/VMESS/Trojan),
  the config name, and the transport are all readable, and for configs
  the author did not lock, the full server details too. When the author
  *locked* the config, those credentials stay sealed (that's the app's
  intended protection) and the app now says so clearly instead of
  showing nothing.
- You can now supply your own decryption keys at runtime without
  rebuilding the app. Point the `INJECTX_KEYFILE` environment variable
  at a JSON file of keys and they're used alongside the built-in ones.
  This is how newly recovered keys get applied when an app changes the
  secret it uses to lock its config files — for example, to bring TLS
  Tunnel or HA Tunnel configs back to life once a current key is found.
  A new guide, `docs/key-extraction.md`, walks through recovering those
  keys.

### Fixed
- TLS Tunnel (`.tls`) configs from newer app builds no longer fail to
  process before decryption is even attempted. These files drop the
  trailing padding on their encoded payload, which made the app give up
  early and report the file as unreadable rather than as key-protected.
  The bundled TLS samples still can't be decoded because newer TLS
  Tunnel builds changed their secret key and no public key for them
  exists yet — but the app now handles the file correctly and reports
  the real reason.
- The desktop app's main process now respects a custom `INJECTX_PORT`
  (or `INJECTX_HOST`) when spawning and proxying to the Python backend.
  Previously a custom port silently broke every renderer call — the
  backend bound to the new port but the proxy kept targeting the
  default. Default-port users were unaffected.
- The decrypt-audit log can now actually persist to disk. The
  persistence path called a deprecated serialization method that
  raised an error on Pydantic v2; the error was silently swallowed,
  so opt-in file-backed logging produced no files. The in-memory path
  was unaffected. No caller currently opts in.
- Configs whose protocol cannot be identified from their fields now
  show "unknown" in the UI instead of being mislabeled as SSH.
- The "Open Config File" dialog now lists OpenVPN (`.ovpn`) and
  generic `.conf` files under the "VPN Config Files" filter, matching
  what the backend accepts.
- The `/api/formats` capability list is accurate again. It had fallen
  behind the code: it still claimed HTTP Custom could only decrypt the
  legacy schemes (missing the v2.7+ decryptor), listed HTTP Injector as
  unencrypted with only the old decryptor (missing the v6.3+ one), and
  omitted the ZIVPN and `.lnk` formats entirely.

### Changed
- Internal: added automated parsing tests over every bundled sample
  config (32 files across HTTP Custom, HTTP Injector, ZIVPN, DARK
  Tunnel, and TLS Tunnel), so parser changes are caught by the test
  suite instead of only by manual spot-checks.
- Internal: the file-backed audit log serialization now uses the
  Pydantic v2 `model_dump_json()` method, completing the v2 migration
  that had already handled `model_dump()`.
- Internal: removed a few unused variables and a duplicate dictionary
  key in the backend (decryptor + parser). No behavior change.
- Internal: added a `pyproject.toml` for the backend, configuring
  pytest (test discovery + strict markers), ruff (style + bug rules,
  passing clean today), and mypy (type checks, informational at this
  point). Sets up the project for future CI.

### Docs
- Corrected the README's API table (parse / detect / export are `GET`,
  not `POST`) and added the missing `/api/config/{id}/trace` endpoint.
- Corrected the README's "Supported Formats" table: HAT and TLS do
  have working decryptors in InjectX (only DARK is unsupported).
  Added the missing VHD row.
- Refreshed the README's "Next Steps" to reflect what's actually
  done vs pending.

### Security
- Tightened input validation on the config-parsing API. Files outside the
  supported set of extensions (`.ehi`, `.hc`, `.hat`, etc.) are now rejected
  before being read, closing a path-traversal issue that affected local API
  callers.
- Closed a follow-up gap in that same extension check: a shortcut (symlink)
  named like a supported config but pointing at an unrelated file is now
  rejected based on where it actually points, not just its name.
- Restricted the backend's CORS policy to the origins the desktop app
  actually uses (the Electron `file://` origin and the loopback), instead
  of allowing any origin.
- Added a 50 MB size cap on uploaded config files. Config files are
  kilobyte-scale; larger uploads are rejected before they reach disk.

### Fixed
- The "Export Normalized JSON" button in the config detail view no longer
  silently fails. The export endpoint was unreachable due to a route
  registration ordering issue; this has been corrected.
- The format-detection API is now reachable from the frontend (same route
  ordering fix).

### Changed
- Internal: migrated the IR serialization calls from Pydantic v2's
  deprecated `.dict()` method to `.model_dump()`. Removes log noise and
  prepares for Pydantic v3.
- The backend now honors `INJECTX_HOST`, `INJECTX_PORT`, and
  `INJECTX_UPLOAD_DIR` for its runtime configuration, matching the
  documented environment-variable contract. When a custom port is set, the
  allowed local origins now follow that port instead of the default.
- Internal: replaced a deprecated Pydantic serialization setting with the
  supported equivalent, removing warning noise and preparing for Pydantic v3.
- Internal: the backend now uses the `logging` module for startup and
  shutdown messages instead of `print()`, with timestamps and severity
  levels.
- Internal: synced `package-lock.json` to `package.json` v0.4.0 (was
  stale at v0.2.0).

## [0.4.0] — prior to 2026-07-15

The v0.4 baseline as it existed at the start of the first `.context/`
session. Notable features already present:

- Multi-feature format detector (Shannon entropy, byte distribution skew,
  ASCII ratio, ZIP magic, base64 likelihood, null byte ratio).
- Scheme-router-based decryption with 8 schemes (A1-A4, B1, C1, D1, E1,
  F1, G1) covering HC, EHI, NPV, NSH, HAT, TLS, VHD.
- Versioned IR (`NormalizedConfig` with `ir_version="1.0"`) as the
  canonical contract between backend and frontend.
- Audit trace (`DecryptTrace`) recording every decrypt attempt with
  confidence scoring.
- Electron frontend with custom title bar, config list, detail view,
  formats browser, and settings view.
- 76+ known encryption keys sourced from HCTools/hcdecryptor and
  Pancho7532/HCDecryptor research.

No changelog was kept for changes prior to v0.4.0.
