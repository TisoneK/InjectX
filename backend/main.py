"""
InjectX — FastAPI Backend v0.4

Architecture: Detector → Scheme Router → Decryptor → Parse Engine → NormalizedConfig IR

Key changes from v0.3:
  - All endpoints return versioned IR objects
  - Decryption uses the Scheme Router (not hardcoded parser-decryptor coupling)
  - Detection uses multi-feature classifier
  - Full audit trail via DecryptTrace
  - Confidence-based decrypt selection
"""

import os
import sys
import uuid
import asyncio
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone
from contextlib import asynccontextmanager
import glob

# Ensure backend/ is on sys.path so absolute imports (ir.models, parser, etc.) work
# whether run as `python backend/main.py` or `cd backend && python main.py`
_BACKEND_DIR = Path(__file__).resolve().parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from parser import detect_format, detect_with_features, parse_config
from parser.detector import EXTENSION_MAP
from ir.models import (
    IR_VERSION,
    NormalizedConfig,
    FormatEnum,
    DecryptStatusEnum,
)
from audit.live_log import get_live_log

# SNI Host Hunter (feature: discover + probe SNI bug hosts). Kept in its own
# package sibling to parser/decrypt/audit — see .context/memory/features/
# sni-host-hunter.md and ADR-6/7/8 in plans/decisions.md.
from snihunter import (
    SNI_MAX_CONCURRENCY,
    apply_sni_to_config_id,
    check_ech as sni_check_ech,
    check_ports as sni_check_ports,
    discover as sni_discover,
    list_bundled_seedlists,
    load_seedlist,
    reverseip_lookup as sni_reverseip,
    scan as sni_scan,
    sni_job_store,
    watch_certstream as sni_watch_certstream,
)
from snihunter.models import SniCandidate, SniScanJob
from snihunter.export import export_job

logger = logging.getLogger("injectx")
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


# ── Configuration ─────────────────────────────────────────────────────────────

HOST = os.environ.get("INJECTX_HOST", "127.0.0.1")
PORT = int(os.environ.get("INJECTX_PORT", "8742"))
UPLOAD_DIR = Path(os.environ.get("INJECTX_UPLOAD_DIR", str(Path.home() / ".injectx" / "configs")))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Project-local sample-config tree. The UI's "IMPORT ASSETS" button
# walks this and parses every file in one batch — much faster than
# picking files one at a time when you have many to test. Set
# INJECTX_AUTOIMPORT=1 to do the same on backend startup.
ASSETS_CONFIGS_DIR = Path(__file__).resolve().parent.parent / "assets" / "configs"
AUTOIMPORT = os.environ.get("INJECTX_AUTOIMPORT", "").lower() in ("1", "true", "yes", "on")

# Cap on uploaded file size — 50 MiB. Config files for the supported formats
# are kilobyte-scale; anything larger is almost certainly not a config file.
MAX_UPLOAD_BYTES = 50 * 1024 * 1024

# Extensions accepted by the path-based endpoints (`/parse`, `/detect`) and
# the upload endpoint. Anything else is rejected at the API boundary —
# /etc/passwd, ~/.ssh/id_rsa, and similar targets have no .ehi extension and
# must not be parseable through InjectX.
ALLOWED_EXTENSIONS: frozenset[str] = frozenset({
    ".ehi", ".hc", ".hat", ".ha", ".dark", ".drak", ".dt", ".darktunnel",
    ".tls", ".npv4", ".inpv", ".npv", ".nsh", ".vhd", ".ovpn", ".conf",
    ".ziv", ".lnk",
})

# In-memory config store (keyed by ID → NormalizedConfig dict)
config_store: dict[str, dict] = {}

# ── SNI Host Hunter configuration ─────────────────────────────────────────────

# Extensions accepted for user-supplied seed-list files. Kept SEPARATE from
# ALLOWED_EXTENSIONS (which is config-file-only) so a seedlist path can't be
# used to smuggle in a config-file read and vice-versa (ADR-1/ADR-5 spirit).
ALLOWED_SEEDLIST_EXTENSIONS: frozenset[str] = frozenset({".txt", ".csv", ".json"})

# Seedlists are kilobyte-scale; cap at 5 MiB so a hostile 50 MiB list can't
# queue millions of probes (design doc §4.4).
MAX_SEEDLIST_BYTES = 5 * 1024 * 1024

