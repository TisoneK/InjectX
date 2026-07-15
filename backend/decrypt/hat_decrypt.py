"""
InjectX — HA Tunnel Plus (.hat) Decryption

Scheme E1: AES-128-ECB with base64-encoded keys.

Based on Pancho7532/HCDecryptor aotDecryptor.lib.js research:
  - Encryption: AES-128-ECB
  - Keys: base64-encoded 16-byte values stored in keyFile.aot
  - Input: base64-encoded ciphertext
  - Validation: output starts with '{"' (valid JSON)
  - Three known JSON structures: "profile" (legacy), "profilev4" (Pro), "configuration" (ShellTun)
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


def _aes_ecb_decrypt(ciphertext_b64: str, key: bytes) -> Optional[bytes]:
    """AES-128-ECB decryption from base64 input."""
    try:
        from Crypto.Cipher import AES

        ciphertext = base64.b64decode(ciphertext_b64)
        cipher = AES.new(key, AES.MODE_ECB)
        decrypted = cipher.decrypt(ciphertext)

        # Remove PKCS7 padding
        pad_len = decrypted[-1]
        if 1 <= pad_len <= 16:
            if all(b == pad_len for b in decrypted[-pad_len:]):
                decrypted = decrypted[:-pad_len]

        return decrypted
    except Exception:
        return None


def _score_hat_result(data: dict) -> float:
    """Confidence scoring for HAT decryption."""
    if not data or not isinstance(data, dict):
        return 0.0

    score = 0.0

    # Check for known HAT JSON structures
    if "profile" in data:
        score += 0.4
        profile = data["profile"]
        if isinstance(profile, dict):
            if profile.get("custom_payload"):
                score += 0.15
            if profile.get("custom_sni"):
                score += 0.1
            if profile.get("primary_host"):
                score += 0.15
            if profile.get("connection_mode"):
                score += 0.1
    elif "profilev4" in data:
        score += 0.4
        profile = data["profilev4"]
        if isinstance(profile, dict):
            if profile.get("custom_payload"):
                score += 0.15
            if profile.get("custom_sni"):
                score += 0.1
            if profile.get("primary_host"):
                score += 0.15
            if profile.get("connection_mode"):
                score += 0.1
    elif "configuration" in data:
        score += 0.4
        config = data["configuration"]
        if isinstance(config, dict):
            if config.get("server_host"):
                score += 0.15
            if config.get("server_username"):
                score += 0.15
            if config.get("http_headers"):
                score += 0.1
    else:
        # Unknown structure — low confidence
        score = 0.2

    # Protection metadata
    if "protextras" in data:
        score += 0.1

    return min(1.0, score)


def decrypt_hat(
    scheme: SchemeEnum,
    raw: bytes,
    keys: KeyStore,
    trace: DecryptTrace,
) -> DecryptedPayload:
    """Decrypt HA Tunnel Plus (.hat) config using AES-128-ECB."""
    aot_keys = keys.aot

    try:
        content = raw.decode("utf-8", errors="strict").strip()
    except Exception:
        return DecryptedPayload(
            scheme=SchemeEnum.E1,
            confidence=0.0,
            status=DecryptStatusEnum.FAILED,
        )

    best_result: Optional[dict] = None
    best_confidence = 0.0
    best_key = ""

    for key_b64 in aot_keys:
        start = time.monotonic()
        try:
            key = base64.b64decode(key_b64)
            if len(key) != 16:
                continue

            decrypted = _aes_ecb_decrypt(content, key)
            if decrypted:
                text = decrypted.decode("utf-8", errors="strict")
                # Validate: must start with '{"'
                if text.startswith('{"'):
                    try:
                        data = json.loads(text)
                        confidence = _score_hat_result(data)
                        elapsed = (time.monotonic() - start) * 1000

                        trace.add_attempt(DecryptAttempt(
                            scheme=SchemeEnum.E1,
                            key_label=key_b64,
                            result="success" if confidence > 0.3 else "fail",
                            confidence=confidence,
                            elapsed_ms=elapsed,
                        ))

                        if confidence > best_confidence:
                            best_result = data
                            best_confidence = confidence
                            best_key = key_b64
                            if confidence >= 0.8:
                                break
                    except json.JSONDecodeError:
                        pass
        except Exception:
            pass

        elapsed = (time.monotonic() - start) * 1000
        trace.add_attempt(DecryptAttempt(
            scheme=SchemeEnum.E1,
            key_label=key_b64,
            result="fail",
            confidence=0.0,
            elapsed_ms=elapsed,
        ))

    if best_result and best_confidence > 0.0:
        return DecryptedPayload(
            scheme=SchemeEnum.E1,
            confidence=best_confidence,
            status=DecryptStatusEnum.SUCCESS if best_confidence >= 0.5 else DecryptStatusEnum.PARTIAL,
            json_data=best_result,
            key_label=best_key,
        )

    return DecryptedPayload(
        scheme=SchemeEnum.E1,
        confidence=0.0,
        status=DecryptStatusEnum.FAILED,
    )
