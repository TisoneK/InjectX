"""
InjectX — SocksHTTP (.nsh) Decryption

Scheme D1: AES-128-GCM with PBKDF2 key derivation.

Based on Pancho7532/HCDecryptor slipkDecryptor.lib.js research:
  - File format: dot-separated triplet "salt.iv.ciphertext_mac"
  - Key derivation: PBKDF2(password=key, salt=from_file, iterations=1000, keylen=16, hash=SHA-256)
  - Decryption: AES-128-GCM(ciphertext, derived_key, iv, auth_tag=last_16_bytes)
  - Output: XML <properties><entry key="...">value</entry>...</properties>
"""

from __future__ import annotations

import base64
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


def _pbkdf2_derive(password: bytes, salt: bytes, iterations: int = 1000, key_len: int = 16) -> bytes:
    """Derive AES-128 key using PBKDF2-HMAC-SHA256."""
    import hashlib
    return hashlib.pbkdf2_hmac("sha256", password, salt, iterations, dklen=key_len)


def _aes_gcm_decrypt(ciphertext: bytes, key: bytes, iv: bytes, tag: bytes) -> Optional[bytes]:
    """AES-128-GCM decryption with authentication tag."""
    try:
        from Crypto.Cipher import AES
        cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
        plaintext = cipher.decrypt_and_verify(ciphertext, tag)
        return plaintext
    except Exception:
        return None


def _parse_xml_properties(xml_text: str) -> dict:
    """Parse simple <properties><entry key="...">value</entry></properties> XML."""
    import re
    result = {}
    # Match <entry key="fieldName">value</entry>
    pattern = r'<entry\s+key="([^"]+)">([^<]*)</entry>'
    for match in re.finditer(pattern, xml_text):
        key, value = match.group(1), match.group(2)
        result[key] = value
    return result


def _score_nsh_result(data: dict) -> float:
    """Confidence scoring for NSH decryption."""
    if not data:
        return 0.0

    known_fields = {
        "sshUser", "sshServer", "sshPassword", "sshPort",
        "proxyUser", "proxyPasswd", "proxyRemoto", "proxyRemotoPorta",
        "payload", "sniStr", "hostSniSSL", "SNI",
        "dnsResolver", "tunnelType",
    }

    keys = set(data.keys())
    overlap = len(keys & known_fields)
    if overlap >= 5:
        return 0.95
    elif overlap >= 3:
        return 0.8
    elif overlap >= 1:
        return 0.5
    return 0.2


def decrypt_nsh(
    scheme: SchemeEnum,
    raw: bytes,
    keys: KeyStore,
    trace: DecryptTrace,
) -> DecryptedPayload:
    """Decrypt SocksHTTP (.nsh) config using AES-128-GCM + PBKDF2."""
    slipk_keys = keys.slipk

    try:
        content = raw.decode("utf-8", errors="strict").strip()
    except Exception:
        return DecryptedPayload(
            scheme=SchemeEnum.D1,
            confidence=0.0,
            status=DecryptStatusEnum.FAILED,
        )

    # Parse dot-separated triplet: salt.iv.ciphertext_mac
    parts = content.split(".")
    if len(parts) != 3:
        return DecryptedPayload(
            scheme=SchemeEnum.D1,
            confidence=0.0,
            status=DecryptStatusEnum.FAILED,
        )

    try:
        salt = base64.b64decode(parts[0])
        iv = base64.b64decode(parts[1])
        full_data = base64.b64decode(parts[2])
    except Exception:
        return DecryptedPayload(
            scheme=SchemeEnum.D1,
            confidence=0.0,
            status=DecryptStatusEnum.FAILED,
        )

    if len(iv) != 12 or len(full_data) < 17:
        return DecryptedPayload(
            scheme=SchemeEnum.D1,
            confidence=0.0,
            status=DecryptStatusEnum.FAILED,
        )

    ciphertext = full_data[:-16]
    auth_tag = full_data[-16:]

    best_result: Optional[dict] = None
    best_confidence = 0.0
    best_key = ""

    for key_str in slipk_keys:
        start = time.monotonic()
        try:
            # Derive key via PBKDF2
            derived_key = _pbkdf2_derive(key_str.encode("utf-8"), salt)
            # Decrypt
            decrypted = _aes_gcm_decrypt(ciphertext, derived_key, iv, auth_tag)

            if decrypted:
                text = decrypted.decode("utf-8", errors="strict")
                # Parse XML properties
                if "<properties>" in text or "<entry" in text:
                    data = _parse_xml_properties(text)
                    confidence = _score_nsh_result(data)
                    elapsed = (time.monotonic() - start) * 1000

                    trace.add_attempt(DecryptAttempt(
                        scheme=SchemeEnum.D1,
                        key_label=key_str,
                        result="success" if confidence > 0.3 else "fail",
                        confidence=confidence,
                        elapsed_ms=elapsed,
                    ))

                    if confidence > best_confidence:
                        best_result = data
                        best_confidence = confidence
                        best_key = key_str
                        if confidence >= 0.8:
                            break
        except Exception:
            pass

        elapsed = (time.monotonic() - start) * 1000
        trace.add_attempt(DecryptAttempt(
            scheme=SchemeEnum.D1,
            key_label=key_str,
            result="fail",
            confidence=0.0,
            elapsed_ms=elapsed,
        ))

    if best_result and best_confidence > 0.0:
        return DecryptedPayload(
            scheme=SchemeEnum.D1,
            confidence=best_confidence,
            status=DecryptStatusEnum.SUCCESS if best_confidence >= 0.5 else DecryptStatusEnum.PARTIAL,
            json_data=best_result,
            key_label=best_key,
        )

    return DecryptedPayload(
        scheme=SchemeEnum.D1,
        confidence=0.0,
        status=DecryptStatusEnum.FAILED,
    )