# The feature is dual-use (design doc §7). It ships ENABLED by default (the app
# is already a dual-use decrypt tool), but can be turned off wholesale by
# setting INJECTX_ENABLE_SNI_HUNTER=0 — every /api/sni/* endpoint then 403s.
SNI_HUNTER_ENABLED = os.environ.get("INJECTX_ENABLE_SNI_HUNTER", "1").strip().lower() not in (
    "0", "false", "no", "off",
)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_config_path(filepath: str) -> Path:
    """
    Validate a user-supplied filepath for the /parse and /detect endpoints.

    Returns the resolved Path on success. Raises HTTPException on rejection.

    Checks (in order):
      1. Path is non-empty and absolute (no implicit cwd resolution).
      2. Extension is in the allowlist (blocks /etc/passwd, id_rsa, etc.).
      3. Path resolves to a real file (no broken symlinks, no missing).
      4. File is under MAX_UPLOAD_BYTES (caps work on hostile inputs).

    Note: the desktop app's file dialog already filters by extension, but the
    HTTP endpoint is reachable by any local process. The extension check is
    the primary defence; the size check is a backstop.
    """
    if not filepath or not filepath.strip():
        raise HTTPException(status_code=400, detail="No filepath provided")

    raw = Path(filepath)
    if not raw.is_absolute():
        raise HTTPException(status_code=400, detail=f"Path must be absolute: {filepath}")

    ext = raw.suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension '{ext}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    # Resolve symlinks/`..` segments to detect traversal attempts. `strict=True`
    # raises if the path doesn't exist on disk.
    try:
        resolved = raw.resolve(strict=True)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {filepath}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid path: {e}")

    # Re-check the extension of the RESOLVED target, not just the path the
    # caller supplied. A symlink named `x.ehi` -> `/etc/passwd` passes the
    # first extension check (the link ends in .ehi) but resolves to a file
    # with a disallowed extension. Without this second check the allowlist is
    # bypassable and the endpoint becomes an arbitrary-file-read oracle again.
    resolved_ext = resolved.suffix.lower()
    if resolved_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Symlink target has unsupported extension '{resolved_ext}'",
        )

    if not resolved.is_file():
        raise HTTPException(status_code=400, detail=f"Not a file: {filepath}")

    try:
        size = resolved.stat().st_size
    except OSError:
        raise HTTPException(status_code=500, detail=f"Could not stat file: {filepath}")
    if size > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size} bytes); max {MAX_UPLOAD_BYTES} bytes",
        )
    if size == 0:
        raise HTTPException(status_code=400, detail=f"File is empty: {filepath}")

    return resolved


def _validate_seedlist_path(filepath: str) -> Path:
    """Validate a user-supplied seed-list path for /api/sni/scan.

    Mirrors `_validate_config_path` (absolute → allowlisted extension →
    resolve(strict) → re-check resolved extension → size cap) but against the
    seedlist extension set and the 5 MiB seedlist cap. The resolved-extension
    re-check closes the same symlink bypass ADR-5 fixed for config paths: a
    `.txt` symlink pointing at `/etc/passwd` must be rejected.
    """
    if not filepath or not filepath.strip():
        raise HTTPException(status_code=400, detail="No seedlist path provided")

    raw = Path(filepath)
    if not raw.is_absolute():
        raise HTTPException(status_code=400, detail=f"Path must be absolute: {filepath}")

    ext = raw.suffix.lower()
    if ext not in ALLOWED_SEEDLIST_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported seedlist extension '{ext}'. Allowed: {sorted(ALLOWED_SEEDLIST_EXTENSIONS)}",
        )

    try:
        resolved = raw.resolve(strict=True)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Seedlist not found: {filepath}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid path: {e}")

    if resolved.suffix.lower() not in ALLOWED_SEEDLIST_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Symlink target has unsupported extension '{resolved.suffix.lower()}'",
        )

    if not resolved.is_file():
        raise HTTPException(status_code=400, detail=f"Not a file: {filepath}")

    try:
        size = resolved.stat().st_size
    except OSError:
        raise HTTPException(status_code=500, detail=f"Could not stat file: {filepath}")
    if size > MAX_SEEDLIST_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Seedlist too large ({size} bytes); max {MAX_SEEDLIST_BYTES} bytes",
        )
    if size == 0:
        raise HTTPException(status_code=400, detail=f"Seedlist is empty: {filepath}")

    return resolved


def _require_sni_enabled() -> None:
    if not SNI_HUNTER_ENABLED:
        raise HTTPException(
            status_code=403,
            detail="SNI Host Hunter is disabled. Set INJECTX_ENABLE_SNI_HUNTER=1 to enable it.",
        )


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Backend v0.4 starting (IR version %s)...", IR_VERSION)
    logger.info("Config upload directory: %s", UPLOAD_DIR)
    logger.info("Assets configs directory: %s", ASSETS_CONFIGS_DIR)

    # Optional auto-import on startup. Useful for dev/test so you don't
    # have to click IMPORT ASSETS every time. Disabled by default.
    if AUTOIMPORT:
        n = _import_assets_synchronously()
        if n > 0:
            logger.info("Auto-imported %d config(s) from %s", n, ASSETS_CONFIGS_DIR)

    yield
    logger.info("Backend shutting down...")


