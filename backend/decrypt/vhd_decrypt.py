"""
InjectX — VHD (V2Ray/NapsternetV newer format) Decryption

Scheme G1: AES-128-CBC with raw ASCII key and IV.

Based on Pancho7532/HCDecryptor vhdDecryptor.lib.js research:
  - File format: base64-encoded ciphertext (with newlines stripped)
  - Key: "vmmEncryptionKey" (16 ASCII bytes)
  - IV: "vmmV2RayInt36489" (16 ASCII bytes)
  - Decrypted content: JSON with V2Ray/Xray outboundBean structure
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


def _aes_cbc_decrypt(ciphertext_b64: str, key: bytes, iv: bytes) -> Optional[bytes]:
    """AES-128-CBC decryption from base64 input."""
    try:
        from Crypto.Cipher import AES

        ciphertext = base64.b64decode(ciphertext_b64)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(ciphertext)

        # Remove PKCS7 padding
        pad_len = decrypted[-1]
        if 1 <= pad_len <= 16:
            if all(b == pad_len for b in decrypted[-pad_len:]):
                decrypted = decrypted[:-pad_len]

        return decrypted
    except Exception:
        return None


def _score_vhd_result(data: dict) -> float:
    """Confidence scoring for VHD decryption."""
    if not data or not isinstance(data, dict):
        return 0.0

    score = 0.0

    # Check for V2Ray/Xray outboundBean structure
    outbound = data.get("outboundBean")
    if outbound and isinstance(outbound, dict):
        score += 0.4
        settings = outbound.get("settings", {})
        if isinstance(settings, dict):
            vnext = settings.get("vnext")
            if vnext and isinstance(vnext, list) and len(vnext) > 0:
                score += 0.2
                first = vnext[0]
                if first.get("address"):
                    score += 0.1
                if first.get("port"):
                    score += 0.05

        stream = outbound.get("streamSettings")
        if stream and isinstance(stream, dict):
            score += 0.15

    # Security metadata
    if data.get("hardwareLock") is not None or data.get("passwordLock") is not None:
        score += 0.1

    return min(1.0, score)


def decrypt_vhd(
    scheme: SchemeEnum,
    raw: bytes,
    keys: KeyStore,
    trace: DecryptTrace,
) -> DecryptedPayload:
    """Decrypt VHD (V2Ray/NapsternetV newer format) config using AES-128-CBC."""
    vhd_keys = keys.vhd  # [0]=keys, [1]=IVs

    vhd_key_list = vhd_keys[0] if len(vhd_keys) > 0 else []
    vhd_iv_list = vhd_keys[1] if len(vhd_keys) > 1 else []

    try:
        content = raw.decode("utf-8", errors="strict").replace("\n", "").strip()
    except Exception:
        return DecryptedPayload(
            scheme=SchemeEnum.G1,
            confidence=0.0,
            status=DecryptStatusEnum.FAILED,
        )

    best_result: Optional[dict] = None
    best_confidence = 0.0
    best_key_combo = ""

    for key_str in vhd_key_list:
        for iv_str in vhd_iv_list:
            start = time.monotonic()
            try:
                key = key_str.encode("utf-8")[:16]
                iv = iv_str.encode("utf-8")[:16]

                decrypted = _aes_cbc_decrypt(content, key, iv)
                if decrypted:
                    text = decrypted.decode("utf-8", errors="strict")
                    data = json.loads(text)
                    confidence = _score_vhd_result(data)
                    elapsed = (time.monotonic() - start) * 1000

                    trace.add_attempt(DecryptAttempt(
                        scheme=SchemeEnum.G1,
                        key_label=f"{key_str}+IV:{iv_str}",
                        result="success" if confidence > 0.3 else "fail",
                        confidence=confidence,
                        elapsed_ms=elapsed,
                    ))

                    if confidence > best_confidence:
                        best_result = data
                        best_confidence = confidence
                        best_key_combo = f"{key_str}+IV:{iv_str}"
                        if confidence >= 0.8:
                            break
            except Exception:
                pass

            elapsed = (time.monotonic() - start) * 1000
            trace.add_attempt(DecryptAttempt(
                scheme=SchemeEnum.G1,
                key_label=f"{key_str}+IV:{iv_str}",
                result="fail",
                confidence=0.0,
                elapsed_ms=elapsed,
            ))

        if best_confidence >= 0.8:
            break

    if best_result and best_confidence > 0.0:
        return DecryptedPayload(
            scheme=SchemeEnum.G1,
            confidence=best_confidence,
            status=DecryptStatusEnum.SUCCESS if best_confidence >= 0.5 else DecryptStatusEnum.PARTIAL,
            json_data=best_result,
            key_label=best_key_combo,
        )

    return DecryptedPayload(
        scheme=SchemeEnum.G1,
        confidence=0.0,
        status=DecryptStatusEnum.FAILED,
    )
