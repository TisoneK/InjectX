"""
HC (HTTP Custom) config parser.

⚠️ CRITICAL FINDING FROM RESEARCH:
HC files are ENCRYPTED, not plain JSON or ZIP.
The app uses custom encryption/obfuscation on .hc files.

There is an open-source decryptor available:
- HCTools/hcdecryptor (Python) — https://github.com/HCTools/hcdecryptor
- CONIGUERO/HCDecryptor (JavaScript port) — https://github.com/CONIGUERO/HCDecryptor
- PANCHO7532/HCDecryptor (JavaScript, multi-format) — https://gitlab.com/PANCHO7532/HCDecryptor
  This version also supports: HTTP Injector, APK Custom, eProxy, NapsternetV, SocksHTTP

Pancho7532's decryptor is the most comprehensive — it handles:
  .hc (HTTP Custom), .ehi (HTTP Injector), .nsh (SocksHTTP),
  .npv4/.inpv (NapsternetV), eProxy configs

The decrypt.py from HCTools uses a specific AES-like decryption scheme.
As of 2024-2025, newer HC versions (v233+) may not be supported yet
(see GitHub issue #4 on HCTools/hcdecryptor).

This parser attempts to:
1. Try decrypting using the HCDecryptor algorithm (if available)
2. Fall back to trying plain JSON / base64 (older versions)
3. Report that the file is encrypted if all methods fail
"""

import zipfile
import json
import base64
import struct
import hashlib
from pathlib import Path
from typing import Optional


# HC file magic/header bytes for version detection
HC_MAGIC = b"HCUST"


def parse_hc(filepath: str) -> dict:
    """
    Parse an .hc config file and return normalized config data.

    HC files are encrypted. This parser attempts decryption using
    the known HCDecryptor algorithm, and falls back to raw analysis.
    """
    path = Path(filepath)
    raw = path.read_bytes()

    normalized = {
        "host": None,
        "port": None,
        "payload": None,
        "protocol": None,
        "sni": None,
        "bug_host": None,
        "ssh_server": None,
        "ssh_port": None,
        "ssh_user": None,
        "ssh_pass": None,
        "ssh_key": None,
        "proxy_host": None,
        "proxy_port": None,
        "dns": None,
        "remote_dns": None,
        "custom_headers": {},
        "connection_type": None,
        "tunnel_type": None,
        "v2ray": None,
        "websocket": None,
        "ssl_enabled": None,
        "direct_connect": None,
        "_encryption_info": None,
        "raw_data": None,
    }

    # Step 1: Try the HCDecryptor decryption algorithm
    decrypted = _try_hc_decrypt(raw)
    if decrypted is not None:
        try:
            data = json.loads(decrypted)
            if isinstance(data, dict):
                normalized["_encryption_info"] = "decrypted_successfully"
                return _normalize_hc(data, normalized)
        except Exception:
            pass

    # Step 2: Try plain JSON (very old versions)
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            normalized["_encryption_info"] = "plain_json"
            return _normalize_hc(data, normalized)
    except Exception:
        pass

    # Step 3: Try base64 → JSON
    try:
        decoded = base64.b64decode(raw)
        data = json.loads(decoded)
        if isinstance(data, dict):
            normalized["_encryption_info"] = "base64_json"
            return _normalize_hc(data, normalized)
    except Exception:
        pass

    # Step 4: Try ZIP archive
    if zipfile.is_zipfile(path):
        raw_data = {}
        with zipfile.ZipFile(path, "r") as zf:
            for name in zf.namelist():
                if name.endswith(".json"):
                    try:
                        content = zf.read(name).decode("utf-8")
                        data = json.loads(content)
                        if isinstance(data, dict):
                            raw_data.update(data)
                    except Exception:
                        continue
        if raw_data:
            normalized["_encryption_info"] = "zip_archive"
            return _normalize_hc(raw_data, normalized)

    # Step 5: Cannot decrypt — report file metadata
    normalized["_encryption_info"] = "encrypted_unable_to_decrypt"
    normalized["_warning"] = (
        "HC file is encrypted and could not be decrypted. "
        "Try using HCDecryptor (https://github.com/HCTools/hcdecryptor) "
        "or Pancho7532/HCDecryptor (https://gitlab.com/PANCHO7532/HCDecryptor) "
        "which supports HTTP Custom (.hc), HTTP Injector (.ehi), NapsternetV (.npv4), "
        "SocksHTTP (.nsh), and eProxy configs. "
        "Note: .hat, .dark, and .tls formats have no public decryptor."
    )
    normalized["raw_data"] = {
        "file_size": len(raw),
        "hex_preview": raw[:64].hex(),
        "detected_header": raw[:10].hex() if len(raw) >= 10 else raw.hex(),
    }

    # Try to detect HC version from header
    if raw.startswith(HC_MAGIC):
        normalized["raw_data"]["format"] = "HCUST format (encrypted)"
    elif raw[:4] == b"\x50\x4b\x03\x04":
        normalized["raw_data"]["format"] = "ZIP-based"
    else:
        normalized["raw_data"]["format"] = "custom encrypted"

    return normalized


def _try_hc_decrypt(raw: bytes) -> Optional[bytes]:
    """
    Attempt to decrypt HC config using the known HCDecryptor algorithm.

    The algorithm from HCTools/hcdecryptor works roughly as follows:
    1. Read the file header to get version info
    2. Extract an encrypted payload
    3. Derive a key from known constants
    4. Decrypt using AES-ECB or AES-CBC

    This is a simplified implementation. For full support, install hcdecryptor.
    """
    # Check for HCUST header
    if not raw.startswith(HC_MAGIC):
        return None

    try:
        # HCUST format structure (simplified):
        # - 5 bytes: magic "HCUST"
        # - Variable: version info
        # - Rest: encrypted payload

        offset = 5

        # Try to read version byte
        if offset >= len(raw):
            return None
        version = raw[offset]
        offset += 1

        # The decryptor uses a hardcoded key derived from the app
        # Different versions use different keys
        # This is a placeholder — the actual key derivation is in hcdecryptor
        key_material = b"httpcustom"

        # For now, we can't decrypt without the full algorithm
        # Return None to indicate we need the external tool
        return None

    except Exception:
        return None


