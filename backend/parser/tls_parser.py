"""
TLS (TLS Tunnel VPN) config parser.

⚠️ RESEARCH FINDINGS:
TLS Tunnel uses .tls config files which are ENCRYPTED.

From the app's official documentation:
"The configuration file, having the .tls extension, contains all necessary
information except for DNS and connection options like reconnection and internal IP."

TLS Tunnel uses a proprietary protocol called TLSVPN with TLS 1.3 encryption.
Config files contain: server, port, payload/SNI, and tunnel settings.

The encryption scheme is specific to the TLS Tunnel app.
"""

import json
import base64
from pathlib import Path
from typing import Optional


def parse_tls(filepath: str) -> dict:
    """
    Parse a .tls config file and return normalized config data.
    """
    path = Path(filepath)
    raw = path.read_bytes()

    normalized = {
        "host": None,
        "port": None,
        "payload": None,
        "protocol": "tls_vpn",
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
        "tls_version": None,
        "internal_ip": None,
        "reconnect": None,
        "_encryption_info": None,
        "raw_data": None,
    }

    # Step 1: Try plain JSON
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            normalized["_encryption_info"] = "plain_json"
            return _normalize_tls(data, normalized)
    except Exception:
        pass

    # Step 2: Try base64 → JSON
    try:
        decoded = base64.b64decode(raw)
        data = json.loads(decoded)
        if isinstance(data, dict):
            normalized["_encryption_info"] = "base64_json"
            return _normalize_tls(data, normalized)
    except Exception:
        pass

    # Step 3: Try key=value text format
    try:
        text = raw.decode("utf-8", errors="ignore")
        if "=" in text and "\n" in text:
            kv_data = {}
            for line in text.strip().split("\n"):
                if "=" in line:
                    k, _, v = line.partition("=")
                    kv_data[k.strip()] = v.strip()
            if len(kv_data) >= 3:
                normalized["_encryption_info"] = "key_value_text"
                return _normalize_tls(kv_data, normalized)
    except Exception:
        pass

    # Step 4: Cannot decrypt
    normalized["_encryption_info"] = "encrypted_unable_to_decrypt"
    normalized["_warning"] = (
        "TLS Tunnel .tls config files are encrypted. "
        "They contain all connection information except DNS and reconnect settings. "
        "Try extracting config details from within the TLS Tunnel app directly."
    )
    normalized["raw_data"] = {
        "file_size": len(raw),
        "hex_preview": raw[:64].hex(),
        "detected_header": raw[:10].hex() if len(raw) >= 10 else raw.hex(),
    }

    return normalized


def _normalize_tls(raw: dict, normalized: dict) -> dict:
    """Normalize raw TLS Tunnel data into consistent format."""
    field_map = {
        "host": "host", "server": "host",
        "port": "port", "serverport": "port", "server_port": "port",
        "payload": "payload", "sni": "sni", "servername": "sni",
        "sshserver": "ssh_server", "ssh_server": "ssh_server",
        "sshport": "ssh_port", "ssh_port": "ssh_port",
        "sshuser": "ssh_user", "ssh_user": "ssh_user",
        "username": "ssh_user",
        "sshpass": "ssh_pass", "ssh_pass": "ssh_pass", "password": "ssh_pass",
        "proxyip": "proxy_host", "proxy_host": "proxy_host",
        "proxyport": "proxy_port", "proxy_port": "proxy_port",
        "dns": "dns", "dnsserver": "dns",
        "remotedns": "remote_dns", "remote_dns": "remote_dns",
        "tlsversion": "tls_version", "tls_version": "tls_version",
        "internalip": "internal_ip", "internal_ip": "internal_ip",
        "internal_ip": "internal_ip",
        "reconnect": "reconnect",
    }

    for raw_key, value in raw.items():
        key_lower = raw_key.lower().replace("-", "_").replace(" ", "_")
        if key_lower in field_map:
            target = field_map[key_lower]
            if normalized[target] is None:
                normalized[target] = value

    if normalized["payload"]:
        normalized["payload_parsed"] = _parse_tls_payload(normalized["payload"])

    return normalized


def _parse_tls_payload(payload: str) -> list:
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
