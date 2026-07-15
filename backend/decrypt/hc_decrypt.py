"""
InjectX — HTTP Custom (.hc) Decryption

Schemes A1–A4 based on HCTools/hcdecryptor and Pancho7532/HCDecryptor research.

A1: XOR deobfuscation + AES-128-ECB (SHA1 key derivation, ePro keys)
A2: Raw AES-128-ECB (no XOR, SHA1 key derivation)
A3: HC v233 double-encryption (XOR + plain key layer + SHA1 key layer)
A4: eProxy raw AES-128-ECB (pisahConk delimiter)
"""

from __future__ import annotations

import hashlib
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


# ── XOR deobfuscation values (Unicode chars from Pancho7532) ──────────────────

_XOR_VALUES = [
    0x3002, 0x3003, 0x3004, 0x3005, 0x3006, 0x3007,  # 。〃〄々〆〇
    0x3008, 0x3009, 0x300A, 0x300B, 0x300C, 0x300D,  # 〈〉《》「」
    0x300E, 0x300F, 0x3010, 0x3011, 0x3012, 0x3013,  # 『』【】〒〓
    0x3014, 0x3015,                                     # 〔〕
]

_SPLIT_CONFIG = "[splitConfig]"
_PISAH_CONK = "[pisahConk]"


def _sha1_key(password: str) -> bytes:
    """Derive AES-128 key: SHA1(password), take first 16 bytes."""
    digest = hashlib.sha1(password.encode("utf-8")).digest()
    return digest[:16]


def _xor_deobfuscate(data: bytes) -> bytes:
    """
    XOR deobfuscation step for A1/A3 schemes.
    Strips Unicode spacing chars and newlines, then XORs with cycling key.
    Returns base64-encoded ciphertext.
    """
    try:
        text = data.decode("utf-8", errors="ignore")
    except Exception:
        return b""

    # Strip Unicode spacing characters (U+2000–U+20EF) and newlines
    cleaned = []
    for ch in text:
        cp = ord(ch)
        if 0x2000 <= cp <= 0x20EF:
            continue
        if ch in ("\n", "\r"):
            continue
        cleaned.append(ch)

    # XOR with cycling key
    result = []
    b = 0
    for ch in cleaned:
        xored = ord(ch) ^ _XOR_VALUES[b]
        result.append(chr(xored))
        b += 1
        if b >= len(_XOR_VALUES):
            b = 0

    return "".join(result).encode("utf-8")


def _aes_ecb_decrypt(ciphertext_b64: bytes, key: bytes) -> Optional[bytes]:
    """
    AES-128-ECB decryption.
    Returns decrypted bytes or None on failure.
    """
    try:
        from Crypto.Cipher import AES
        # Strip whitespace and decode base64
        raw_b64 = ciphertext_b64.strip()
        import base64
        ciphertext = base64.b64decode(raw_b64)

        cipher = AES.new(key, AES.MODE_ECB)
        decrypted = cipher.decrypt(ciphertext)

        # Remove PKCS7 padding
        pad_len = decrypted[-1]
        if 1 <= pad_len <= 16:
            # Verify padding
            if all(b == pad_len for b in decrypted[-pad_len:]):
                decrypted = decrypted[:-pad_len]

        return decrypted
    except Exception:
        return None


def _try_aes_b64(raw: bytes, key: bytes) -> Optional[dict]:
    """Try AES-ECB decrypt on base64 input, parse as JSON. Returns dict or None."""
    decrypted = _aes_ecb_decrypt(raw, key)
    if decrypted is None:
        return None
    try:
        text = decrypted.decode("utf-8", errors="strict")
        # Validate: must contain [splitConfig] or [pisahConk] or be valid JSON
        if _SPLIT_CONFIG in text or _PISAH_CONK in text:
            return {"_raw_delimited": text, "_delimiter": _SPLIT_CONFIG if _SPLIT_CONFIG in text else _PISAH_CONK}
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return None