def _import_assets_synchronously() -> int:
    """Walk assets/configs/** and parse every file. Returns count imported.

    Called from lifespan (auto-import) and from the /api/configs/import-assets
    endpoint (manual import via UI button).
    """
    if not ASSETS_CONFIGS_DIR.exists():
        return 0

    from audit.live_log import get_live_log
    live_log = get_live_log()

    count = 0
    # Walk every file under assets/configs/**/*
    for path in sorted(ASSETS_CONFIGS_DIR.rglob("*")):
        if not path.is_file():
            continue
        if path.name == ".gitkeep" or path.name == "README.md":
            continue
        ext = path.suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            live_log.add("SKIP", f"Skipping {path.relative_to(ASSETS_CONFIGS_DIR)} — unsupported extension '{ext}'", "warn")
            continue

        live_log.add("ACQUIRE", f"Importing {path.relative_to(ASSETS_CONFIGS_DIR)}", "info")
        try:
            config_id = str(uuid.uuid4())[:8]
            normalized = parse_config(str(path))
            config_store[config_id] = normalized.model_dump()
            count += 1

            fmt = normalized.format if isinstance(normalized.format, str) else normalized.format.value
            status_raw = normalized.decryption_status
            status = status_raw if isinstance(status_raw, str) else status_raw.value
            live_log.add("OK", f"Imported {path.name} · {fmt.upper()} · {status.upper()}", "info")
        except Exception as e:
            live_log.add("ERR", f"Failed to import {path.name}: {e}", "err")

    return count


# ── App Setup ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="InjectX API",
    version="0.4.0",
    lifespan=lifespan,
)

# CORS — the backend binds to 127.0.0.1 only, but any local process can
# still issue requests. Restrict origins to the ones the Electron renderer
# actually uses: `file://` (the default Electron loadFile origin) and the
# loopback origin. `allow_credentials=False` because no auth/cookies are
# used; the wildcard origin + credentials combo is also invalid per CORS
# spec (browsers reject it).
#
# Note: `file://` pages send `Origin: null` per the Fetch spec, so we
# include the string "null" in the allowlist. This is safe because the
# backend binds to 127.0.0.1 only — no remote origin can reach it.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://127.0.0.1:{PORT}",
        f"http://localhost:{PORT}",
        "file://",
        "null",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)


# ── Response Models ───────────────────────────────────────────────────────────

class ConfigInfo(BaseModel):
    """API response model — wraps the IR for HTTP transport."""
    id: str
    ir_version: str = IR_VERSION
    filename: str
    format: str
    encrypted: bool = False
    decryption_status: str = "not_encrypted"
    scheme_used: Optional[str] = None
    confidence: float = 0.0
    config: Optional[dict] = None
    errors: list[str] = []
    warnings: list[str] = []
    decrypt_trace: Optional[dict] = None


class StatusResponse(BaseModel):
    status: str
    version: str = "0.4.0"
    ir_version: str = IR_VERSION


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ir_to_response(config_id: str, normalized: NormalizedConfig) -> ConfigInfo:
    """Convert NormalizedConfig IR to API response model."""
    config_dict = None
    if normalized and any(v is not None for k, v in normalized.model_dump().items()
                         if k not in ("filepath", "filename", "format", "ir_version",
                                      "is_encrypted", "decryption_status", "scheme_used",
                                      "errors", "warnings", "raw_data", "decrypt_trace")):
        # Include only non-None, non-metadata fields.
        # We DO include raw_data here because format-specific extras (HC v2.7
        # notes/protections/_all_fields, HAT protextras, etc.) live there —
        # the UI needs them to render the full config.
        config_dict = {}
        exclude_keys = {"filepath", "filename", "format", "ir_version", "is_encrypted",
                       "decryption_status", "scheme_used", "errors", "warnings",
                       "decrypt_trace", "payload_parsed"}
        for k, v in normalized.model_dump().items():
            if k not in exclude_keys and v is not None:
                config_dict[k] = v

    trace_dict = None
    if normalized.decrypt_trace:
        trace_dict = normalized.decrypt_trace.model_dump()

    confidence = 0.0
    if normalized.decrypt_trace and normalized.decrypt_trace.winning_scheme:
        confidence = 1.0  # Winner found
    elif normalized.decryption_status == DecryptStatusEnum.NOT_ENCRYPTED:
        confidence = 1.0

    return ConfigInfo(
        id=config_id,
        ir_version=normalized.ir_version,
        filename=normalized.filename,
        format=normalized.format if isinstance(normalized.format, str) else normalized.format.value,
        encrypted=normalized.is_encrypted,
        decryption_status=normalized.decryption_status if isinstance(normalized.decryption_status, str) else normalized.decryption_status.value,
        scheme_used=normalized.scheme_used if isinstance(normalized.scheme_used, str) or normalized.scheme_used is None else normalized.scheme_used.value,
        confidence=confidence,
        config=config_dict,
        errors=normalized.errors,
        warnings=normalized.warnings,
        decrypt_trace=trace_dict,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "0.4.0", "ir_version": IR_VERSION}


