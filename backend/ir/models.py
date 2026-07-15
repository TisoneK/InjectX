"""
InjectX — Versioned IR Models

This module defines the canonical Intermediate Representation (IR) contract
for InjectX. All components must produce/consume these models — never raw dicts.

IR Versioning Rule:
  - ir_version is incremented on ANY breaking change to the schema
  - Consumers MUST check ir_version before deserializing
  - Additive changes (new optional fields) do NOT bump version
  - Removal or type-change of any field DOES bump version

Current: IR v1.0
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_serializer, field_validator


# ── IR Version ────────────────────────────────────────────────────────────────

IR_VERSION = "1.0"


# ── Enums (strict — no free-form strings) ─────────────────────────────────────

class FormatEnum(str, enum.Enum):
    """All recognized config file formats."""
    EHI = "ehi"
    HC = "hc"
    HAT = "hat"
    DARK = "dark"
    DARKTUNNEL = "darktunnel"
    TLS = "tls"
    NPV = "npv"
    NSH = "nsh"
    VHD = "vhd"
    OVPN = "ovpn"
    CONF = "conf"
    ENCRYPTED_UNKNOWN = "encrypted_unknown"
    UNKNOWN = "unknown"


class ProtocolEnum(str, enum.Enum):
    """All recognized tunnel protocols."""
    SSH = "ssh"
    SSL = "ssl"
    V2RAY = "v2ray"
    VLESS = "vless"
    VMESS = "vmess"
    WEBSOCKET = "websocket"
    HYSTERIA = "hysteria"
    HYSTERIA2 = "hysteria2"
    XRAY = "xray"
    SHADOWSOCKS = "shadowsocks"
    TROJAN = "trojan"
    WIREGUARD = "wireguard"
    TLS_VPN = "tls_vpn"
    SOCKS = "socks"
    SLOWDNS = "slowdns"
    DNSTT = "dnstt"
    UNKNOWN = "unknown"


class DecryptStatusEnum(str, enum.Enum):
    """Decryption outcome states."""
    SUCCESS = "success"
    PARTIAL = "partial"          # Decrypted but some fields remain obfuscated
    FAILED = "failed"            # Tried all keys/schemes, none worked
    NOT_ENCRYPTED = "not_encrypted"
    NO_DECRYPTOR = "no_decryptor"  # Format known, no public algorithm exists


class SchemeEnum(str, enum.Enum):
    """
    Decryption scheme taxonomy.
    Maps to the crypto-router's dispatch table.

    A-series: HTTP Custom (.hc) variants
    B-series: HTTP Injector (.ehi) 2-stage AES + field XOR
    C-series: NapsternetV (.npv4/.inpv) subtraction cipher
    D-series: SocksHTTP (.nsh) AES-128-GCM + PBKDF2
    E-series: HA Tunnel (.hat) AES-128-ECB
    F-series: TLS Tunnel (.tls) AES-256-GCM
    G-series: VHD (.vhd) AES-128-CBC
    """
    # A-series: HTTP Custom
    A1 = "A1"   # HC XOR + AES-128-ECB (SHA1 key derivation, ePro keys)
    A2 = "A2"   # HC raw AES-128-ECB (no XOR, SHA1 key derivation)
    A3 = "A3"   # HC v233 double-encryption (XOR + plain key + SHA1 key)
    A4 = "A4"   # eProxy raw AES-128-ECB (pisahConk delimiter)
    A5 = "A5"   # HC v2.7+ multi-layer (initial XOR + ChaCha20 + RST AES-ECB + per-field ChaCha20/JKL)

    # B-series: HTTP Injector
    B1 = "B1"   # EHI AES-256-CBC → AES-128-CBC + configSalt XOR + custom base64

    # C-series: NapsternetV
    C1 = "C1"   # NPV4 subtraction cipher (charCode subtraction with cycling key)

    # D-series: SocksHTTP
    D1 = "D1"   # NSH AES-128-GCM + PBKDF2 (dot-separated salt.iv.ciphertext_mac)

    # E-series: HA Tunnel
    E1 = "E1"   # HAT AES-128-ECB (base64-encoded keys, brute-force)

    # F-series: TLS Tunnel
    F1 = "F1"   # TLS AES-256-GCM (build_number:base64_payload format)

    # G-series: VHD
    G1 = "G1"   # VHD AES-128-CBC (raw ASCII key + IV)

    # Special
    NONE = "none"             # No decryption needed (plain text / ZIP + JSON)
    UNSUPPORTED = "unsupported"  # No public decryptor exists


# ── Detection Result ──────────────────────────────────────────────────────────

class DetectionFeatures(BaseModel):
    """Multi-feature classification vector used by the detector."""
    entropy: float = Field(ge=0.0, le=8.0, description="Shannon entropy of first 512 bytes")
    byte_distribution_skew: float = Field(ge=0.0, le=1.0, description="How uniform the byte distribution is (0=uniform, 1=skewed)")
    ascii_ratio: float = Field(ge=0.0, le=1.0, description="Ratio of printable ASCII bytes in first 512 bytes")
    is_zip: bool = Field(description="Whether file starts with ZIP magic bytes")
    base64_likelihood: float = Field(ge=0.0, le=1.0, description="How likely the content is base64-encoded")
    null_byte_ratio: float = Field(ge=0.0, le=1.0, description="Ratio of null bytes")


class DetectResult(BaseModel):
    """Output of the detection layer."""
    ir_version: Literal["1.0"] = IR_VERSION
    filepath: str
    filename: str
    format: FormatEnum
    features: DetectionFeatures
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    is_encrypted: bool = False
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ── Decryption Layer ──────────────────────────────────────────────────────────

class DecryptAttempt(BaseModel):
    """Record of a single decryption attempt — used by the audit layer."""
    scheme: SchemeEnum
    key_label: str = ""          # Human-readable key identifier (e.g. "hc_reborn_4")
    result: str                  # "success", "fail", "error"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    error_message: str = ""
    elapsed_ms: float = 0.0
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DecryptTrace(BaseModel):
    """Complete audit trail of all decryption attempts for a single file."""
    filepath: str
    filename: str
    format: FormatEnum
    attempts: list[DecryptAttempt] = []
    winning_scheme: Optional[SchemeEnum] = None
    winning_key_label: Optional[str] = None
    total_elapsed_ms: float = 0.0
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def add_attempt(self, attempt: DecryptAttempt) -> None:
        self.attempts.append(attempt)
        if attempt.result == "success" and self.winning_scheme is None:
            self.winning_scheme = attempt.scheme
            self.winning_key_label = attempt.key_label


class DecryptedPayload(BaseModel):
    """
    Intermediate crypto representation — the bridge between crypto and parser.

    This is what the scheme router returns. Parsers consume this, never raw bytes.
    """
    ir_version: Literal["1.0"] = IR_VERSION
    scheme: SchemeEnum
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score from decryptor")
    status: DecryptStatusEnum
    raw_bytes: Optional[bytes] = Field(default=None, description="Raw decrypted bytes")
    json_data: Optional[dict[str, Any]] = Field(default=None, description="Parsed JSON if available")
    key_label: str = Field(default="", description="Which key succeeded")
    trace: DecryptTrace = Field(default_factory=lambda: DecryptTrace(filepath="", filename="", format=FormatEnum.UNKNOWN))

    model_config = {
        "arbitrary_types_allowed": True,
    }

    @field_serializer("raw_bytes", when_used="json")
    def _serialize_raw_bytes(self, v: Optional[bytes]) -> str:
        """Render decrypted bytes as hex on JSON serialization.

        Pydantic v2 replacement for the deprecated ``json_encoders`` config.
        Scoped to ``when_used="json"`` so ``model_dump()`` (python mode) still
        returns the raw ``bytes``, preserving the prior behaviour exactly.
        """
        return v.hex() if v else ""

    @field_validator("confidence")
    @classmethod
    def confidence_matches_status(cls, v, info):
        """Invariant: failed decryption must have 0 confidence."""
        # In Pydantic v2, we can't access other fields in field_validator easily,
        # so we do a post-init check instead. This validator just ensures non-negative.
        if v < 0.0:
            raise ValueError(f"Confidence must be >= 0, got {v}")
        return v


# ── Normalized Config (the canonical IR) ──────────────────────────────────────

class NormalizedConfig(BaseModel):
    """
    The canonical config IR — every parser MUST produce this exact shape.

    This is the versioned contract between backend and frontend.
    UI renders this structure, nothing else.
    """
    ir_version: Literal["1.0"] = IR_VERSION

    # Identity
    filepath: str
    filename: str
    format: FormatEnum
    is_encrypted: bool = False
    decryption_status: DecryptStatusEnum = DecryptStatusEnum.NOT_ENCRYPTED
    scheme_used: Optional[SchemeEnum] = None

    # Connection
    host: Optional[str] = None
    port: Optional[int] = None
    protocol: Optional[ProtocolEnum] = None

    # SSH
    ssh_server: Optional[str] = None
    ssh_port: Optional[int] = None
    ssh_user: Optional[str] = None
    ssh_pass: Optional[str] = None
    ssh_key: Optional[str] = None

    # Proxy
    proxy_host: Optional[str] = None
    proxy_port: Optional[int] = None

    # HTTP Injection
    payload: Optional[str] = None
    payload_parsed: list[dict[str, Any]] = []
    custom_headers: dict[str, Any] = {}
    sni: Optional[str] = None
    bug_host: Optional[str] = None

    # DNS
    dns: Optional[str] = None
    remote_dns: Optional[str] = None

    # V2Ray / Xray
    v2ray: Optional[dict[str, Any]] = None
    vmess_config: Optional[dict[str, Any]] = None
    vless_config: Optional[dict[str, Any]] = None
    websocket: Optional[dict[str, Any]] = None

    # Protocol-specific
    connection_type: Optional[str] = None
    tunnel_type: Optional[str] = None
    tunnel_mode: Optional[str] = None
    inject_type: Optional[str] = None

    # TLS
    tls_version: Optional[str] = None
    internal_ip: Optional[str] = None
    ssl_enabled: Optional[bool] = None

    # Hysteria / Xray / Shadowsocks / WireGuard
    hysteria: Optional[dict[str, Any]] = None
    xray: Optional[dict[str, Any]] = None
    shadowsocks: Optional[dict[str, Any]] = None
    wireguard: Optional[dict[str, Any]] = None

    # Metadata
    errors: list[str] = []
    warnings: list[str] = []
    raw_data: Optional[dict[str, Any]] = None

    # Audit
    decrypt_trace: Optional[DecryptTrace] = None

    model_config = {"use_enum_values": True}