def _score_result(data: dict) -> float:
    """
    Confidence scoring for HC decryption results.
    More recognized fields = higher confidence.
    """
    if not data:
        return 0.0

    known_fields = {
        "payload", "proxyURL", "sshAddr", "sniValue", "bugHost",
        "connectionType", "tunnelType", "dns", "remoteDns",
        "sshServer", "sshPort", "sshUser", "sshPassword",
        "proxyHost", "proxyPort", "customPayload", "sslFile",
        "directConnect", "blockRooted", "expireDate",
    }

    raw_text = data.get("_raw_delimited", "")
    if raw_text:
        # Delimiter-based format — parse fields from split
        delimiter = data.get("_delimiter", _SPLIT_CONFIG)
        parts = raw_text.split(delimiter)
        field_count = len([p for p in parts if p.strip()])
        # Confidence based on how many meaningful parts we got
        return min(1.0, field_count / 10.0) if field_count >= 3 else 0.2

    # JSON format — check known fields
    keys = set(data.keys())
    overlap = len(keys & known_fields)
    if overlap >= 5:
        return 0.95
    elif overlap >= 3:
        return 0.8
    elif overlap >= 1:
        return 0.5
    return 0.2


def decrypt_hc(
    scheme: SchemeEnum,
    raw: bytes,
    keys: KeyStore,
    trace: DecryptTrace,
) -> DecryptedPayload:
    """
    Decrypt HTTP Custom (.hc) file using the specified scheme.

    Tries all keys in the ePro key set and returns the highest-confidence result.
    """
    epro_keys = keys.epro  # [0]=standard, [1]=v233

    if scheme == SchemeEnum.A1:
        return _decrypt_a1(raw, epro_keys, trace)
    elif scheme == SchemeEnum.A2:
        return _decrypt_a2(raw, epro_keys, trace)
    elif scheme == SchemeEnum.A3:
        return _decrypt_a3(raw, epro_keys, trace)
    elif scheme == SchemeEnum.A4:
        return _decrypt_a4(raw, epro_keys, trace)

    return DecryptedPayload(
        scheme=scheme,
        confidence=0.0,
        status=DecryptStatusEnum.FAILED,
    )


def _decrypt_a1(raw: bytes, epro_keys: list, trace: DecryptTrace) -> DecryptedPayload:
    """A1: XOR deobfuscation + AES-128-ECB with SHA1-derived keys."""
    xored = _xor_deobfuscate(raw)
    if not xored:
        return DecryptedPayload(scheme=SchemeEnum.A1, confidence=0.0, status=DecryptStatusEnum.FAILED)

    best_result: Optional[dict] = None
    best_confidence = 0.0
    best_key = ""

    for password in epro_keys[0]:
        start = time.monotonic()
        key = _sha1_key(password)
        result = _try_aes_b64(xored, key)
        elapsed = (time.monotonic() - start) * 1000

        if result is not None:
            confidence = _score_result(result)
            trace.add_attempt(DecryptAttempt(
                scheme=SchemeEnum.A1,
                key_label=password,
                result="success" if confidence > 0.3 else "fail",
                confidence=confidence,
                elapsed_ms=elapsed,
            ))
            if confidence > best_confidence:
                best_result = result
                best_confidence = confidence
                best_key = password
                if confidence >= 0.8:
                    break  # High confidence, no need to try more
        else:
            trace.add_attempt(DecryptAttempt(
                scheme=SchemeEnum.A1,
                key_label=password,
                result="fail",
                confidence=0.0,
                elapsed_ms=elapsed,
            ))

    if best_result and best_confidence > 0.0:
        return DecryptedPayload(
            scheme=SchemeEnum.A1,
            confidence=best_confidence,
            status=DecryptStatusEnum.SUCCESS if best_confidence >= 0.5 else DecryptStatusEnum.PARTIAL,
            json_data=best_result,
            key_label=best_key,
        )

    return DecryptedPayload(scheme=SchemeEnum.A1, confidence=0.0, status=DecryptStatusEnum.FAILED)


def _decrypt_a2(raw: bytes, epro_keys: list, trace: DecryptTrace) -> DecryptedPayload:
    """A2: Raw AES-128-ECB (no XOR) with SHA1-derived keys."""
    best_result: Optional[dict] = None
    best_confidence = 0.0
    best_key = ""

    for password in epro_keys[0]:
        start = time.monotonic()
        key = _sha1_key(password)
        result = _try_aes_b64(raw, key)
        elapsed = (time.monotonic() - start) * 1000

        if result is not None:
            confidence = _score_result(result)
            trace.add_attempt(DecryptAttempt(
                scheme=SchemeEnum.A2,
                key_label=password,
                result="success" if confidence > 0.3 else "fail",
                confidence=confidence,
                elapsed_ms=elapsed,
            ))
            if confidence > best_confidence:
                best_result = result
                best_confidence = confidence
                best_key = password
                if confidence >= 0.8:
                    break
        else:
            trace.add_attempt(DecryptAttempt(
                scheme=SchemeEnum.A2,
                key_label=password,
                result="fail",
                confidence=0.0,
                elapsed_ms=elapsed,
            ))

    if best_result and best_confidence > 0.0:
        return DecryptedPayload(
            scheme=SchemeEnum.A2,
            confidence=best_confidence,
            status=DecryptStatusEnum.SUCCESS if best_confidence >= 0.5 else DecryptStatusEnum.PARTIAL,
            json_data=best_result,
            key_label=best_key,
        )

    return DecryptedPayload(scheme=SchemeEnum.A2, confidence=0.0, status=DecryptStatusEnum.FAILED)


