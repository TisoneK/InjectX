# Changelog

All notable changes to InjectX are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Security
- Tightened input validation on the config-parsing API. Files outside the
  supported set of extensions (`.ehi`, `.hc`, `.hat`, etc.) are now rejected
  before being read, closing a path-traversal issue that affected local API
  callers.
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
  documented environment-variable contract.
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
