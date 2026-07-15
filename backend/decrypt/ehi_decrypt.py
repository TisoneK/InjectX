"""
InjectX — HTTP Injector (.ehi) Decryption

Scheme B1: Two-stage AES decryption + field-level XOR with custom base64.

Based on Pancho7532/HCDecryptor evoziDecryptor.lib.js research:
  Stage 1: AES-256-CBC with brute-forced key × IV combinations
  Stage 2: AES-128-CBC on the last-colon-segment
  Stage 3: Field deobfuscation (reverse + custom base64 + XOR with configSalt)

Custom base64 charset for EHI:
  RkLC2QaVMPYgGJW/A4f7qzDb9e+t6Hr0Zp8OlNyjuxKcTw1o5EIimhBn3UvdSFXs?
  Padding: ? (instead of =)
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


# ── Custom Base64 charset for EHI ─────────────────────────────────────────────

_EHI_B64_CHARSET = "RkLC2QaVMPYgGJW/A4f7qzDb9e+t6Hr0Zp8OlNyjuxKcTw1o5EIimhBn3UvdSFXs?"
_EHI_B64_PADDING = "?"
_STD_B64_CHARSET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"


def _custom_b64_decode(encoded: str, charset: str = _EHI_B64_CHARSET, padding: str = _EHI_B64_PADDING) -> Optional[bytes]:
    """Decode a string using a custom base64 charset."""
    try:
        # Build translation table: custom charset → standard charset
        trans = str.maketrans(charset[:64], _STD_B64_CHARSET[:64])
        # Replace custom padding with standard padding
        standardized = encoded.replace(padding, "=")
        # Translate charset
        standardized = standardized.translate(trans)
        # Add padding if needed
        missing = len(standardized) % 4
        if missing:
            standardized += "=" * (4 - missing)
        return base64.b64decode(standardized)
    except Exception:
        return None


def _xor_with_key(data: str, key: str) -> str:
    """Repeating XOR: data[i] ^ key[i % len(key)]."""
    result = []
    for i, ch in enumerate(data):
        result.append(chr(ord(ch) ^ ord(key[i % len(key)])))
    return "".join(result)


def _reverse_string(s: str) -> str:
    return s[::-1]


def _aes_cbc_decrypt(ciphertext: bytes, key: bytes, iv: bytes, key_size: int = 256) -> Optional[bytes]:
    """AES-CBC decryption. key_size=256 for Stage 1, key_size=128 for Stage 2."""
    try:
        from Crypto.Cipher import AES
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(ciphertext)

        # Remove PKCS7 padding
        pad_len = decrypted[-1]
        if 1 <= pad_len <= (key_size // 8):
            if all(b == pad_len for b in decrypted[-pad_len:]):
                decrypted = decrypted[:-pad_len]

        return decrypted
    except Exception:
        return None


def _deobfuscate_ehi_field(value: str, config_salt: str) -> Optional[str]:
    """
    Deobfuscate a single EHI field:
    1. Reverse the string
    2. Custom base64 decode
    3. XOR with configSalt
    """
    try:
        reversed_val = _reverse_string(value)
        decoded = _custom_b64_decode(reversed_val)
        if decoded is None:
            return None

        # Convert bytes to hex string, then XOR
        hex_str = decoded.hex()
        # The Pancho7532 algorithm: parse hex pairs to chars, then XOR with key
        pre_data = ""
        i = 0
        while i < len(hex_str):
            if i + 2 <= len(hex_str):
                pre_data += chr(int(hex_str[i:i + 2], 16))
                i += 2
            else:
                break

        result = _xor_with_key(pre_data, config_salt)
        return result
    except Exception:
        return None


def _score_ehi_result(data: dict) -> float:
    """Confidence scoring for EHI decryption results."""
    if not data or not isinstance(data, dict):
        return 0.0

    known_fields = {
        "Payload", "PayloadMethod", "PayloadURL", "RemoteProxy", "RemoteProxyPort",
        "SSHHost", "SSHPort", "SSHUser", "SSHPassword", "SSL", "DNS",
        "OnlineHost", "ProxyType", "Version", "V2Ray", "configSalt",
    }

    keys = set(data.keys())
    overlap = len(keys & known_fields)

    # Check if essential fields are present and non-empty
    has_ssh = bool(data.get("SSHHost") or data.get("SSHUser"))
    has_payload = bool(data.get("Payload"))
    has_proxy = bool(data.get("RemoteProxy"))

    score = 0.3  # Base score for valid JSON
    score += min(0.3, overlap * 0.03)
    if has_ssh:
        score += 0.15
    if has_payload:
        score += 0.15
    if has_proxy:
        score += 0.1

    return min(1.0, score)


def decrypt_ehi(
    scheme: SchemeEnum,
    raw: bytes,
    keys: KeyStore,
    trace: DecryptTrace,
) -> DecryptedPayload:
    """
    Decrypt HTTP Injector (.ehi) config.

    Two-stage AES + field deobfuscation.
    """
    evozi_keys = keys.evozi  # [0]=AES-256 keys, [1]=AES-128 keys, [2]=IVs

    aes256_keys = evozi_keys[0]
    aes128_keys = evozi_keys[1] if len(evozi_keys) > 1 else []
    ivs = evozi_keys[2] if len(evozi_keys) > 2 else []

    if not aes256_keys or not ivs:
        return DecryptedPayload(
            scheme=SchemeEnum.B1,
            confidence=0.0,
            status=DecryptStatusEnum.FAILED,
        )

    # Step 0: Strip header (40 bytes for regular EHI, 41 for Lite)
    is_lite = b"ehil" in raw[:50]
    offset = 41 if is_lite else 40
    payload_data = raw[offset:]

    # Stage 1: AES-256-CBC — try all key × IV combinations
    best_stage1_result: Optional[tuple[bytes, str, str]] = None
    best_stage1_confidence = 0.0

    for key_b64 in aes256_keys:
        for iv_str in ivs:
            start = time.monotonic()
            try:
                key = base64.b64decode(key_b64)
                iv = iv_str.encode("utf-8")[:16]
                decrypted = _aes_cbc_decrypt(payload_data, key, iv, key_size=256)

                if decrypted:
                    text = decrypted.decode("utf-8", errors="strict")
                    # Split on colon, take last segment
                    last_segment = text.rsplit(":", 1)[-1] if ":" in text else text
                    # Quick validation: must be base64-like
                    if len(last_segment) > 20:
                        elapsed = (time.monotonic() - start) * 1000
                        trace.add_attempt(DecryptAttempt(
                            scheme=SchemeEnum.B1,
                            key_label=f"S1:{key_b64[:12]}…+IV:{iv_str}",
                            result="success",
                            confidence=0.3,  # Stage 1 only — not final
                            elapsed_ms=elapsed,
                        ))
                        if best_stage1_result is None:
                            best_stage1_result = (last_segment.encode("utf-8"), key_b64, iv_str)
                            best_stage1_confidence = 0.3
                        continue
            except Exception:
                pass

            elapsed = (time.monotonic() - start) * 1000
            trace.add_attempt(DecryptAttempt(
                scheme=SchemeEnum.B1,
                key_label=f"S1:{key_b64[:12]}…+IV:{iv_str}",
                result="fail",
                confidence=0.0,
                elapsed_ms=elapsed,
            ))

    if best_stage1_result is None:
        return DecryptedPayload(
            scheme=SchemeEnum.B1,
            confidence=0.0,
            status=DecryptStatusEnum.FAILED,
        )

    stage1_data, winning_s1_key, winning_s1_iv = best_stage1_result

    # Stage 2: AES-128-CBC on last segment
    for key_b64 in aes128_keys:
        for iv_str in ivs:
            start = time.monotonic()
            try:
                key = base64.b64decode(key_b64)
                iv = iv_str.encode("utf-8")[:16]
                decrypted = _aes_cbc_decrypt(stage1_data, key, iv, key_size=128)

                if decrypted:
                    text = decrypted.decode("utf-8", errors="strict")
                    if "configSalt" in text:
                        # Fix malformed JSON prefix (first 17 chars)
                        fixed = '{"a":"' + text[17:]

                        try:
                            data = json.loads(fixed)
                        except json.JSONDecodeError:
                            # Try alternative fix
                            fixed = '{"a"' + text[14:]
                            try:
                                data = json.loads(fixed)
                            except json.JSONDecodeError:
                                continue

                        # Stage 3: Deobfuscate sensitive fields
                        config_salt = data.get("configSalt", "EVZJNI")
                        obfuscated_fields = [
                            "host", "user", "password", "remoteProxy", "payload",
                            "sniHostname", "shadowsocksConfig", "httpObfsSettings",
                            "v2rWsPath",
                        ]
                        for field in obfuscated_fields:
                            if field in data and isinstance(data[field], str) and data[field]:
                                deobfuscated = _deobfuscate_ehi_field(data[field], config_salt)
                                if deobfuscated:
                                    data[field] = deobfuscated

                        confidence = _score_ehi_result(data)
                        elapsed = (time.monotonic() - start) * 1000
                        trace.add_attempt(DecryptAttempt(
                            scheme=SchemeEnum.B1,
                            key_label=f"S2:{key_b64[:12]}…+IV:{iv_str}",
                            result="success",
                            confidence=confidence,
                            elapsed_ms=elapsed,
                        ))

                        return DecryptedPayload(
                            scheme=SchemeEnum.B1,
                            confidence=confidence,
                            status=DecryptStatusEnum.SUCCESS if confidence >= 0.5 else DecryptStatusEnum.PARTIAL,
                            json_data=data,
                            key_label=f"S1:{winning_s1_key[:12]}…+S2:{key_b64[:12]}…",
                        )
            except Exception:
                pass

            elapsed = (time.monotonic() - start) * 1000
            trace.add_attempt(DecryptAttempt(
                scheme=SchemeEnum.B1,
                key_label=f"S2:{key_b64[:12]}…+IV:{iv_str}",
                result="fail",
                confidence=0.0,
                elapsed_ms=elapsed,
            ))

    return DecryptedPayload(
        scheme=SchemeEnum.B1,
        confidence=0.0,
        status=DecryptStatusEnum.FAILED,
    )
