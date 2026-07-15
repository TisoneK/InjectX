"""
InjectX — HTTP Injector (.ehi) v2 Decryption (Scheme B2)

Newer HTTP Injector files (v6.3+) use a multi-layer encryption scheme
that the legacy B1 scheme (2-stage AES + field XOR) cannot handle.

Algorithm (reverse-engineered by @HABIBI_1ST / @NullptrO):

  1. Parse EHI binary header: [2-byte len][magic "ehi"][4-byte ver]
     [4-byte len][2-byte len][version string]... → extract encrypted payload

  2. Layer 1: AES-256-CBC decrypt with L1_KEY, try 6 known IVs
     (3 BYPASS_IVS + 3 STANDARD_IVS). Result is "parts[0]:parts[1]:parts[2]"

  3. Layer 2: AES-128-CBC decrypt parts[2] with L2_KEY_STATIC and IV=parts[0]
     → "garbage" bytes

  4. Layer 3: XXTEA decrypt garbage with EOO_MASTER_KEY → JSON config

  5. If matched IV is a STANDARD_IVS (not bypass):
     - Extract configData field
     - XOR-decrypt with configSalt → base64 payload
     - Derive Argon2id key from master key + salt
     - ChaCha20-Poly1305 decrypt → final JSON

  6. Decode inner fields: XOR layer with configSalt, or EHIMSG decode
     for configMessage

Output: a dict with normalized fields: payload, sshServer, sshPort,
sshUser, sshPass, proxyURL, sniHostname, customDns1, customDns2, etc.

Reference: https://github.com/ENIGMATIC-MAN/DECRYPTION_SCRIPTS/blob/main/HTTPINJECTOR.py
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import struct
import time
from typing import Any, Optional

import base64

from Crypto.Cipher import AES, ChaCha20_Poly1305
from Crypto.Util.Padding import unpad

try:
    from argon2.low_level import hash_secret_raw, Type
    ARGON2_AVAILABLE = True
except ImportError:
    ARGON2_AVAILABLE = False

from ir.models import (
    DecryptedPayload,
    DecryptAttempt,
    DecryptStatusEnum,
    DecryptTrace,
    SchemeEnum,
)


# ── Constants ────────────────────────────────────────────────────────────────

class _EHIConstants:
    L1_KEY: bytes = bytes.fromhex("7e1210f7aab956f7a668bda6e57feddb7f84ad840aef8d27b1b969959be3ab6c")
    L2_KEY_STATIC: bytes = bytes.fromhex("b2bc617c32d8b9eb1943a5ffa8051eea")
    EOO_MASTER_KEY: bytes = b"null=V5kU5+FFrY\x00"
    BYPASS_IVS = (
        bytes.fromhex("221d572349555f1d112133236b1f4a3f"),
        bytes.fromhex("5543494c53443e3f4a6a4539384e776a"),
        bytes.fromhex("374c2541575e4d531a3c327b75431e5f"),
    )
    STANDARD_IVS = (
        bytes.fromhex("2c5d1147bbad422b3b334d4d235f1a53"),
        bytes.fromhex("522b01433a5e8b2fc7549e1ad368e541"),
        bytes.fromhex("337a1035aaedf3458ca167e92d74b839"),
    )

    STD_ALPHABET: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    CUSTOM_ALPHABET: str = "RkLC2QaVMPYgGJW/A4f7qzDb9e+t6Hr0Zp8OlNyjuxKcTw1o5EIimhBn3UvdSFXs"
    TRANSLATION_TABLE = str.maketrans(CUSTOM_ALPHABET, STD_ALPHABET)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _custom_b64_decode(encoded_str: str) -> bytes:
    clean_str = encoded_str.replace("?", "")
    if (rem := len(clean_str) % 4):
        clean_str += "=" * (4 - rem)
    return base64.b64decode(clean_str.translate(_EHIConstants.TRANSLATION_TABLE))


def _decrypt_xor_layer(ciphertext_str: str, key: str) -> Optional[str]:
    if not ciphertext_str or not ciphertext_str.strip():
        return ciphertext_str
    with contextlib.suppress(Exception):
        hex_bytes_raw = _custom_b64_decode(ciphertext_str[::-1])
        hex_string = hex_bytes_raw.decode("ascii")
        if len(hex_string) % 2 != 0:
            hex_string = f"0{hex_string}"
        raw_bytes = bytes.fromhex(hex_string)
        key_len = len(key)
        decrypted_bytes = bytearray(
            b ^ ord(key[i % key_len]) for i, b in enumerate(raw_bytes) if (b ^ ord(key[i % key_len])) != 0
        )
        plaintext = decrypted_bytes.decode("utf-8")
        if plaintext and (sum(1 for c in plaintext if ord(c) < 32 and ord(c) not in (9, 10, 13)) / len(plaintext)) > 0.5:
            return None
        return plaintext
    return None


def _decode_config_message(ciphertext_str: str) -> str:
    if not ciphertext_str or not ciphertext_str.strip():
        return ciphertext_str
    with contextlib.suppress(Exception):
        padded_str = ciphertext_str + "=" * ((4 - len(ciphertext_str) % 4) % 4)
        raw_bytes = base64.b64decode(padded_str)
        utf16_bytes = raw_bytes.decode("utf-8", errors="replace").encode("utf-16-be", errors="surrogatepass")
        num_chars = len(utf16_bytes) // 2
        java_chars = struct.unpack(f">{num_chars}H", utf16_bytes)
        key_chars = [ord(c) for c in "EHIMSG"]
        key_len = len(key_chars)
        xored_chars = [jc ^ key_chars[i % key_len] for i, jc in enumerate(java_chars)]
        xored_bytes = struct.pack(f">{num_chars}H", *xored_chars)
        return xored_bytes.decode("utf-16-be", errors="surrogatepass").encode("utf-16", "surrogatepass").decode("utf-16")
    return ciphertext_str


def _decode_inner_fields(parsed_json: dict, salt_key: str) -> dict:
    cleaned_json = {}
    vital_keys = {"overwriteServerData"}
    for k, v in parsed_json.items():
        if isinstance(v, str) and v.strip():
            decrypted_val = _decode_config_message(v) if k == "configMessage" else _decrypt_xor_layer(v, salt_key)
            if decrypted_val is not None:
                cleaned_json[k] = decrypted_val
            elif k in vital_keys:
                cleaned_json[k] = v
        else:
            cleaned_json[k] = v
    return cleaned_json


def _xxtea_decrypt(data: bytes, key: bytes) -> bytes:
    if not data:
        return b""
    if (rem := len(data) % 4):
        data += b"\x00" * (4 - rem)
    k = struct.unpack("<4I", key.ljust(16, b"\x00")[:16])
    n = len(data) // 4
    v = list(struct.unpack(f"<{n}I", data))
    delta = 0x9E3779B9
    sum_val = ((6 + 52 // n) * delta) & 0xFFFFFFFF
    y = v[0]
    while sum_val != 0:
        e = (sum_val >> 2) & 3
        for p in range(n - 1, 0, -1):
            z = v[p - 1]
            mx = (((z >> 5) ^ (y << 2)) + ((y >> 3) ^ (z << 4))) ^ ((sum_val ^ y) + (k[(p & 3) ^ e] ^ z))
            y = v[p] = (v[p] - mx) & 0xFFFFFFFF
        z = v[n - 1]
        mx = (((z >> 5) ^ (y << 2)) + ((y >> 3) ^ (z << 4))) ^ ((sum_val ^ y) + (k[(0 & 3) ^ e] ^ z))
        y = v[0] = (v[0] - mx) & 0xFFFFFFFF
        sum_val = (sum_val - delta) & 0xFFFFFFFF
    decrypted = struct.pack(f"<{n}I", *v)
    length = v[-1]
    return decrypted[:length] if 0 < length <= n * 4 else decrypted.rstrip(b"\x00")


def _parse_ehi_bytes(file_bytes: bytes) -> Optional[bytes]:
    """Parse the EHI binary header and extract the encrypted payload."""
    try:
        f = io.BytesIO(file_bytes)

        def r_utf() -> str:
            if len(l_bytes := f.read(2)) < 2:
                return ""
            return f.read(struct.unpack(">H", l_bytes)[0]).decode("utf-8", errors="ignore")

        r_utf()       # magic "ehi"
        f.read(8)     # version + padding
        r_utf()       # app version string
        f.read(8)     # more header
        if len(p_len_bytes := f.read(4)) < 4:
            return None
        p_len = struct.unpack(">I", p_len_bytes)[0]
        f.read(8)     # padding
        return f.read(p_len)
    except struct.error:
        return None


def _generate_master_key(config: dict) -> bytes:
    payload = "".join(str(p) for p in (
        config.get("configAesKey", ""),
        config.get("configIdentifier", ""),
        config.get("configSalt", ""),
        str(config.get("configTimestamp", 0)),
        str(config.get("configExpiryTimestamp", 0)),
        config.get("lockModes", ""),
        config.get("lockModesHash", ""),
        config.get("configHwid", ""),
        config.get("configLockMobileOperatorId", ""),
    ) if p)
    return hashlib.sha256(payload.encode("utf-8")).digest()


# ── Main entry point ─────────────────────────────────────────────────────────

def decrypt_ehi_v2(
    scheme: SchemeEnum,
    raw: bytes,
    trace: DecryptTrace,
    live_log=None,
) -> DecryptedPayload:
    """Decrypt EHI v2 multi-layer encryption (scheme B2)."""
    t0 = time.monotonic()

    def log(msg: str, result: str = "info"):
        elapsed = (time.monotonic() - t0) * 1000
        trace.add_attempt(DecryptAttempt(
            scheme=scheme,
            key_label="ehi_v2",
            result=result,
            confidence=0.0 if result == "fail" else 0.5,
            elapsed_ms=elapsed,
            error_message=msg if result == "error" else "",
        ))
        if live_log:
            live_log.add("CRACK", msg, "info" if result != "fail" else "warn")

    if not ARGON2_AVAILABLE:
        log("argon2-cffi not installed — EHI v2 decryption unavailable", "fail")
        return DecryptedPayload(scheme=scheme, confidence=0.0, status=DecryptStatusEnum.FAILED)

    log("Parsing EHI binary header...", "info")
    payload = _parse_ehi_bytes(raw)
    if not payload:
        log("EHI header parse failed — not a v2 EHI file", "fail")
        return DecryptedPayload(scheme=scheme, confidence=0.0, status=DecryptStatusEnum.FAILED)

    log(f"Payload extracted ({len(payload)} bytes) · trying 6 IVs for L1 AES-256-CBC...", "info")
    config: Optional[dict] = None
    matched_iv: Optional[bytes] = None

    for iv in _EHIConstants.BYPASS_IVS + _EHIConstants.STANDARD_IVS:
        with contextlib.suppress(Exception):
            c1 = AES.new(_EHIConstants.L1_KEY, AES.MODE_CBC, iv)
            l1_text = unpad(c1.decrypt(payload), 16).decode("utf-8")
            if (parts := l1_text.split(":")) and len(parts) >= 3:
                c2 = AES.new(_EHIConstants.L2_KEY_STATIC, AES.MODE_CBC, base64.b64decode(parts[0]))
                garbage = unpad(c2.decrypt(base64.b64decode(parts[2])), 16)
                final_raw = _xxtea_decrypt(garbage, _EHIConstants.EOO_MASTER_KEY)
                if (start := final_raw.find(b"{")) != -1:
                    config = json.loads(final_raw[start:].decode("utf-8", errors="ignore"))
                    matched_iv = iv
                    iv_label = "BYPASS" if iv in _EHIConstants.BYPASS_IVS else "STANDARD"
                    log(f"L1+L2+XXTEA succeeded with {iv_label} IV", "info")
                    break

    if not config:
        log("All 6 IVs failed — not a v2 EHI or unsupported variant", "fail")
        return DecryptedPayload(scheme=scheme, confidence=0.0, status=DecryptStatusEnum.FAILED)

    target_salt = config.get("configSalt", "EVZJNI")

    if matched_iv in _EHIConstants.BYPASS_IVS:
        log("Bypass IV matched — skipping Argon2/ChaCha20 layer", "info")
        parsed_final = config
    else:
        log(f"Standard IV matched · decrypting configData with salt={target_salt!r}...", "info")
        target_data = config.get("configData")
        if not target_data or not (aaa_result := _decrypt_xor_layer(target_data, target_salt)):
            log("configData XOR decrypt failed", "fail")
            return DecryptedPayload(scheme=scheme, confidence=0.0, status=DecryptStatusEnum.FAILED)

        raw_payload = base64.b64decode(aaa_result)
        if len(raw_payload) <= 50:
            log("Decoded payload too short", "fail")
            return DecryptedPayload(scheme=scheme, confidence=0.0, status=DecryptStatusEnum.FAILED)

        log("Deriving Argon2id key + ChaCha20-Poly1305 decrypt...", "info")
        try:
            argon_key = hash_secret_raw(
                secret=_generate_master_key(config),
                salt=raw_payload[0x0A:0x1A],
                time_cost=int.from_bytes(raw_payload[1:5], "little"),
                memory_cost=int.from_bytes(raw_payload[5:9], "little"),
                parallelism=raw_payload[9],
                hash_len=32,
                type=Type.ID,
            )
            cipher3 = ChaCha20_Poly1305.new(key=argon_key, nonce=raw_payload[0x1A:0x32])
            cipher3.update(raw_payload[:0x1A])  # AAD
            decrypted_json_bytes = cipher3.decrypt_and_verify(raw_payload[0x32:-16], raw_payload[-16:])
            parsed_final = json.loads(decrypted_json_bytes.decode("utf-8", errors="ignore"))
            log("Argon2 + ChaCha20-Poly1305 succeeded", "info")
        except Exception as e:
            log(f"Argon2/ChaCha20 decrypt failed: {e}", "fail")
            return DecryptedPayload(scheme=scheme, confidence=0.0, status=DecryptStatusEnum.FAILED)

    log("Decoding inner fields (XOR + EHIMSG)...", "info")
    cleaned_final_json = _decode_inner_fields(parsed_final, target_salt)

    # Parse nested JSON fields
    for json_field in ("v2rRawJson", "overwriteServerData"):
        if json_field in cleaned_final_json and isinstance(raw_str := cleaned_final_json[json_field], str):
            try:
                if (start_idx := raw_str.find("{")) != -1 and (end_idx := raw_str.rfind("}")) != -1:
                    parsed_obj = json.loads(raw_str[start_idx:end_idx + 1], strict=False)
                    cleaned_final_json[json_field] = json.loads(parsed_obj, strict=False) if isinstance(parsed_obj, str) else parsed_obj
            except Exception:
                pass

    log(f"Extraction complete · {len(cleaned_final_json)} fields recovered", "info")

    # Build normalized dict for the IR parser
    normalized = _build_normalized_dict(cleaned_final_json)

    return DecryptedPayload(
        scheme=scheme,
        confidence=0.95,
        status=DecryptStatusEnum.SUCCESS,
        json_data=normalized,
        key_label="ehi_v2_argon2_chacha20",
    )


def _build_normalized_dict(config: dict) -> dict:
    """Convert EHI v2 JSON into a flat dict the IR's _normalize_ehi() can consume."""
    out: dict[str, Any] = {}

    # Direct field mappings (EHI field names → IR field names)
    field_map = {
        "payload": "payload",
        "remoteProxy": "proxy_host",
        "sshServer": "ssh_server",
        "sshPort": "ssh_port",
        "sshUser": "ssh_user",
        "sshPassword": "ssh_pass",
        "sniHostname": "sni",
        "customDns1": "dns",
        "customDns2": "remote_dns",
        "proxyURL": "proxy_host",
        "proxyPort": "proxy_port",
        "configMessage": "notes",
        "v2rRawJson": "v2ray",
    }
    for ehi_key, ir_key in field_map.items():
        if ehi_key in config and config[ehi_key]:
            out[ir_key] = config[ehi_key]

    # Extract host:port from sshServer if present
    if "ssh_server" in out and isinstance(out["ssh_server"], str) and ":" in out["ssh_server"]:
        parts = out["ssh_server"].split(":")
        if len(parts) >= 2:
            out.setdefault("host", parts[0])
            try:
                out.setdefault("port", int(parts[1]))
            except ValueError:
                pass

    # V2Ray config
    v2r = config.get("v2rRawJson")
    if v2r and isinstance(v2r, dict):
        out["v2ray"] = v2r
        if "address" in v2r:
            out.setdefault("host", v2r["address"])
        if "port" in v2r:
            try:
                out.setdefault("port", int(v2r["port"]))
            except (ValueError, TypeError):
                pass
    elif v2r and isinstance(v2r, str):
        out["v2ray_raw"] = v2r

    # Overwrite server data (embedded server config)
    osd = config.get("overwriteServerData")
    if osd and isinstance(osd, dict):
        out["overwrite_server"] = osd

    # Protocol detection
    if "v2rRawJson" in config or any(k.startswith("v2r") for k in config):
        out["protocol"] = "v2ray"
    elif out.get("ssh_server"):
        out["protocol"] = "ssh"

    # Carry through all fields for raw view
    out["_all_fields"] = config

    return out
