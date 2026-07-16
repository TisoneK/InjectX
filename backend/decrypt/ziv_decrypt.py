"""
InjectX — ZIVPN (.ziv) Decryption (Scheme H1)

ZIVPN config files use AES-256-GCM with PBKDF2-HMAC-SHA256 key derivation.

File format: "salt.iv.ciphertext_mac" (3 dot-separated base64 segments)
  - salt:     base64-encoded PBKDF2 salt (32 bytes)
  - iv:       base64-encoded AES-GCM nonce (12 bytes)
  - ciphertext_mac: base64-encoded ciphertext + auth tag (last 16 bytes)

Key derivation: PBKDF2(password, salt, hmac=SHA256) → 32-byte AES key
Decryption: AES-256-GCM(key, iv).decrypt_and_verify(ciphertext, mac)

The password is a hardcoded app constant. Current ZIVPN Tunnel builds
(v2.1.5, com.zi.zivpn) use 'SecurePart1..SecurePart5' concatenated —
extracted by static analysis of class o3.a / u3.c / v3.b in the APK
(BouncyCastle PKCS5S2 PBKDF2, 1000 iterations, 16-byte AES key, AES-GCM).
The original X-Tools password 'fubvx788b46v' works for older .ziv files.

Decrypted output: XML properties with <entry key="...">value</entry> pairs.

References: https://github.com/EstebanZxx/X-Tools (Main.py) for the legacy
password; ZIVPN Tunnel v2.1.5 APK (o3.a) for the current one.
"""

from __future__ import annotations

import base64
import re
import time
from typing import Optional

from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Protocol.KDF import PBKDF2

from ir.models import (
    DecryptedPayload,
    DecryptAttempt,
    DecryptStatusEnum,
    DecryptTrace,
    SchemeEnum,
)


# Known ZIVPN passwords — try all of them.
# The original X-Tools password works for older files; newer builds
# may have rotated the key (not yet publicly reversed).
_ZIV_PASSWORDS: list[bytes] = [
    # Current password, extracted from ZIVPN Tunnel v2.1.5 (com.zi.zivpn):
    # class o3.a builds it in <clinit> by concatenating five base64 parts
    # (U2VjdXJlUGFydDE=.."U2VjdXJlUGFydDU=" -> "SecurePart1".."SecurePart5"),
    # feeds it to a BouncyCastle PKCS5S2 (PBKDF2) generator (1000 iterations),
    # then AES-GCM-decrypts the salt.iv.ct payload. Matches this module's
    # PBKDF2(SHA256, dkLen=16, count=1000) + AES-GCM exactly.
    b"SecurePart1SecurePart2SecurePart3SecurePart4SecurePart5",
    b"fubvx788b46v",        # X-Tools / KMKZ era (older builds)
    b"fubvx788B4mev",       # variant
    b"zivpn",
    b"ZIVPN",
    b"com.zi.zivpn",
    b"zi.zivpn",
]


