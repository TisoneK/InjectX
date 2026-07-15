"""
InjectX — TLS Tunnel (.tls) Decryption

Scheme F1: AES-256-GCM with structured file format.

Based on Pancho7532/HCDecryptor tlsDecryptor.lib.js research:
  - File format: "<build_number>:<base64_payload>"
  - base64_payload decodes to: IV(12 bytes) + ciphertext + MAC(16 bytes)
  - Encryption: AES-256-GCM with single hardcoded key
  - Decrypted data is colon-separated with base64-encoded subfields
"""

from __future__ import annotations

import base64
import json
import time
from typing import Optional

from ir.models import (
    DecryptedPayload,
    DecryptAttempt,
    DecryptStatusEnum,
    DecryptTrace,
    SchemeEnum,
)
from .keys import KeyStore


def _aes_gcm_decrypt(ciphertext: bytes, key: bytes, iv: bytes, tag: bytes) -> Optional[bytes]:
    """AES-256-GCM decryption with authentication tag."""
    try:
        from Crypto.Cipher import AES
        cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
        return cipher.decrypt_and_verify(ciphertext, tag)
    except Exception:
        return None


def _parse_tls_fields(text: str, build_number: int) -> dict:
    """Parse colon-separated TLS Tunnel decrypted data into structured dict."""
    parts = text.split(":")

    result: dict = {}

    def _b64_decode_safe(val: str) -> str:
        try:
            return base64.b64decode(val).decode("utf-8", errors="replace")
        except Exception:
            return val

    if build_number >= 200 and len(parts) >= 14:
        # Structured format (build >= 200)
        connection_methods = ["Default", "Payload", "SNI", "Payload+SNI",
                              "Payload+Proxy", "Payload+Proxy+SNI", "DNS Tunnel"]
        dns_types = ["UDP[53]", "DoT[853]", "DoH[853]"]
        predefined_ports = ["Auto", "25", "80", "110", "143", "443", "465",
                            "853", "993", "995", "2525", "3128", "8080", "8888", "33827"]

        try:
            result["connection_method"] = connection_methods[int(parts[0])] if int(parts[0]) < len(connection_methods) else f"Unknown({parts[0]})"
        except (ValueError, IndexError):
            result["connection_method_raw"] = parts[0]

        result["payload"] = _b64_decode_safe(parts[1]) if len(parts) > 1 else None
        result["sni"] = _b64_decode_safe(parts[2]) if len(parts) > 2 else None
        result["note"] = _b64_decode_safe(parts[3]) if len(parts) > 3 else None
        result["ssh_server"] = _b64_decode_safe(parts[4]) if len(parts) > 4 else None

        if len(parts) > 5:
            try:
                result["predefined_port"] = predefined_ports[int(parts[5])] if int(parts[5]) < len(predefined_ports) else parts[5]
            except (ValueError, IndexError):
                result["predefined_port_raw"] = parts[5]

        result["ssh_port"] = _b64_decode_safe(parts[6]) if len(parts) > 6 else None
        result["ssh_user"] = _b64_decode_safe(parts[7]) if len(parts) > 7 else None
        result["ssh_pass"] = _b64_decode_safe(parts[8]) if len(parts) > 8 else None
        result["proxy_url"] = _b64_decode_safe(parts[9]) if len(parts) > 9 else None
        result["proxy_port"] = _b64_decode_safe(parts[10]) if len(parts) > 10 else None

        if len(parts) > 11:
            try:
                dns_type_idx = int(parts[11])
                result["dns_type"] = dns_types[dns_type_idx] if dns_type_idx < len(dns_types) else f"Unknown({dns_type_idx})"
            except (ValueError, IndexError):
                result["dns_type_raw"] = parts[11]

        result["dns_server"] = _b64_decode_safe(parts[12]) if len(parts) > 12 else None
        result["dns_domain"] = _b64_decode_safe(parts[13]) if len(parts) > 13 else None
        result["dns_public_key"] = _b64_decode_safe(parts[14]) if len(parts) > 14 else None

        # Tail fields
        if len(parts) > 5:
            result["lock_payload_servers"] = parts[-5] if len(parts) > 5 else None
            result["block_torrent"] = parts[-4] if len(parts) > 4 else None
    else:
        # Legacy format (build < 200) — return raw
        result["_raw_decrypted"] = text

    return result


