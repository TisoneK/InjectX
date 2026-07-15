"""
NPV (NapsternetV / NPV Tunnel) config parser.

⚠️ RESEARCH FINDINGS:
NapsternetV uses .npv4 and .inpv config file extensions.

From Stack Overflow (https://stackoverflow.com/questions/78740504):
"I dragged a .npv4 file into notepad but it was not a clear text and readable.
So I don't know how it's generated."

NPV4 files are ENCRYPTED, not plain text or JSON.

NapsternetV supports: V2Ray (VMess/VLess), SSH, SlowDNS
NPV Tunnel (a fork/rebrand) uses the same format.

PANCHO7532/HCDecryptor on GitLab supports NapsternetV decryption:
https://gitlab.com/PANCHO7532/HCDecryptor

Supported extensions:
- .npv4 — NapsternetV V4 config
- .inpv — NapsternetV config (alternative extension)
- .npv  — NPV Tunnel config
"""

import json
import base64
from pathlib import Path
from typing import Optional


def parse_npv(filepath: str) -> dict:
    """
    Parse a .npv4/.inpv config file and return normalized config data.
    """
    path = Path(filepath)
    raw = path.read_bytes()

    normalized = {
        "host": None,
        "port": None,
        "payload": None,
        "protocol": None,
        "sni": None,
        "ssh_server": None,
        "ssh_port": None,
        "ssh_user": None,
        "ssh_pass": None,
        "proxy_host": None,
        "proxy_port": None,
        "dns": None,
        "remote_dns": None,
        "custom_headers": {},
        "v2ray_config": None,
        "vless_config": None,
        "vmess_config": None,
        "ssh_config": None,
        "slowdns_config": None,
        "_encryption_info": None,
        "raw_data": None,
    }

    # Determine sub-format from extension
    ext = path.suffix.lower()
    if ext == ".npv4":
        normalized["_sub_format"] = "npv4"
    elif ext == ".inpv":
        normalized["_sub_format"] = "inpv"
    elif ext == ".npv":
        normalized["_sub_format"] = "npv"
    else:
        normalized["_sub_format"] = "unknown"

    # Step 1: Try plain JSON
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            normalized["_encryption_info"] = "plain_json"
            return _normalize_npv(data, normalized)
    except Exception:
        pass

    # Step 2: Try base64 → JSON
    try:
        decoded = base64.b64decode(raw)
        data = json.loads(decoded)
        if isinstance(data, dict):
            normalized["_encryption_info"] = "base64_json"
            return _normalize_npv(data, normalized)
    except Exception:
        pass

    # Step 3: Try base64 with NPV prefix
    for prefix in [b"NPV4:", b"INPV:", b"NPV:", b"napsternetv://"]:
        if raw.startswith(prefix):
            try:
                decoded = base64.b64decode(raw[len(prefix):])
                data = json.loads(decoded)
                if isinstance(data, dict):
                    normalized["_encryption_info"] = f"prefixed_base64 ({prefix.decode()})"
                    return _normalize_npv(data, normalized)
            except Exception:
                continue

    # Step 4: Try VMess/VLess base64 config format
    # VMess links start with vmess:// and contain base64-encoded JSON
    try:
        text = raw.decode("utf-8", errors="ignore").strip()
        if text.startswith("vmess://"):
            vmess_data = _parse_vmess_link(text)
            if vmess_data:
                normalized["_encryption_info"] = "vmess_link"
                return _normalize_npv(vmess_data, normalized)
        elif text.startswith("vless://"):
            vless_data = _parse_vless_link(text)
            if vless_data:
                normalized["_encryption_info"] = "vless_link"
                return _normalize_npv(vless_data, normalized)
    except Exception:
        pass

    # Step 5: Cannot decrypt
    normalized["_encryption_info"] = "encrypted_unable_to_decrypt"
    normalized["_warning"] = (
        "NapsternetV/NPV Tunnel .npv4/.inpv files are encrypted, not plain text. "
        "Try PANCHO7532/HCDecryptor on GitLab which supports NapsternetV decryption, "
        "or extract config details from within the NapsternetV app."
    )
    normalized["raw_data"] = {
        "file_size": len(raw),
        "hex_preview": raw[:64].hex(),
        "detected_header": raw[:10].hex() if len(raw) >= 10 else raw.hex(),
    }

    return normalized