def _decrypt_a3(raw: bytes, epro_keys: list, trace: DecryptTrace) -> DecryptedPayload:
    """A3: HC v233 double-encryption — XOR + plain key, then SHA1 key."""
    xored = _xor_deobfuscate(raw)
    if not xored:
        return DecryptedPayload(scheme=SchemeEnum.A3, confidence=0.0, status=DecryptStatusEnum.FAILED)

    for v233_key_str in epro_keys[1]:
        start = time.monotonic()
        # Layer 1: AES with plain key (first 16 bytes of string)
        plain_key = v233_key_str.encode("utf-8")[:16]
        layer1 = _aes_ecb_decrypt(xored, plain_key)
        elapsed = (time.monotonic() - start) * 1000

        if layer1 is None:
            trace.add_attempt(DecryptAttempt(
                scheme=SchemeEnum.A3,
                key_label=v233_key_str,
                result="fail",
                confidence=0.0,
                elapsed_ms=elapsed,
            ))
            continue

        # Layer 2: Try SHA1-derived keys on layer1 result
        for password in epro_keys[0]:
            sha1_key = _sha1_key(password)
            result = _try_aes_b64(layer1, sha1_key)
            if result is not None:
                confidence = _score_result(result)
                trace.add_attempt(DecryptAttempt(
                    scheme=SchemeEnum.A3,
                    key_label=f"{v233_key_str}+{password}",
                    result="success" if confidence > 0.3 else "fail",
                    confidence=confidence,
                    elapsed_ms=elapsed,
                ))
                if confidence >= 0.5:
                    return DecryptedPayload(
                        scheme=SchemeEnum.A3,
                        confidence=confidence,
                        status=DecryptStatusEnum.SUCCESS if confidence >= 0.5 else DecryptStatusEnum.PARTIAL,
                        json_data=result,
                        key_label=f"{v233_key_str}+{password}",
                    )

        trace.add_attempt(DecryptAttempt(
            scheme=SchemeEnum.A3,
            key_label=v233_key_str,
            result="fail",
            confidence=0.0,
            elapsed_ms=elapsed,
        ))

    return DecryptedPayload(scheme=SchemeEnum.A3, confidence=0.0, status=DecryptStatusEnum.FAILED)


def _decrypt_a4(raw: bytes, epro_keys: list, trace: DecryptTrace) -> DecryptedPayload:
    """A4: eProxy — raw AES-128-ECB with [pisahConk] delimiter validation."""
    for password in epro_keys[0]:
        start = time.monotonic()
        key = _sha1_key(password)
        decrypted = _aes_ecb_decrypt(raw, key)
        elapsed = (time.monotonic() - start) * 1000

        if decrypted:
            try:
                text = decrypted.decode("utf-8", errors="strict")
                if _PISAH_CONK in text:
                    parts = text.split(_PISAH_CONK)
                    field_count = len([p for p in parts if p.strip()])
                    confidence = min(1.0, field_count / 15.0) if field_count >= 5 else 0.3
                    trace.add_attempt(DecryptAttempt(
                        scheme=SchemeEnum.A4,
                        key_label=password,
                        result="success",
                        confidence=confidence,
                        elapsed_ms=elapsed,
                    ))
                    return DecryptedPayload(
                        scheme=SchemeEnum.A4,
                        confidence=confidence,
                        status=DecryptStatusEnum.SUCCESS,
                        json_data={"_raw_delimited": text, "_delimiter": _PISAH_CONK},
                        key_label=password,
                    )
            except Exception:
                pass

        trace.add_attempt(DecryptAttempt(
            scheme=SchemeEnum.A4,
            key_label=password,
            result="fail",
            confidence=0.0,
            elapsed_ms=elapsed,
        ))

    return DecryptedPayload(scheme=SchemeEnum.A4, confidence=0.0, status=DecryptStatusEnum.FAILED)
