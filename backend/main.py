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
import logging
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

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
})

# In-memory config store (keyed by ID → NormalizedConfig dict)
config_store: dict[str, dict] = {}


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


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Backend v0.4 starting (IR version %s)...", IR_VERSION)
    logger.info("Config upload directory: %s", UPLOAD_DIR)
    yield
    logger.info("Backend shutting down...")


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
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://127.0.0.1:{PORT}",
        f"http://localhost:{PORT}",
        "file://",
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
        # Include only non-None, non-metadata fields
        config_dict = {}
        exclude_keys = {"filepath", "filename", "format", "ir_version", "is_encrypted",
                       "decryption_status", "scheme_used", "errors", "warnings",
                       "raw_data", "decrypt_trace", "payload_parsed"}
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

    # Export: exclude raw_data and decrypt_trace (too verbose)
    export = {k: v for k, v in normalized.model_dump().items()
              if k not in ("raw_data", "decrypt_trace") and v is not None}

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
            {"id": "ehi", "name": "HTTP Injector", "extensions": [".ehi"], "encrypted": False, "decryptable": True, "schemes": ["B1"], "description": "ZIP archive with JSON config (may be locked/obfuscated with 2-stage AES)"},
            {"id": "hc", "name": "HTTP Custom", "extensions": [".hc"], "encrypted": True, "decryptable": True, "schemes": ["A1", "A2", "A3", "A4"], "description": "Encrypted HCUST format (XOR + AES-128-ECB, 76+ known keys)"},
            {"id": "hat", "name": "HA Tunnel Plus", "extensions": [".hat", ".ha"], "encrypted": True, "decryptable": True, "schemes": ["E1"], "description": "AES-128-ECB encrypted JSON (2 known keys, profile/profilev4/configuration structures)"},
            {"id": "dark", "name": "DARK TUNNEL VPN", "extensions": [".dark", ".drak", ".dt"], "encrypted": True, "decryptable": False, "schemes": [], "description": "Proprietary encryption (no public decryptor)"},
            {"id": "tls", "name": "TLS Tunnel", "extensions": [".tls"], "encrypted": True, "decryptable": True, "schemes": ["F1"], "description": "AES-256-GCM with build_number:base64_payload format"},
            {"id": "npv", "name": "NapsternetV", "extensions": [".npv4", ".inpv", ".npv"], "encrypted": True, "decryptable": True, "schemes": ["C1"], "description": "Subtraction cipher (charCode subtraction with cycling key)"},
            {"id": "nsh", "name": "SocksHTTP", "extensions": [".nsh"], "encrypted": True, "decryptable": True, "schemes": ["D1"], "description": "AES-128-GCM + PBKDF2 with dot-separated salt.iv.ciphertext_mac format"},
            {"id": "vhd", "name": "V2Ray/NPV Tunnel", "extensions": [".vhd"], "encrypted": True, "decryptable": True, "schemes": ["G1"], "description": "AES-128-CBC with V2Ray/Xray outboundBean structure"},
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


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
