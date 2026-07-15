"""
InjectX — HTTP Custom (.hc) v2.7+ Decryption (Scheme A5)

Newer HTTP Custom files (v2.6+) use a completely different multi-layer
encryption scheme than the legacy A1–A4 (XOR + AES-128-ECB with ePro keys).

Algorithm (reverse-engineered by @HABIBI_1ST / ENIGMATIC-MAN):

  1. Initial XOR layer with hex key "e382e4b8adc386f09f9293"
     (file_bytes.decode('utf-8').encode('latin-1') → XOR → decode utf-8)

  2. ChaCha20 decrypt with key index [5], nonce = b'\\xdb' * 8, seek(64)
     Result is a JSON envelope with structure:
       { "cfg": { "content": "...", "b": "...", "f": "..." }, ... }
     or older: { "a": {...}, "xy": "...", "uv": "...", "bb": "...", ... }

  3. RST decryption (XOR with bytes(range(2,22)) → base64-decode →
     AES-128-ECB with one of 9 known RST keys) on cfg.content / xy

  4. Per-field decryption:
     - Each field is split by [splitConfig] (or custom delimiter)
     - Each value may be:
       * ChaCha20-encrypted hex/latin-1/utf-8 → decrypt with derived nonce
       * JKL-XOR encoded (old or new key)
       * Braille-encoded (SSH credentials)
       * z3a decimal-encoded (credentials)

Output: a dict with normalized field names matching the IR's expectations.

Reference: https://github.com/ENIGMATIC-MAN/DECRYPTION_SCRIPTS/blob/main/HTTPCUSTOM.py
"""

from __future__ import annotations

import base64
import contextlib
import json
import re
import time
from typing import Any, Optional

from Crypto.Cipher import AES, ChaCha20
from Crypto.Util.Padding import unpad

from ir.models import (
    DecryptedPayload,
    DecryptAttempt,
    DecryptStatusEnum,
    DecryptTrace,
    SchemeEnum,
)


# ── Constants ────────────────────────────────────────────────────────────────