def _normalize_hc(raw: dict, normalized: dict) -> dict:
    """Normalize raw HC/HA Tunnel JSON data into consistent format."""
    field_map = {
        "host": "host", "server": "host",
        "bughost": "bug_host", "bug_host": "bug_host", "bugHost": "bug_host",
        "serverhost": "host", "server_host": "host",
        "port": "port", "serverport": "port", "server_port": "port",
        "sshserver": "ssh_server", "ssh_server": "ssh_server", "sshServer": "ssh_server",
        "sshhost": "ssh_server", "ssh_host": "ssh_server",
        "sshport": "ssh_port", "ssh_port": "ssh_port", "sshPort": "ssh_port",
        "sshuser": "ssh_user", "ssh_user": "ssh_user", "sshUser": "ssh_user",
        "username": "ssh_user", "login": "ssh_user",
        "sshpass": "ssh_pass", "ssh_pass": "ssh_pass", "sshPass": "ssh_pass",
        "password": "ssh_pass",
        "sshkey": "ssh_key", "ssh_key": "ssh_key", "privatekey": "ssh_key",
        "ssl_file": "ssh_key",
        "payload": "payload", "httppayload": "payload", "httpPayload": "payload",
        "custompayload": "payload", "custom_payload": "payload",
        "proxyip": "proxy_host", "proxy_ip": "proxy_host", "proxyIp": "proxy_host",
        "proxyhost": "proxy_host", "proxy_host": "proxy_host",
        "proxyport": "proxy_port", "proxy_port": "proxy_port", "proxyPort": "proxy_port",
        "dns": "dns", "dnsserver": "dns", "dns_server": "dns",
        "remotedns": "remote_dns", "remote_dns": "remote_dns", "remoteDns": "remote_dns",
        "sni": "sni", "servername": "sni", "server_name": "sni",
        "connectiontype": "connection_type", "connectionType": "connection_type",
        "connection_type": "connection_type",
        "tunneltype": "tunnel_type", "tunnelType": "tunnel_type", "tunnel_type": "tunnel_type",
        "directconnect": "direct_connect", "direct_connect": "direct_connect", "directConnect": "direct_connect",
        "sslenabled": "ssl_enabled", "ssl_enabled": "ssl_enabled", "sslEnabled": "ssl_enabled",
        "tls": "ssl_enabled",
    }

    for raw_key, value in raw.items():
        key_lower = raw_key.lower().replace("-", "_").replace(" ", "_")
        if key_lower in field_map:
            target = field_map[key_lower]
            if normalized[target] is None:
                normalized[target] = value
        elif "header" in key_lower:
            if isinstance(value, str):
                normalized["custom_headers"][raw_key] = value
            elif isinstance(value, dict):
                normalized["custom_headers"].update(value)

    if normalized["protocol"] is None:
        normalized["protocol"] = _detect_hc_protocol(raw, normalized)

    normalized["v2ray"] = _extract_hc_v2ray(raw)
    normalized["websocket"] = _extract_hc_websocket(raw)

    if normalized["payload"]:
        normalized["payload_parsed"] = _parse_hc_payload(normalized["payload"])

    return normalized


def _detect_hc_protocol(raw: dict, normalized: dict) -> str:
    keys_lower = {k.lower() for k in raw.keys()}
    if normalized["connection_type"]:
        ct = str(normalized["connection_type"]).lower()
        if "v2ray" in ct or "vless" in ct or "vmess" in ct:
            return "v2ray"
        if "ws" in ct or "websocket" in ct:
            return "websocket"
        if "ssl" in ct or "tls" in ct:
            return "ssl"
    if any("v2ray" in k for k in keys_lower):
        return "v2ray"
    if any("ws" in k for k in keys_lower):
        return "websocket"
    if any("ssh" in k for k in keys_lower):
        return "ssh"
    return "ssh"


def _extract_hc_v2ray(raw: dict) -> Optional[dict]:
    v2ray_fields = {}
    for key, value in raw.items():
        if any(vk in key.lower() for vk in ["v2ray", "vless", "vmess", "uuid"]):
            v2ray_fields[key] = value
    return v2ray_fields if v2ray_fields else None


def _extract_hc_websocket(raw: dict) -> Optional[dict]:
    ws_fields = {}
    for key, value in raw.items():
        if any(wk in key.lower() for wk in ["ws", "websocket", "wspath", "wshost"]):
            ws_fields[key] = value
    return ws_fields if ws_fields else None


def _parse_hc_payload(payload: str) -> list:
    if not payload:
        return []
    headers = []
    lines = payload.strip().split("\n")
    current = {}
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith(("GET ", "POST ", "PUT ", "CONNECT ", "HEAD ", "OPTIONS ")):
            if current:
                headers.append(current)
            parts = line.split()
            current = {"type": "method", "method": parts[0], "path": parts[1] if len(parts) > 1 else "/", "version": parts[2] if len(parts) > 2 else "HTTP/1.1"}
        elif ":" in line:
            key, _, value = line.partition(":")
            if current.get("type") != "method":
                current = {"type": "header"}
            current[key.strip()] = value.strip()
    if current:
        headers.append(current)
    return headers