@app.post("/api/config/upload", response_model=ConfigInfo)
async def upload_config(file: UploadFile = File(...)):
    """Upload a config file, detect format, decrypt, and parse.

    Validates filename extension against the same allowlist as /parse and
    /detect, and caps uploaded size at MAX_UPLOAD_BYTES. Rejects before
    touching disk so a hostile upload can't pollute UPLOAD_DIR.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension '{ext}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    config_id = str(uuid.uuid4())[:8]
    save_path = UPLOAD_DIR / f"{config_id}{ext}"

    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read upload: {str(e)}")

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Uploaded file too large ({len(content)} bytes); max {MAX_UPLOAD_BYTES} bytes",
        )

    try:
        save_path.write_bytes(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Full pipeline: detect → decrypt → parse → normalize
    normalized = parse_config(str(save_path))
    config_store[config_id] = normalized.model_dump()

    return _ir_to_response(config_id, normalized)


@app.get("/api/config/parse", response_model=ConfigInfo)
async def parse_config_file(filepath: str = Query(..., description="Absolute path to config file")):
    """Parse a config file from a local file path.

    Validates the path against an extension allowlist + size cap before
    reading — the endpoint is reachable by any local process, not just the
    Electron renderer, so /etc/passwd and similar targets must be rejected.
    """
    path = _validate_config_path(filepath)

    config_id = str(uuid.uuid4())[:8]
    normalized = parse_config(str(path))
    config_store[config_id] = normalized.model_dump()

    return _ir_to_response(config_id, normalized)


@app.get("/api/config/detect")
async def detect_config_format(filepath: str = Query(..., description="Path to config file")):
    """Detect format with multi-feature classification vector.

    Same path validation as /parse — the endpoint must not be a file-read
    oracle for arbitrary paths. Changed from POST to GET to match the
    frontend's actual usage (`fetch(url)` defaults to GET); detection is
    idempotent so GET is the correct semantic.

    Route ordering: must be registered BEFORE /api/config/{config_id} or
    the parameterized route shadows it (config_id='detect').
    """
    path = _validate_config_path(filepath)
    result = detect_with_features(str(path))
    return result.model_dump()


@app.get("/api/config/export")
async def export_normalized_config(config_id: str = Query(...), format: str = Query("json", description="Export format: json")):
    """Export a parsed config in normalized JSON format.

    Changed from POST to GET to match the frontend's actual usage
    (`fetch(url)` defaults to GET); export is idempotent so GET is the
    correct semantic.

    Route ordering: must be registered BEFORE /api/config/{config_id} or
    the parameterized route shadows it (config_id='export') and the
    renderer's Export button silently 404s.
    """
    if config_id not in config_store:
        raise HTTPException(status_code=404, detail=f"Config not found: {config_id}")

    data = config_store[config_id]
    normalized = NormalizedConfig(**data)
    dumped = normalized.model_dump()

    # Export excludes the verbose decrypt_trace. It KEEPS the decoded
    # raw_data — that's where formats other than HC (HTTP Injector, ZIVPN,
    # DARK) keep most of their fields (_all_fields); dropping it made those
    # exports look empty while HC (which maps everything to top-level IR
    # fields) exported fully. Only the debug-only keys, which appear on
    # failed decodes, are stripped from raw_data.
    raw = dumped.get("raw_data")
    if isinstance(raw, dict):
        raw = {k: v for k, v in raw.items()
               if k not in ("file_size", "hex_preview", "features", "detected_header")}

    export = {k: v for k, v in dumped.items()
              if k not in ("raw_data", "decrypt_trace") and v is not None}
    if raw:
        export["raw_data"] = raw

    return {"config_id": config_id, "ir_version": IR_VERSION, "export_format": format, "data": export}


@app.get("/api/config/{config_id}", response_model=ConfigInfo)
async def get_config(config_id: str):
    """Retrieve a previously parsed config by ID."""
    if config_id not in config_store:
        raise HTTPException(status_code=404, detail=f"Config not found: {config_id}")

    data = config_store[config_id]
    normalized = NormalizedConfig(**data)
    return _ir_to_response(config_id, normalized)


@app.get("/api/configs")
async def list_configs():
    """List all previously parsed configs."""
    configs = []
    for config_id, data in config_store.items():
        configs.append({
            "id": config_id,
            "filename": data.get("filename", ""),
            "format": data.get("format", "unknown"),
            "encrypted": data.get("is_encrypted", False),
            "decryption_status": data.get("decryption_status", "unknown"),
            "scheme_used": data.get("scheme_used"),
            "has_errors": bool(data.get("errors")),
        })
    return {"configs": configs, "total": len(configs), "ir_version": IR_VERSION}


@app.delete("/api/config/{config_id}")
async def delete_config(config_id: str):
    """Delete a parsed config from the store."""
    if config_id not in config_store:
        raise HTTPException(status_code=404, detail=f"Config not found: {config_id}")
    del config_store[config_id]
    return {"status": "deleted", "id": config_id}


@app.get("/api/formats")
async def supported_formats():
    """List all supported config file formats."""
    return {
        "ir_version": IR_VERSION,
        "formats": [
            {"id": "ehi", "name": "HTTP Injector", "extensions": [".ehi"], "encrypted": True, "decryptable": True, "schemes": ["B2", "B1"], "description": "ZIP/binary config; B2 = v6.3+ (Argon2id + ChaCha20-Poly1305 + XXTEA + 2-stage AES), B1 = legacy 2-stage AES"},
            {"id": "hc", "name": "HTTP Custom", "extensions": [".hc"], "encrypted": True, "decryptable": True, "schemes": ["A5", "A1", "A2", "A3", "A4"], "description": "Encrypted HCUST format; A5 = v2.7+ (initial XOR + ChaCha20 + AES-ECB), A1-A4 = legacy XOR + AES-128-ECB (76+ known keys)"},
            {"id": "hat", "name": "HA Tunnel Plus", "extensions": [".hat", ".ha"], "encrypted": True, "decryptable": True, "schemes": ["E1"], "description": "AES-128-ECB encrypted JSON (2 known keys, profile/profilev4/configuration structures)"},
            {"id": "dark", "name": "DARK TUNNEL VPN", "extensions": [".dark", ".drak", ".dt"], "encrypted": True, "decryptable": True, "schemes": ["I1"], "description": "darktunnel:// base64(JSON) envelope decoded (type/name/transport); author-locked configs keep credentials sealed in encryptedLockedConfig"},
            {"id": "tls", "name": "TLS Tunnel", "extensions": [".tls"], "encrypted": True, "decryptable": True, "schemes": ["F1"], "description": "AES-256-GCM with build_number:base64_payload format (keys rotated in newer builds)"},
            {"id": "npv", "name": "NapsternetV", "extensions": [".npv4", ".inpv", ".npv"], "encrypted": True, "decryptable": True, "schemes": ["C1"], "description": "Subtraction cipher (charCode subtraction with cycling key)"},
            {"id": "nsh", "name": "SocksHTTP", "extensions": [".nsh"], "encrypted": True, "decryptable": True, "schemes": ["D1"], "description": "AES-128-GCM + PBKDF2 with dot-separated salt.iv.ciphertext_mac format"},
            {"id": "vhd", "name": "V2Ray/NPV Tunnel", "extensions": [".vhd"], "encrypted": True, "decryptable": True, "schemes": ["G1"], "description": "AES-128-CBC with V2Ray/Xray outboundBean structure"},
            {"id": "ziv", "name": "ZIVPN", "extensions": [".ziv"], "encrypted": True, "decryptable": True, "schemes": ["H1"], "description": "AES-128-GCM + PBKDF2-SHA256 (1000 iters), dot-separated salt.iv.ciphertext_mac; current v2.1.5 password supported"},
            {"id": "lnk", "name": "Renamed config (.lnk)", "extensions": [".lnk"], "encrypted": True, "decryptable": False, "schemes": [], "description": "Config renamed to .lnk so Windows treats it as a file, not a shortcut; algorithm not yet reversed"},
            {"id": "ovpn", "name": "OpenVPN", "extensions": [".ovpn"], "encrypted": False, "decryptable": False, "schemes": [], "description": "Plain text OpenVPN config (not yet implemented)"},
        ],
    }


@app.get("/api/config/{config_id}/trace")
async def get_decrypt_trace(config_id: str):
    """Get the full decryption audit trace for a config."""
    if config_id not in config_store:
        raise HTTPException(status_code=404, detail=f"Config not found: {config_id}")

    data = config_store[config_id]
    trace = data.get("decrypt_trace")

    if not trace:
        return {"config_id": config_id, "trace": None, "message": "No decrypt trace available"}

    return {"config_id": config_id, "trace": trace}


@app.get("/api/logs")
async def get_logs(since: int = Query(0, description="Return entries with id > since")):
    """Live log buffer — frontend polls this during decryption to stream
    per-step progress (initial XOR, ChaCha20 outer, RST AES, per-field
    extraction, etc.) into the activity console in real time.
    """
    log = get_live_log()
    return {"entries": log.since(since), "count": log.count}


@app.post("/api/configs/import-assets")
async def import_assets():
    """Walk assets/configs/** and import every config file in one batch.

    The user drops real .hc/.ehi/.hat/... files into the per-format
    subdirectories under assets/configs/ in the repo, then clicks the
    IMPORT ASSETS button in the UI. This endpoint walks the tree and
    parses each file, streaming progress to the live log so the UI
    console shows each import in real time.

    Returns the count of successfully imported configs.
    """
    # Run the synchronous walker in a thread so we don't block the event
    # loop while parsing many files. The live log writes are thread-safe.
    import asyncio
    n = await asyncio.to_thread(_import_assets_synchronously)
    return {"imported": n, "total_in_store": len(config_store)}


@app.get("/api/configs/assets")
async def list_assets():
    """List all config files currently in assets/configs/** without importing.

    The UI calls this to show a preview ("3 files ready to import") next
    to the IMPORT ASSETS button.
    """
    if not ASSETS_CONFIGS_DIR.exists():
        return {"files": [], "total": 0, "dir": str(ASSETS_CONFIGS_DIR)}

    files = []
    for path in sorted(ASSETS_CONFIGS_DIR.rglob("*")):
        if not path.is_file():
            continue
        if path.name in (".gitkeep", "README.md"):
            continue
        ext = path.suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            continue
        rel = path.relative_to(ASSETS_CONFIGS_DIR)
        files.append({
            "path": str(rel),
            "name": path.name,
            "ext": ext,
            "size": path.stat().st_size,
        })
    return {"files": files, "total": len(files), "dir": str(ASSETS_CONFIGS_DIR)}


# ── SNI Host Hunter endpoints ─────────────────────────────────────────────────
#
# All under /api/sni/* — they inherit the existing CORS middleware (ADR-2). GET
# for idempotent reads (jobs, seedlists); POST for state-changing ops (discover
# pulls the network, scan starts a job, stop cancels one, export renders a file).
# Every endpoint gates on SNI_HUNTER_ENABLED. See ADR-6/7/8.


class SniDiscoverRequest(BaseModel):
    domain: str


class SniScanRequest(BaseModel):
    seedlist_path: Optional[str] = None
    candidates: list[str] = []
    concurrency: int = 50
    timeout_s: float = 5.0
    cloudflare_only: bool = False


class SniStopRequest(BaseModel):
    job_id: str


class SniExportRequest(BaseModel):
    job_id: str
    format: str = "txt"


def _sni_job_summary(job: SniScanJob) -> dict:
    """Compact job view for the jobs-list endpoint (omits full results)."""
    return {
        "job_id": job.job_id,
        "status": job.status,
        "total": job.total,
        "done": job.done,
        "found": job.found,
        "created_at": job.created_at,
        "finished_at": job.finished_at,
        "seed_domain": job.seed_domain,
        "seedlist_path": job.seedlist_path,
    }


async def _run_sni_scan(job: SniScanJob) -> None:
    """Background runner: probe every candidate, streaming progress to the live
    log (the UI polls /api/logs, so the scan shows up in the activity console
    with no UI change — design doc §4.1)."""
    live = get_live_log()
    stop = sni_job_store.stop_flag(job.job_id)
    job.status = "running"
    job.started_at = _utcnow_iso()
    live.add("SNI", f"Scan {job.job_id} started — {job.total} host(s), concurrency {job.concurrency}", "info")

    def on_result(res) -> None:
        job.done += 1
        if res.verdict == "working":
            job.found += 1
        job.results.append(res)
        status_str = f" ({res.http_status})" if res.http_status is not None else ""
        live.add(
            "SNI",
            f"[{job.done}/{job.total}] {res.hostname} → {res.verdict}{status_str}",
            "ok" if res.verdict == "working" else "info",
        )

    try:
        hosts = [c.hostname for c in job.candidates]
        await sni_scan(hosts, concurrency=job.concurrency, timeout=job.timeout_s,
                       on_result=on_result, stop_flag=stop)
        job.status = "stopped" if stop.is_set() else "done"
    except Exception as e:  # a scan must never crash the event loop
        job.status = "failed"
        job.error = str(e)
        live.add("SNI", f"Scan {job.job_id} failed: {e}", "err")
    finally:
        job.finished_at = _utcnow_iso()
        live.add("SNI", f"Scan {job.job_id} {job.status} — {job.found} working / {job.total}", "info")


@app.post("/api/sni/discover")
async def sni_discover_endpoint(req: SniDiscoverRequest):
    """Discover candidate hosts for a domain via crt.sh (Certificate Transparency)."""
    _require_sni_enabled()
    domain = (req.domain or "").strip()
    if not domain:
        raise HTTPException(status_code=400, detail="No domain provided")

    live = get_live_log()
    live.add("SNI", f"Discovering candidates for {domain} via crt.sh...", "info")
    try:
        candidates = await sni_discover(domain)
    except Exception as e:
        live.add("SNI", f"crt.sh discovery failed for {domain}: {e}", "err")
        raise HTTPException(status_code=502, detail=f"crt.sh discovery failed: {e}")

    live.add("SNI", f"Discovered {len(candidates)} candidate(s) for {domain}", "ok")
    return {
        "domain": domain,
        "count": len(candidates),
        "candidates": [c.model_dump() for c in candidates],
    }


@app.post("/api/sni/scan")
async def sni_scan_endpoint(req: SniScanRequest):
    """Start a scan job over a seedlist and/or an explicit candidate list.

    Returns immediately with a job_id; poll /api/sni/jobs/{job_id} for progress
    (or watch the activity log). Concurrency is clamped to ADR-6's ceiling.
    """
    _require_sni_enabled()

    candidates: list[SniCandidate] = []
    if req.seedlist_path:
        path = _validate_seedlist_path(req.seedlist_path)
        try:
            candidates = load_seedlist(path, cloudflare_only=req.cloudflare_only)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    for h in req.candidates:
        if h and h.strip():
            candidates.append(SniCandidate(hostname=h.strip().lower().lstrip("*."), source="manual"))

    if not candidates:
        raise HTTPException(status_code=400, detail="No candidates — provide seedlist_path and/or candidates[]")

    concurrency = max(1, min(int(req.concurrency), SNI_MAX_CONCURRENCY))
    job_id = str(uuid.uuid4())[:8]
    job = SniScanJob(
        job_id=job_id,
        seedlist_path=req.seedlist_path,
        candidates=candidates,
        concurrency=concurrency,
        timeout_s=req.timeout_s,
        cloudflare_only=req.cloudflare_only,
        total=len(candidates),
    )
    sni_job_store.add(job)
    # Fire-and-forget background task; the store holds the job by reference so
    # progress is visible via the jobs endpoints while it runs.
    asyncio.create_task(_run_sni_scan(job))
    return {"job_id": job_id, "total": job.total, "concurrency": concurrency}


@app.post("/api/sni/scan/stop")
async def sni_scan_stop(req: SniStopRequest):
    """Signal a running scan to stop (in-flight probes finish; queued ones skip)."""
    _require_sni_enabled()
    if not sni_job_store.request_stop(req.job_id):
        raise HTTPException(status_code=404, detail=f"Job not found: {req.job_id}")
    return {"status": "stopping", "job_id": req.job_id}


@app.get("/api/sni/jobs")
async def sni_jobs():
    """List scan jobs (newest first), compact view."""
    _require_sni_enabled()
    return {"jobs": [_sni_job_summary(j) for j in sni_job_store.list()]}


@app.get("/api/sni/jobs/{job_id}")
async def sni_job(job_id: str):
    """Full job state including all probe results."""
    _require_sni_enabled()
    job = sni_job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return job.model_dump()


@app.get("/api/sni/seedlists")
async def sni_seedlists():
    """List the bundled per-ISP seed lists shipped in-tree (ADR-8)."""
    _require_sni_enabled()
    return {"seedlists": list_bundled_seedlists()}


@app.post("/api/sni/export")
async def sni_export(req: SniExportRequest):
    """Export a job's results as txt (working hosts), csv, or json.

    Returns the rendered content in JSON (the frontend proxies via IPC and
    turns `content` into a downloadable Blob — same pattern as config export).
    """
    _require_sni_enabled()
    job = sni_job_store.get(req.job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {req.job_id}")
    try:
        content, media_type, filename = export_job(job, req.format)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "job_id": req.job_id,
        "format": req.format.lower(),
        "filename": filename,
        "media_type": media_type,
        "content": content,
    }


# ── SNI Host Hunter — Phase 2 endpoints ───────────────────────────────────────
#
# Five new endpoints covering: real-time CT watch (CertStream), ECH capability
# detection (RFC 9848 DNS HTTPS-RR), reverse-IP lookup, open-port checker, and
# "use as SNI" (apply a discovered bug host to a parsed config). All gate on
# SNI_HUNTER_ENABLED and inherit the existing CORS middleware (ADR-2).


class SniWatchRequest(BaseModel):
    domain: str
    duration_s: float = 60.0


class SniEchRequest(BaseModel):
    hostname: str


class SniReverseIpRequest(BaseModel):
    ip: str


class SniPortCheckRequest(BaseModel):
    host: str
    ports: list[int] = []
    timeout_s: float = 3.0


class SniApplyRequest(BaseModel):
    config_id: str
    sni: str


@app.post("/api/sni/watch")
async def sni_watch(req: SniWatchRequest):
    """Watch the CertStream feed for `duration_s` and collect new hostnames
    for `domain`. Returns the deduped SniCandidate list.

    CertStream is an OPTIONAL dep — if the `certstream` package isn't
    installed this returns 503 with a clear install hint. The watch runs
    synchronously within the request (the websocket feed is in a background
    thread); for durations > ~120s the UI should background this.
    """
    _require_sni_enabled()
    domain = (req.domain or "").strip().lower().lstrip("*.")
    if not domain:
        raise HTTPException(status_code=400, detail="No domain provided")
    # Clamp duration to a sane window — CertStream is a firehose; a 1-hour
    # watch would collect thousands of hostnames and saturate the request.
    duration = max(1.0, min(float(req.duration_s), 300.0))

    live = get_live_log()
    live.add("SNI", f"Watching CertStream for {domain} ({duration:.0f}s)...", "info")

    def on_candidate(cand) -> None:
        live.add("SNI", f"CT new: {cand.hostname}", "info")

    try:
        candidates = await sni_watch_certstream(domain, duration_s=duration,
                                                 on_candidate=on_candidate)
    except ImportError as e:
        live.add("SNI", f"CertStream unavailable: {e}", "err")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        live.add("SNI", f"CertStream watch failed: {e}", "err")
        raise HTTPException(status_code=502, detail=f"CertStream watch failed: {e}")

    live.add("SNI", f"CertStream watch done — {len(candidates)} new host(s) for {domain}", "ok")
    return {
        "domain": domain,
        "duration_s": duration,
        "count": len(candidates),
        "candidates": [c.model_dump() for c in candidates],
    }


@app.post("/api/sni/ech")
async def sni_ech(req: SniEchRequest):
    """Check whether a hostname advertises ECH (Encrypted Client Hello) via
    its DNS SVCB/HTTPS RR (RFC 9848).

    ECH-capable hosts hide their real SNI from the network path, which makes
    them *less useful* as bug hosts — an ISP doing SNI-based zero-rating
    can't see the hostname to match against its whitelist. The UI flags
    ECH-capable hosts distinctly in the results.
    """
    _require_sni_enabled()
    hostname = (req.hostname or "").strip().lower().lstrip("*.")
    if not hostname:
        raise HTTPException(status_code=400, detail="No hostname provided")
    result = await sni_check_ech(hostname)
    return result


@app.post("/api/sni/reverseip")
async def sni_reverseip_endpoint(req: SniReverseIpRequest):
    """Reverse-IP lookup: what other domains are hosted on this IP?

    Uses public APIs (HackerTarget's free reverse-IP endpoint, falling back
    to PTR) per ADR-6 — no active scanning. Useful because an ISP's zero-
    rating whitelist is often the whole IP, so sibling hostnames on the same
    IP can surface more bug-host candidates.
    """
    _require_sni_enabled()
    ip = (req.ip or "").strip()
    if not ip:
        raise HTTPException(status_code=400, detail="No IP provided")
    result = await sni_reverseip(ip)
    return result


@app.post("/api/sni/portcheck")
async def sni_portcheck(req: SniPortCheckRequest):
    """Probe a small fixed set of common web ports on a host (BugScanX #7).

    ADR-6 backstop: at most MAX_PORTS_PER_HOST ports per call (default set
    is 80/443/8080/8443). The probe is a plain TCP connect — no banner
    grabbing, no fingerprinting.
    """
    _require_sni_enabled()
    host = (req.host or "").strip().lower().lstrip("*.")
    if not host:
        raise HTTPException(status_code=400, detail="No host provided")
    ports = req.ports or None  # empty list → default set
    result = await sni_check_ports(host, ports=ports, timeout=req.timeout_s)
    return result


@app.post("/api/sni/apply")
async def sni_apply(req: SniApplyRequest):
    """Apply a discovered bug host to an existing parsed config ("use as SNI").

    Re-parses the config from disk (so the decrypt trace is fresh), overrides
    the `sni` field with the new hostname, preserves the original SNI under
    `raw_data._original_sni` for revert, and stores the result back into
    config_store under the same config_id. Returns the new ConfigInfo.

    This closes the discover→probe→use loop: scan a seedlist, find a working
    host, click "Use as SNI" on a target config, and the config is updated
    in place.
    """
    _require_sni_enabled()
    config_id = (req.config_id or "").strip()
    new_sni = (req.sni or "").strip()
    if not config_id:
        raise HTTPException(status_code=400, detail="No config_id provided")
    if not new_sni:
        raise HTTPException(status_code=400, detail="No SNI hostname provided")

    live = get_live_log()
    live.add("SNI", f"Applying SNI '{new_sni}' to config {config_id}...", "info")
    try:
        normalized = apply_sni_to_config_id(config_store, config_id, new_sni)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Config not found: {config_id}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # A re-parse failure (e.g. the file was moved) is a 500 — the config
        # is in the store but its filepath no longer parses.
        live.add("SNI", f"Apply failed for {config_id}: {e}", "err")
        raise HTTPException(status_code=500, detail=f"Re-parse failed: {e}")

    config_store[config_id] = normalized.model_dump()
    live.add("SNI", f"Config {config_id} SNI → {new_sni}", "ok")
    return _ir_to_response(config_id, normalized)


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