class _HC27:
    """Cryptographic constants for HC v2.7+ decryption."""

    CHACHA_KEYS = [
        bytes.fromhex("2be4342943c6f91ff58987f41a1aafd179eeb4e053f5cea55b11d6a7db58bd7d"),
        bytes.fromhex("3380aa278b744ba5b529a7f32fa803e48749280dae378345d9b526cf1dbce372"),
        bytes.fromhex("cea9305c95168b162a335b137c61983b8df54e6375da01136547890f14c5fac3"),
        bytes.fromhex("4beeace0e42bae8f29470cf40cf2dfacd5f4e1f751912bf52e803c8c85792193"),
        bytes.fromhex("f8e5f6ebea90558eb32229da24fd0fb7d813091dafe89bb2954fda33b4c60f63"),
        bytes.fromhex("81342f558a6273bac4548d473f54c4ffc7c41747dee81369acab9c787d41ab9c"),
        bytes.fromhex("45635e6fc70486e2fd10d3c2b4780f02d0b4c5f4aa929fc54f86bb8fa4417944"),
        bytes.fromhex("3d632a251c9820f2baf83e15498d27548fc67921cb437f8ce48505989378adea"),
    ]

    RST_KEYS = [
        b"JN1k3YHc2.6_v235", b"JN1k3YHc_2.7_v71", b"JN1k3YHc2.7.ps69",
        b"JN1k3YHc2.7.6950", b"Jn1K3yHc2.8.ps08", b"Jn1K3yHc2.9.ps6c",
        b"Zk:L7>WKaiK*s9>D", b"!<f!&WIlM**R.B0X", b"b4a5opinx2uloec6",
    ]

    JKL_KEY_OLD = bytes([
        0xd5, 0xd4, 0xd3, 0xd2, 0xd1, 0xd0, 0xcf, 0xce, 0xcd, 0xcc,
        0xbd, 0xbc, 0xbb, 0xba, 0xb9, 0xb8, 0xb7, 0xb6, 0xb5, 0xb4,
    ])

    JKL_KEY_NEW = bytes([
        8, 9, 10, 11, 12, 13, 14, 15, 17, 17,
        5, 4, 3, 2, 1, 0, 255, 254, 253, 252,
    ])

    TOKEN_MAP = {
        0: "payload", 1: "proxy_host", 2: "lock_all_config", 3: "blocked_by_root",
        4: "expiry_time", 5: "note_enabled", 6: "notes", 7: "ssh_server",
        8: "mobile_data_lock", 9: "unlock_user_pass", 10: "openvpn_config",
        11: "openvpn_creds", 12: "sni", 13: "unlock_user_pass_2",
        14: "unknown_14", 15: "blocked_by_hwid", 16: "cloud_config",
        17: "psiphon", 18: "name", 19: "block_area",
        20: "connection_mode", 21: "blocked_by_password", 22: "unknown_22",
        23: "extra_sniffer", 24: "psiphon_2", 25: "v2ray_enabled",
        26: "v2ray_config", 27: "version", 28: "slowdns_enabled",
        29: "slowdns_server", 30: "slowdns_publickey", 31: "dns_resolver",
    }

    BRAILLE_ALPHABET = (
        "⠁⠃⠉⠙⠑⠋⠛⠓⠊⠚⠅⠇⠍⠝⠕⠏⠟⠗⠎⠞⠥⠧⠺⠭⠽⠵"
        "⠼⠁⠼⠃⠼⠉⠼⠙⠼⠑⠼⠋⠼⠛⠼⠓⠼⠊⠼⠚"
    )

    STATIC_NONCE = b"\xdb" * 8
    RST_XOR_KEY = bytes(range(2, 22))  # length 20
    INITIAL_XOR_KEY = bytes.fromhex("e382e4b8adc386f09f9293")


# ── Helpers ──────────────────────────────────────────────────────────────────

def _clean_hex(raw_str: str) -> str:
    if not raw_str:
        return ""
    clean = re.sub(r"[^0-9a-fA-F]", "", raw_str)
    return f"0{clean}" if len(clean) % 2 != 0 else clean


def _is_hex(s: str) -> bool:
    return bool(s and len(s) >= 16 and re.fullmatch(r"^[0-9a-fA-F]+$", s))


def _is_mostly_printable(s: str, strict: bool = False) -> bool:
    if not s:
        return False
    if len(s) < 4:
        return True
    printable_count = sum(1 for c in s if c.isprintable() or c in "\t\n\r")
    return (printable_count / len(s)) > (0.90 if strict else 0.80)


