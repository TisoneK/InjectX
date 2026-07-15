"""
InjectX — Config File Format Detector v2

Upgraded with 3-feature classification:
  - Shannon entropy (byte randomness)
  - Byte distribution skew (uniformity)
  - ASCII ratio (printable content)
  - ZIP signature detection
  - Base64 likelihood score

This replaces the old entropy-only heuristic with a multi-signal classifier
that avoids false classification of encrypted vs compressed vs encoded data.
"""

from __future__ import annotations

import base64
import json
import math
import zipfile
from collections import Counter
from pathlib import Path
from typing import Optional

from ir.models import (
    DetectResult,
    DetectionFeatures,
    FormatEnum,
)


# ── Extension Map ─────────────────────────────────────────────────────────────

EXTENSION_MAP: dict[str, FormatEnum] = {
    ".ehi": FormatEnum.EHI,
    ".hc": FormatEnum.HC,
    ".hat": FormatEnum.HAT,
    ".ha": FormatEnum.HAT,
    ".dark": FormatEnum.DARK,
    ".drak": FormatEnum.DARK,
    ".dt": FormatEnum.DARK,
    ".darktunnel": FormatEnum.DARKTUNNEL,
    ".tls": FormatEnum.TLS,
    ".npv4": FormatEnum.NPV,
    ".inpv": FormatEnum.NPV,
    ".npv": FormatEnum.NPV,
    ".nsh": FormatEnum.NSH,
    ".vhd": FormatEnum.VHD,
    ".ovpn": FormatEnum.OVPN,
    ".conf": FormatEnum.CONF,
}


# ── Feature Extraction ────────────────────────────────────────────────────────