def _parse_vmess_link(link: str) -> Optional[dict]:
    """Parse a vmess:// link into a dict."""
    try:
        b64_part = link[len("vmess://"):]
        # VMess links use base64 without padding
        padding = 4 - len(b64_part) % 4
        if padding != 4:
            b64_part += "=" * padding
        decoded = base64.b64decode(b64_part)
        data = json.loads(decoded)
        return data
    except Exception:
        return None


def _parse_vless_link(link: str) -> Optional[dict]:
    """Parse a vless:// link into a dict."""
    try:
        # VLess links use a URL-like format: vless://uuid@host:port?params#name
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(link)
        params = parse_qs(parsed.query)

        data = {
            "uuid": parsed.username,
            "host": parsed.hostname,
            "port": parsed.port,
            "security": params.get("security", [None])[0],
            "type": params.get("type", [None])[0],
            "sni": params.get("sni", [None])[0],
            "path": params.get("path", [None])[0],
            "host_header": params.get("host", [None])[0],
            "name": parsed.fragment,
        }
        return {k: v for k, v in data.items() if v is not None}
    except Exception:
        return None


def _normalize_npv(raw: dict, normalized: dict) -> dict:
    """Normalize raw NapsternetV data into consistent format."""
    field_map = {
        "host": "host", "server": "host", "add": "host", "address": "host",
        "port": "port",
        "payload": "payload",
        "sni": "sni", "servername": "sni",
        "sshserver": "ssh_server", "ssh_server": "ssh_server",
        "sshport": "ssh_port", "ssh_port": "ssh_port",
        "sshuser": "ssh_user", "ssh_user": "ssh_user", "username": "ssh_user",
        "sshpass": "ssh_pass", "ssh_pass": "ssh_pass", "password": "ssh_pass",
        "proxyip": "proxy_host", "proxy_host": "proxy_host",
        "proxyport": "proxy_port", "proxy_port": "proxy_port",
        "dns": "dns", "dnsserver": "dns",
        "remotedns": "remote_dns", "remote_dns": "remote_dns",
        # V2Ray fields
        "v2rayconfig": "v2ray_config", "v2ray_config": "v2ray_config",
        "vlessconfig": "vless_config", "vless_config": "vless_config",
        "vmessconfig": "vmess_config", "vmess_config": "vmess_config",
        "sshconfig": "ssh_config", "ssh_config": "ssh_config",
        "slowdnsconfig": "slowdns_config", "slowdns_config": "slowdns_config",
        # VMess link fields
        "uuid": "v2ray_config", "id": "v2ray_config",
        "security": "protocol", "net": "protocol", "type": "protocol",
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

    # Detect protocol from V2Ray config presence
    if normalized["protocol"] is None:
        if normalized["vless_config"] is not None:
            normalized["protocol"] = "vless"
        elif normalized["vmess_config"] is not None:
            normalized["protocol"] = "vmess"
        elif normalized["v2ray_config"] is not None:
            normalized["protocol"] = "v2ray"
        elif normalized["ssh_config"] is not None or normalized["ssh_server"] is not None:
            normalized["protocol"] = "ssh"
        elif normalized["slowdns_config"] is not None:
            normalized["protocol"] = "slowdns"
        else:
            normalized["protocol"] = "v2ray"

    if normalized["payload"]:
        normalized["payload_parsed"] = _parse_npv_payload(normalized["payload"])

    return normalized


def _parse_npv_payload(payload: str) -> list:
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