def _extract_z3a(data: str, iv: int) -> str:
    """z3a decimal-pair decoder used for SSH/proxy credentials."""
    if not data:
        return ""
    new_data = bytearray()
    for m in re.finditer(r"(-?\d+)\.(-?\d+)", data):
        val11, val22 = int(m.group(1)) - iv, int(m.group(2)) - iv
        with contextlib.suppress(Exception):
            if (divisor := 1 << val22) != 0:
                new_data.append((val11 // divisor) % 256)
    return new_data.decode("utf-8", errors="ignore")


def _decrypt_braille(ciphertext: str) -> str:
    try:
        return bytes(
            (_HC27.BRAILLE_ALPHABET.index(ciphertext[i]) * 16 +
             _HC27.BRAILLE_ALPHABET.index(ciphertext[i + 1])) & 255
            for i in range(0, len(ciphertext) - 1, 2)
        ).decode("utf-8")
    except ValueError:
        return ciphertext


def _process_credentials(raw_val: str, is_ssh: bool = False) -> str:
    """Decrypt SSH string 'host:port@user:pass' or proxy 'user:pass'."""
    if not raw_val:
        return raw_val

    if is_ssh and raw_val and raw_val[0] in _HC27.BRAILLE_ALPHABET:
        raw_val = _decrypt_braille(raw_val)

    pattern = r"^([\w\.-]+):([\d\-]+)@(.+):(.+)$" if is_ssh else r"^([^:]+):(.+)$"
    if (match := re.match(pattern, raw_val)):
        groups = match.groups()
        u_enc, p_enc = groups[-2:]
        u_dec = _extract_z3a(u_enc, len(re.findall(r"(-?\d+)\.(-?\d+)", u_enc)))
        p_dec = _extract_z3a(p_enc, len(re.findall(r"(-?\d+)\.(-?\d+)", p_enc)))
        final_user = u_dec or u_enc
        final_pass = p_dec or p_enc
        if is_ssh:
            return f"{groups[0]}:{groups[1]}@{final_user}:{final_pass}"
        return f"{final_user}:{final_pass}"
    return raw_val


def _abc_decrypt(raw_input: str, key: bytes, nonce: bytes = _HC27.STATIC_NONCE) -> str:
    """ChaCha20 decrypt with seek(64) — used for outer envelope + per-field."""
    if not raw_input:
        return ""
    with contextlib.suppress(Exception):
        data = bytes.fromhex(_clean_hex(raw_input))
        if len(data) > 16:
            cipher = ChaCha20.new(key=key, nonce=nonce)
            cipher.seek(64)
            decrypted = cipher.decrypt(data[:-16])
            return decrypted.decode("utf-8", errors="ignore")
    return ""


def _rst_decrypt(encrypted_str: str) -> Optional[str]:
    """RST layer: XOR with bytes(range(2,22)) → base64 → AES-128-ECB."""
    with contextlib.suppress(Exception):
        b64_string = bytes(
            b ^ _HC27.RST_XOR_KEY[i % 20]
            for i, b in enumerate(encrypted_str.encode("utf-8"))
        )
        aes_ciphertext = base64.b64decode(b64_string)
        for aes_key in _HC27.RST_KEYS:
            with contextlib.suppress(Exception):
                decrypted = unpad(
                    AES.new(aes_key, AES.MODE_ECB).decrypt(aes_ciphertext),
                    AES.block_size,
                )
                dec_str = decrypted.decode("utf-8", errors="ignore")
                if "[splitConfig]" in dec_str:
                    return dec_str
    return None


def _jkl_decrypt(input_str: str, is_new: bool = False) -> str:
    """JKL XOR layer — reversible transformation on base64 bytes."""
    if not input_str:
        return input_str
    active_key = _HC27.JKL_KEY_NEW if is_new else _HC27.JKL_KEY_OLD
    with contextlib.suppress(Exception):
        pad = len(input_str) % 4
        padded_str = input_str + "=" * (4 - pad) if pad else input_str
        data = bytearray(base64.b64decode(padded_str, validate=True))
        for i, d in enumerate(data):
            k = active_key[i % 20]
            data[i] = (((d ^ 0xff) & 0xca) | (d & 0x35)) ^ (((k ^ 0xff) & 0xca) | (k & 0x35))
        return base64.b64decode(data.decode("utf-8"), validate=True).decode("utf-8")
    return input_str


def _decrypt_field(token: str, dynamic_nonce: bytes) -> str:
    """Decrypt a single config field — try ChaCha20, JKL, Braille, z3a."""
    if not token or token in {"true", "false", "lifeTime", "[splitPsiphon][splitPsiphon]"} or token.startswith("<"):
        return token

    candidates: list[bytes] = []
    if _is_hex(clean_h := _clean_hex(token)) and len(clean_h) >= 32:
        with contextlib.suppress(Exception):
            candidates.append(bytes.fromhex(clean_h))
    if len(token) > 16:
        with contextlib.suppress(Exception):
            candidates.append(token.encode("latin-1"))
        with contextlib.suppress(Exception):
            candidates.append(token.encode("utf-8"))

    unique_cands = list(dict.fromkeys(candidates))
    for data_bytes in (c for c in unique_cands if len(c) > 16):
        ciphertext = data_bytes[:-16]
        for chacha_key in _HC27.CHACHA_KEYS:
            with contextlib.suppress(Exception):
                cipher = ChaCha20.new(key=chacha_key, nonce=dynamic_nonce)
                cipher.seek(64)
                dec_str = cipher.decrypt(ciphertext).decode("utf-8", errors="ignore")
                for is_new in (True, False):
                    if (out := _jkl_decrypt(dec_str, is_new)) and out != dec_str and _is_mostly_printable(out):
                        return out
                if _is_mostly_printable(dec_str, strict=True) and any(
                    x in dec_str for x in ("HTTP", "@", ":", "{")
                ) or dec_str.isalnum():
                    return dec_str

    for is_new in (True, False):
        if (out := _jkl_decrypt(token, is_new)) != token and _is_mostly_printable(out):
            return out

    return token


def _extract_initial_payload(file_bytes: bytes) -> Optional[str]:
    """Apply initial XOR layer with the known hex key."""
    with contextlib.suppress(Exception):
        try:
            encrypted_data = file_bytes.decode("utf-8", errors="ignore").encode("latin-1", errors="ignore")
        except Exception:
            encrypted_data = file_bytes
        k = _HC27.INITIAL_XOR_KEY
        k_len = len(k)
        return bytes(b ^ k[i % k_len] for i, b in enumerate(encrypted_data)).decode("utf-8")
    return None


# ── Main entry point ─────────────────────────────────────────────────────────

def decrypt_hc_v27(
    scheme: SchemeEnum,
    raw: bytes,
    trace: DecryptTrace,
    live_log=None,
) -> DecryptedPayload:
    """
    Decrypt HC v2.7+ multi-layer encryption.

    Returns a DecryptedPayload with json_data containing the normalized config
    fields: payload, proxy_host, sni, ssh_server, ssh_port, ssh_user, ssh_pass,
    notes, openvpn_config, v2ray_config, etc.
    """
    t0 = time.monotonic()

    def log(msg: str, result: str = "info"):
        elapsed = (time.monotonic() - t0) * 1000
        trace.add_attempt(DecryptAttempt(
            scheme=scheme,
            key_label="hc_v27",
            result=result,
            confidence=0.0 if result == "fail" else 0.5,
            elapsed_ms=elapsed,
            error_message=msg if result == "error" else "",
        ))
        if live_log:
            live_log.add("CRACK", msg, "info" if result != "fail" else "warn")

    log("Applying initial XOR layer (key: e382e4b8...)", "info")
    hex_payload = _extract_initial_payload(raw)
    if not hex_payload:
        log("Initial XOR failed — not a v2.7+ file", "fail")
        return DecryptedPayload(scheme=scheme, confidence=0.0, status=DecryptStatusEnum.FAILED)

    log("ChaCha20 outer envelope decrypt (key idx 5)...", "info")
    outer = _abc_decrypt(hex_payload, _HC27.CHACHA_KEYS[5])
    if not outer or not outer.startswith("{"):
        log("Outer envelope did not yield JSON — not v2.7+ format", "fail")
        return DecryptedPayload(scheme=scheme, confidence=0.0, status=DecryptStatusEnum.FAILED)

    try:
        json_obj = json.loads(outer)
    except Exception as e:
        log(f"Outer JSON parse failed: {e}", "fail")
        return DecryptedPayload(scheme=scheme, confidence=0.0, status=DecryptStatusEnum.FAILED)

    if not isinstance(json_obj, dict):
        log("Outer JSON is not an object", "fail")
        return DecryptedPayload(scheme=scheme, confidence=0.0, status=DecryptStatusEnum.FAILED)

    cfg_obj = json_obj.get("cfg", {})
    is_new_format = isinstance(cfg_obj, dict) and "content" in cfg_obj

    meta_values: dict[str, str] = {}
    protections: dict[str, str] = {}

    if is_new_format:
        for k, name in {"b": "hwid", "f": "area"}.items():
            if val := str(json_obj.get(k) or cfg_obj.get(k) or ""):
                meta_values[name] = protections[name] = val
        target_cipher = cfg_obj.get("content")
        split_delim = "[splitConfig]"
        log(f"New format detected · area={meta_values.get('area', '?')}", "info")
    else:
        obj_a = json_obj.get("a") if isinstance(json_obj.get("a"), dict) else {}
        for k, name in {"bb": "hwid", "e": "password", "fe": "area", "ed": "provider"}.items():
            if val := (json_obj.get(k) if k == "e" else obj_a.get(k)):
                if dec_val := _abc_decrypt(str(val), _HC27.CHACHA_KEYS[7]):
                    meta_values[name] = protections[name] = dec_val
        target_cipher = json_obj.get("xy") or obj_a.get("xy")
        split_delim = json_obj.get("uv") or obj_a.get("uv") or "[splitConfig]"
        log(f"Legacy v2.7 format · split_delim={split_delim!r}", "info")

    if not target_cipher or not split_delim:
        log("No target cipher or split delimiter found", "fail")
        return DecryptedPayload(scheme=scheme, confidence=0.0, status=DecryptStatusEnum.FAILED)

    # Derive dynamic nonce
    def to_hex(s):
        return s.encode().hex() if s else ""

    h = meta_values.get("hwid")
    p = meta_values.get("password")
    pr = meta_values.get("provider")
    a = meta_values.get("area")
    derived_hex = (to_hex(h) * 2) if h and not any((p, pr, a)) else (to_hex(p) + to_hex(h) + to_hex(pr) + to_hex(a))

    dynamic_nonce = bytearray(_HC27.STATIC_NONCE)
    if derived_hex:
        with contextlib.suppress(Exception):
            for i, b in enumerate(bytes.fromhex(derived_hex)[:8]):
                dynamic_nonce[i] = b

    # Decrypt the ciphertext block
    log("Decrypting main config block (RST → AES-128-ECB)...", "info")
    xy_dec: Optional[str] = None
    if is_new_format:
        xy_dec = _rst_decrypt(str(target_cipher))
        if not xy_dec:
            log("RST decrypt failed · trying ChaCha20 fallbacks...", "info")
            for idx, key in enumerate(_HC27.CHACHA_KEYS):
                if (temp := _abc_decrypt(str(target_cipher), key)) and split_delim in temp:
                    xy_dec = temp
                    log(f"ChaCha20 key #{idx} succeeded", "info")
                    break
    else:
        xy_dec = _abc_decrypt(str(target_cipher), _HC27.CHACHA_KEYS[1])

    if not xy_dec:
        log("All main-block decrypt attempts failed", "fail")
        return DecryptedPayload(scheme=scheme, confidence=0.0, status=DecryptStatusEnum.FAILED)

    log(f"Main block decrypted · {len(xy_dec.split(split_delim))} fields", "info")

    # Parse fields
    config_data: dict[str, Any] = {}
    raw_tokens = xy_dec.split(str(split_delim))
    for i, token in enumerate(raw_tokens):
        if i in {22, 24}:
            continue
        label = _HC27.TOKEN_MAP.get(i, f"field_{i}")
        final_out: Any = token

        try:
            if is_new_format:
                final_out = _decrypt_field(token, bytes(dynamic_nonce))
            else:
                if _is_hex(token):
                    final_out = _abc_decrypt(token, _HC27.CHACHA_KEYS[7], bytes(dynamic_nonce))
                final_out = _jkl_decrypt(final_out, is_new=False)

            if i == 7:
                final_out = _process_credentials(final_out, is_ssh=True)
            elif i == 11:
                final_out = _process_credentials(final_out, is_ssh=False)

            if final_out and isinstance(final_out, str):
                final_out = final_out.replace(
                    "88a05e8772eac3e5703e0cd26c6e6f23de72fb09f7ee5a43283d1681f19d", ""
                )
                with contextlib.suppress(Exception):
                    if final_out.startswith(("{", "[")):
                        final_out = json.loads(final_out)

                if not (isinstance(final_out, str) and _is_hex(final_out)):
                    config_data[label] = final_out
        except Exception:
            pass

    log(f"Extraction complete · {len(config_data)} fields recovered", "info")

    # Build the final normalized dict that the IR parser can consume
    normalized = _build_normalized_dict(config_data, protections)

    return DecryptedPayload(
        scheme=scheme,
        confidence=0.95,
        status=DecryptStatusEnum.SUCCESS,
        json_data=normalized,
        key_label="hc_v27_chacha20",
    )


def _build_normalized_dict(config: dict, protections: dict) -> dict:
    """
    Convert the v2.7 token-map fields into a flat dict that the IR's
    _normalize_hc() can consume via _apply_field_map().
    """
    out: dict[str, Any] = {}

    # Direct fields
    if "payload" in config:
        out["payload"] = config["payload"]
    if "proxy_host" in config:
        # proxy_host may be "host:port" — split it
        proxy = str(config["proxy_host"])
        if ":" in proxy:
            host, _, port = proxy.rpartition(":")
            out["proxy_host"] = host
            try:
                out["proxy_port"] = int(port)
            except ValueError:
                out["proxy_port"] = port
        else:
            out["proxy_host"] = proxy
    if "sni" in config:
        out["sni"] = config["sni"]
    if "ssh_server" in config:
        # ssh_server field is "host:port@user:pass"
        ssh_val = str(config["ssh_server"])
        m = re.match(r"^([\w\.-]+):(\d+)@(.+):(.+)$", ssh_val)
        if m:
            out["ssh_server"] = m.group(1)
            out["ssh_port"] = int(m.group(2))
            out["ssh_user"] = m.group(3)
            out["ssh_pass"] = m.group(4)
            out["host"] = m.group(1)
            out["port"] = int(m.group(2))
        else:
            out["ssh_server"] = ssh_val
            out["host"] = ssh_val
    if "openvpn_creds" in config:
        # openvpn_creds is "user:pass"
        creds = str(config["openvpn_creds"])
        if ":" in creds:
            u, _, p = creds.partition(":")
            # Don't override ssh creds if present
            out.setdefault("ssh_user", u)
            out.setdefault("ssh_pass", p)
    if "notes" in config:
        out["notes"] = config["notes"]
    if "openvpn_config" in config:
        out["openvpn_config"] = config["openvpn_config"]
    if "v2ray_config" in config:
        out["v2ray"] = config["v2ray_config"]
    if "version" in config:
        out["hc_version"] = config["version"]
    if "name" in config:
        out["config_name"] = config["name"]
    if "connection_mode" in config:
        out["connection_type"] = config["connection_mode"]
    if "dns_resolver" in config:
        out["dns"] = config["dns_resolver"]
    if "psiphon" in config:
        out["psiphon"] = config["psiphon"]
    if "slowdns_server" in config:
        out["slowdns_server"] = config["slowdns_server"]

    # Booleans / metadata
    if "blocked_by_root" in config:
        out["blocks_root"] = config["blocked_by_root"] == "true"
    if "blocked_by_hwid" in config:
        out["blocks_hwid"] = config["blocked_by_hwid"] == "true"
    if "blocked_by_password" in config:
        out["blocks_password"] = config["blocked_by_password"] == "true"
    if "lock_all_config" in config:
        out["locked"] = config["lock_all_config"] == "true"
    if "expiry_time" in config:
        out["expiry"] = config["expiry_time"]

    # Protections (hwid, area, password, provider)
    if protections:
        out["protections"] = protections

    # Carry through all parsed tokens for the raw JSON view
    out["_all_fields"] = config

    return out