def _extract_features(raw: bytes) -> DetectionFeatures:
    """
    Extract a multi-feature classification vector from raw file bytes.
    Uses first 512 bytes for analysis.
    """
    sample = raw[:512] if len(raw) >= 512 else raw

    if not sample:
        return DetectionFeatures(
            entropy=0.0,
            byte_distribution_skew=0.0,
            ascii_ratio=0.0,
            is_zip=False,
            base64_likelihood=0.0,
            null_byte_ratio=1.0,
        )

    # 1. Shannon entropy
    byte_counts = Counter(sample)
    total = len(sample)
    entropy = 0.0
    for count in byte_counts.values():
        p = count / total
        if p > 0:
            entropy -= p * math.log2(p)

    # 2. Byte distribution skew (how far from uniform)
    # Uniform = 256 unique bytes each appearing ~2 times in 512 bytes
    # Perfect uniformity: skew = 0, all same byte: skew = 1
    max_entropy = 8.0  # For 256 equally likely byte values
    skew = 1.0 - (entropy / max_entropy) if max_entropy > 0 else 1.0

    # 3. ASCII ratio
    ascii_count = sum(1 for b in sample if 32 <= b <= 126 or b in (9, 10, 13))
    ascii_ratio = ascii_count / total

    # 4. ZIP detection
    is_zip = raw[:4] == b"PK\x03\x04"

    # 5. Base64 likelihood
    b64_chars = set(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=\n\r")
    b64_count = sum(1 for b in sample if b in b64_chars)
    base64_likelihood = b64_count / total

    # 6. Null byte ratio
    null_count = sample.count(0)
    null_ratio = null_count / total

    return DetectionFeatures(
        entropy=round(entropy, 4),
        byte_distribution_skew=round(skew, 4),
        ascii_ratio=round(ascii_ratio, 4),
        is_zip=is_zip,
        base64_likelihood=round(base64_likelihood, 4),
        null_byte_ratio=round(null_ratio, 4),
    )


def _classify_encrypted(features: DetectionFeatures) -> bool:
    """
    3-feature classifier: determine if data looks encrypted.

    Encrypted data signature:
      - High entropy (> 7.0)
      - Low skew (< 0.15 — near-uniform distribution)
      - Low ASCII ratio (< 0.4)
      - Low null byte ratio (< 0.05)

    Compressed data (e.g., ZIP without entry):
      - High entropy
      - BUT has ZIP magic or known structure

    Base64 encoded data:
      - Medium-high entropy (~6.0)
      - Very high base64_likelihood (> 0.9)
      - High ASCII ratio (> 0.9)
    """
    # Not encrypted if it's a ZIP
    if features.is_zip:
        return False

    # High entropy + low skew + low ASCII = very likely encrypted
    if features.entropy > 7.0 and features.byte_distribution_skew < 0.15 and features.ascii_ratio < 0.4:
        return True

    # High entropy + low null ratio + moderate ASCII = probably encrypted
    if features.entropy > 7.5 and features.null_byte_ratio < 0.05 and features.ascii_ratio < 0.5:
        return True

    return False


def _classify_base64(features: DetectionFeatures) -> bool:
    """Determine if data looks like base64-encoded content."""
    return features.base64_likelihood > 0.85 and features.ascii_ratio > 0.85


# ── Format Detection ──────────────────────────────────────────────────────────

def detect_format(filepath: str) -> FormatEnum:
    """
    Detect config file format using extension + multi-feature content analysis.

    Returns FormatEnum (never raw strings).
    """
    path = Path(filepath)
    ext = path.suffix.lower()

    # Pass 1: Extension-based lookup with content validation
    if ext in EXTENSION_MAP:
        format_hint = EXTENSION_MAP[ext]
        if _validate_format(path, format_hint):
            return format_hint

    # Pass 2: Content-based detection
    return _detect_by_content(path)


def detect_with_features(filepath: str) -> DetectResult:
    """
    Detect format AND return full feature vector.
    This is the primary entry point for v0.4+.
    """
    path = Path(filepath)
    fmt = detect_format(filepath)

    try:
        raw = path.read_bytes()
    except Exception:
        raw = b""

    features = _extract_features(raw)
    is_encrypted = _classify_encrypted(features)

    # Override is_encrypted for known-encrypted formats
    encrypted_formats = {
        FormatEnum.HC, FormatEnum.HAT, FormatEnum.DARK,
        FormatEnum.TLS, FormatEnum.NPV, FormatEnum.NSH,
        FormatEnum.VHD,
    }
    if fmt in encrypted_formats:
        is_encrypted = True

    return DetectResult(
        filepath=str(path),
        filename=path.name,
        format=fmt,
        features=features,
        is_encrypted=is_encrypted,
    )


# ── Content Validation ────────────────────────────────────────────────────────

def _validate_format(path: Path, format_hint: FormatEnum) -> bool:
    """Validate that file content matches the expected format."""
    try:
        if format_hint == FormatEnum.EHI:
            return zipfile.is_zipfile(path)

        elif format_hint in (FormatEnum.HC, FormatEnum.HAT, FormatEnum.DARK,
                             FormatEnum.TLS, FormatEnum.NPV, FormatEnum.NSH,
                             FormatEnum.VHD):
            return path.exists() and path.stat().st_size > 0

        elif format_hint == FormatEnum.DARKTUNNEL:
            return path.exists() and path.stat().st_size > 0

        elif format_hint == FormatEnum.OVPN:
            raw = path.read_bytes()
            text = raw.decode("utf-8", errors="ignore").lower()
            return "client" in text or "dev tun" in text or "remote" in text

    except Exception:
        return False

    return True


def _detect_by_content(path: Path) -> FormatEnum:
    """Content-based format detection (fallback when extension is missing/misleading)."""
    try:
        raw = path.read_bytes()
    except Exception:
        return FormatEnum.UNKNOWN

    if not raw:
        return FormatEnum.UNKNOWN

    features = _extract_features(raw)

    # Check ZIP
    if features.is_zip:
        try:
            with zipfile.ZipFile(path, "r") as zf:
                namelist = zf.namelist()
                for name in namelist:
                    name_lower = name.lower()
                    if "ehi" in name_lower or "httpinjector" in name_lower:
                        return FormatEnum.EHI
                    if "hatunnel" in name_lower or "ha_tunnel" in name_lower:
                        return FormatEnum.HAT
                    if "httpcustom" in name_lower or "hc" in name_lower:
                        return FormatEnum.HC
                return FormatEnum.EHI  # Default ZIP-based config
        except Exception:
            return FormatEnum.EHI

    # Try plain JSON
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return _identify_json_format(data)
    except Exception:
        pass

    # Try base64 → JSON
    if _classify_base64(features):
        try:
            decoded = base64.b64decode(raw)
            data = json.loads(decoded)
            if isinstance(data, dict):
                return _identify_json_format(data)
        except Exception:
            pass

    # Check for OpenVPN
    if features.ascii_ratio > 0.8:
        try:
            text = raw.decode("utf-8", errors="ignore").lower()
            if "client" in text and "dev tun" in text:
                return FormatEnum.OVPN
        except Exception:
            pass

    # Check for VMess/VLess links
    try:
        text = raw.decode("utf-8", errors="ignore").strip()
        if text.startswith("vmess://"):
            return FormatEnum.NPV
        if text.startswith("vless://"):
            return FormatEnum.NPV
    except Exception:
        pass

    # Encrypted unknown
    if _classify_encrypted(features):
        return FormatEnum.ENCRYPTED_UNKNOWN

    return FormatEnum.UNKNOWN


def _identify_json_format(data: dict) -> FormatEnum:
    """Identify config format from parsed JSON field names."""
    keys_lower = {k.lower() for k in data.keys()}

    ehi_indicators = {"payload", "proxyip", "proxyport", "sshserver", "sshport", "sshuser", "sshpass", "dns", "remotedns"}
    if len(keys_lower & ehi_indicators) >= 2:
        return FormatEnum.EHI

    hc_indicators = {"httpcustom", "customheader", "connectiontype", "directconnect", "ssl_file"}
    if keys_lower & hc_indicators:
        return FormatEnum.HC

    hat_indicators = {"hatunnel", "bughost", "tunneltype", "customsni", "profile", "profilev4"}
    if keys_lower & hat_indicators:
        return FormatEnum.HAT

    dark_indicators = {"darktunnel", "dark_tunnel", "injecttype", "payloadgenerator", "hysteria", "xrayconfig"}
    if keys_lower & dark_indicators:
        return FormatEnum.DARK

    tls_indicators = {"tlsvpn", "tls_tunnel", "tlstunnel", "dns_server", "internalip"}
    if keys_lower & tls_indicators:
        return FormatEnum.TLS

    npv_indicators = {"napsternetv", "v2ray_config", "vless_config", "vmess_config", "ssh_config", "vmess", "outboundbean"}
    if keys_lower & npv_indicators:
        return FormatEnum.NPV

    return FormatEnum.UNKNOWN
