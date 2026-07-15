"""
InjectX — NapsternetV (.npv4/.inpv) Decryption

Scheme C1: Subtraction cipher (NOT standard XOR).

Based on Pancho7532/HCDecryptor npv2Decryptor.lib.js research:
  - The file is UTF-8 text
  - Each char code is SUBTRACTED by the cycling key's char code (not XOR)
  - Key: "@))$@)))0.6931471805599453" (0.6931471805599453 = ln(2))
  - After decryption, parse as JSON with configType-based field extraction
"""

from __future__ import annotations

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


def _subtraction_decrypt(text: str, key: str) -> str:
    """
    NapsternetV decryption: subtract key char codes from ciphertext char codes.
    This is NOT XOR — it's character subtraction with cycling key.
    """
    result = []
    b = 0
    for i, ch in enumerate(text):
        result.append(chr(ord(ch) - ord(key[b])))
        b += 1
        if b >= len(key):
            b = 0
    return "".join(result)


def _score_npv_result(data: dict) -> float:
    """Confidence scoring for NPV decryption."""
    if not data or not isinstance(data, dict):
        return 0.0

    score = 0.0

    # Check for vmess structure
    vmess = data.get("vmess")
    if vmess and isinstance(vmess, dict):
        score += 0.4
        if vmess.get("address"):
            score += 0.15
        if vmess.get("port"):
            score += 0.1
        if vmess.get("id"):
            score += 0.15
        config_type = vmess.get("configType")
        if config_type is not None and str(config_type) in ("0", "1", "2", "3", "4"):
            score += 0.1

    # Check for security metadata
    security = data.get("security")
    if security and isinstance(security, dict):
        score += 0.1

    return min(1.0, score)


def decrypt_npv(
    scheme: SchemeEnum,
    raw: bytes,
    keys: KeyStore,
    trace: DecryptTrace,
) -> DecryptedPayload:
    """Decrypt NapsternetV (.npv4/.inpv) config using subtraction cipher."""
    npv_keys = keys.npv2

    try:
        text = raw.decode("utf-8", errors="strict")
    except Exception:
        return DecryptedPayload(
            scheme=SchemeEnum.C1,
            confidence=0.0,
            status=DecryptStatusEnum.FAILED,
        )

    best_result: Optional[dict] = None
    best_confidence = 0.0
    best_key = ""

    for key in npv_keys:
        start = time.monotonic()
        try:
            decrypted_text = _subtraction_decrypt(text, key)
            data = json.loads(decrypted_text)

            if isinstance(data, dict):
                confidence = _score_npv_result(data)
                elapsed = (time.monotonic() - start) * 1000

                trace.add_attempt(DecryptAttempt(
                    scheme=SchemeEnum.C1,
                    key_label=key,
                    result="success" if confidence > 0.3 else "fail",
                    confidence=confidence,
                    elapsed_ms=elapsed,
                ))

                if confidence > best_confidence:
                    best_result = data
                    best_confidence = confidence
                    best_key = key
                    if confidence >= 0.8:
                        break
            else:
                elapsed = (time.monotonic() - start) * 1000
                trace.add_attempt(DecryptAttempt(
                    scheme=SchemeEnum.C1,
                    key_label=key,
                    result="fail",
                    confidence=0.0,
                    elapsed_ms=elapsed,
                ))
        except (json.JSONDecodeError, Exception):
            elapsed = (time.monotonic() - start) * 1000
            trace.add_attempt(DecryptAttempt(
                scheme=SchemeEnum.C1,
                key_label=key,
                result="fail",
                confidence=0.0,
                elapsed_ms=elapsed,
            ))

    if best_result and best_confidence > 0.0:
        return DecryptedPayload(
            scheme=SchemeEnum.C1,
            confidence=best_confidence,
            status=DecryptStatusEnum.SUCCESS if best_confidence >= 0.5 else DecryptStatusEnum.PARTIAL,
            json_data=best_result,
            key_label=best_key,
        )

    return DecryptedPayload(
        scheme=SchemeEnum.C1,
        confidence=0.0,
        status=DecryptStatusEnum.FAILED,
    )