def _score_tls_result(data: dict) -> float:
    """Confidence scoring for TLS decryption."""
    if not data:
        return 0.0

    score = 0.3  # Base score for successful GCM decryption (auth tag passed)

    if data.get("connection_method"):
        score += 0.15
    if data.get("ssh_server"):
        score += 0.2
    if data.get("sni"):
        score += 0.1
    if data.get("payload"):
        score += 0.1
    if data.get("ssh_user"):
        score += 0.1
    if data.get("proxy_url"):
        score += 0.05

    return min(1.0, score)


def decrypt_tls(
    scheme: SchemeEnum,
    raw: bytes,
    keys: KeyStore,
    trace: DecryptTrace,
) -> DecryptedPayload:
    """Decrypt TLS Tunnel (.tls) config using AES-256-GCM."""
    tls_keys = keys.tls

    try:
        content = raw.decode("utf-8", errors="strict").strip()
    except Exception:
        return DecryptedPayload(
            scheme=SchemeEnum.F1,
            confidence=0.0,
            status=DecryptStatusEnum.FAILED,
        )

    # Parse format: "build_number:base64_payload"
    if ":" not in content:
        return DecryptedPayload(
            scheme=SchemeEnum.F1,
            confidence=0.0,
            status=DecryptStatusEnum.FAILED,
        )

    colon_idx = content.index(":")
    try:
        build_number = int(content[:colon_idx])
    except ValueError:
        build_number = 0

    b64_payload = content[colon_idx + 1:]

    try:
        payload_bytes = base64.b64decode(b64_payload)
    except Exception:
        return DecryptedPayload(
            scheme=SchemeEnum.F1,
            confidence=0.0,
            status=DecryptStatusEnum.FAILED,
        )

    # Extract IV (first 12 bytes), ciphertext (middle), MAC (last 16 bytes)
    if len(payload_bytes) < 28:  # 12 (IV) + 16 (MAC) minimum
        return DecryptedPayload(
            scheme=SchemeEnum.F1,
            confidence=0.0,
            status=DecryptStatusEnum.FAILED,
        )

    iv = payload_bytes[:12]
    auth_tag = payload_bytes[-16:]
    ciphertext = payload_bytes[12:-16]

    # Try each key
    for key_b64 in tls_keys:
        start = time.monotonic()
        try:
            key = base64.b64decode(key_b64)
            if len(key) != 32:  # AES-256 needs 32-byte key
                continue

            decrypted = _aes_gcm_decrypt(ciphertext, key, iv, auth_tag)
            if decrypted:
                text = decrypted.decode("utf-8", errors="strict")
                data = _parse_tls_fields(text, build_number)
                confidence = _score_tls_result(data)
                elapsed = (time.monotonic() - start) * 1000

                trace.add_attempt(DecryptAttempt(
                    scheme=SchemeEnum.F1,
                    key_label=key_b64[:20] + "…",
                    result="success",
                    confidence=confidence,
                    elapsed_ms=elapsed,
                ))

                return DecryptedPayload(
                    scheme=SchemeEnum.F1,
                    confidence=confidence,
                    status=DecryptStatusEnum.SUCCESS if confidence >= 0.5 else DecryptStatusEnum.PARTIAL,
                    json_data=data,
                    key_label=key_b64[:20] + "…",
                )
        except Exception:
            pass

        elapsed = (time.monotonic() - start) * 1000
        trace.add_attempt(DecryptAttempt(
            scheme=SchemeEnum.F1,
            key_label=key_b64[:20] + "…",
            result="fail",
            confidence=0.0,
            elapsed_ms=elapsed,
        ))

    return DecryptedPayload(
        scheme=SchemeEnum.F1,
        confidence=0.0,
        status=DecryptStatusEnum.FAILED,
    )