def decrypt_ziv(
    scheme: SchemeEnum,
    raw: bytes,
    trace: DecryptTrace,
    live_log=None,
) -> DecryptedPayload:
    """Decrypt ZIVPN .ziv config using AES-256-GCM + PBKDF2."""
    t0 = time.monotonic()

    def log(msg: str, result: str = "info"):
        elapsed = (time.monotonic() - t0) * 1000
        trace.add_attempt(DecryptAttempt(
            scheme=scheme,
            key_label="ziv",
            result=result,
            confidence=0.0 if result == "fail" else 0.5,
            elapsed_ms=elapsed,
            error_message=msg if result == "error" else "",
        ))
        if live_log:
            live_log.add("CRACK", msg, "info" if result != "fail" else "warn")

    # Parse the file content
    try:
        content = raw.decode("utf-8", errors="strict").strip()
    except Exception:
        log("File is not valid UTF-8", "fail")
        return DecryptedPayload(scheme=scheme, confidence=0.0, status=DecryptStatusEnum.FAILED)

    parts = content.split(".")
    if len(parts) != 3:
        log(f"Expected 3 dot-separated parts, got {len(parts)}", "fail")
        return DecryptedPayload(scheme=scheme, confidence=0.0, status=DecryptStatusEnum.FAILED)

    log("Decoding base64 segments (salt.iv.ciphertext_mac)...", "info")
    try:
        salt = base64.b64decode(parts[0])
        nonce = base64.b64decode(parts[1])
        ct_mac = base64.b64decode(parts[2])
    except Exception as e:
        log(f"Base64 decode failed: {e}", "fail")
        return DecryptedPayload(scheme=scheme, confidence=0.0, status=DecryptStatusEnum.FAILED)

    log(f"salt={len(salt)}B nonce={len(nonce)}B ct_mac={len(ct_mac)}B", "info")

    # Try each known password
    for pw in _ZIV_PASSWORDS:
        start = time.monotonic()
        try:
            key = PBKDF2(pw, salt, hmac_hash_module=SHA256)
            cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
            decrypted = cipher.decrypt_and_verify(ct_mac[:-16], ct_mac[-16:])
            elapsed = (time.monotonic() - start) * 1000

            text = decrypted.decode("utf-8", errors="ignore")
            log(f"SUCCESS with password {pw!r}", "info")

            trace.add_attempt(DecryptAttempt(
                scheme=scheme,
                key_label=f"ziv:{pw.decode()}",
                result="success",
                confidence=0.9,
                elapsed_ms=elapsed,
            ))

            # Parse XML <entry key="...">value</entry> pairs
            normalized = _parse_ziv_xml(text)
            return DecryptedPayload(
                scheme=scheme,
                confidence=0.9,
                status=DecryptStatusEnum.SUCCESS,
                json_data=normalized,
                key_label=f"ziv:{pw.decode()}",
            )
        except Exception:
            elapsed = (time.monotonic() - start) * 1000
            trace.add_attempt(DecryptAttempt(
                scheme=scheme,
                key_label=f"ziv:{pw.decode()}",
                result="fail",
                confidence=0.0,
                elapsed_ms=elapsed,
            ))

    log("All known ZIVPN passwords failed (MAC check) — key may have rotated", "fail")
    return DecryptedPayload(scheme=scheme, confidence=0.0, status=DecryptStatusEnum.FAILED)


def _parse_ziv_xml(text: str) -> dict:
    """Parse ZIVPN XML config into a flat dict.

    ZIVPN configs are XML with <entry key="fieldName">value</entry> pairs.
    """
    pattern = r'<entry key="([^"]*)">([^<]*)</entry>'
    matches = re.findall(pattern, text)

    out: dict = {}
    for key, value in matches:
        out[key] = value

    # Map common ZIVPN field names to IR field names. ZIVPN has two config
    # shapes: SSH-mode (sshServer/…) and UDP-mode (udpserver/…, tunnelType=4).
    field_map = {
        "sshServer": "ssh_server",
        "sshPort": "ssh_port",
        "sshUser": "ssh_user",
        "sshPass": "ssh_pass",
        "proxyHost": "proxy_host",
        "proxyPort": "proxy_port",
        "sni": "sni",
        "bugHost": "bug_host",
        "payload": "payload",
        "dnsServer": "dns",
        "remoteDns": "remote_dns",
        "notes": "notes",
        # UDP-mode (Hysteria-based) fields
        "udpserver": "host",
        "udpResolver": "remote_dns",
        "sniHost": "sni",
    }
    normalized: dict = {}
    for ziv_key, ir_key in field_map.items():
        if ziv_key in out:
            normalized[ir_key] = out[ziv_key]

    # Extract host:port from sshServer
    if "ssh_server" in normalized and isinstance(normalized["ssh_server"], str):
        ssh = normalized["ssh_server"]
        if ":" in ssh:
            parts = ssh.split(":")
            normalized.setdefault("host", parts[0])
            try:
                normalized.setdefault("port", int(parts[1]))
            except ValueError:
                pass
        else:
            normalized.setdefault("host", ssh)

    # Protocol detection
    if "ssh_server" in normalized:
        normalized["protocol"] = "ssh"

    # Carry through all fields
    normalized["_all_fields"] = out

    return normalized
