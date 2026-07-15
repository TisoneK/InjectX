"""
NSH (SocksHTTP) config parser.

RESEARCH FINDINGS:
SocksHTTP uses .nsh config files which are ENCRYPTED.

SocksHTTP is a tunneling app that creates SSH/SOCKS tunnels
through HTTP proxies. The .nsh config files contain connection
settings but are encrypted with a proprietary scheme.

Pancho7532/HCDecryptor on GitLab supports SocksHTTP decryption:
https://gitlab.com/PANCHO7532/HCDecryptor

This parser attempts:
1. Try common decryption patterns (base64, JSON)
2. Report encrypted status if decryption fails
"""

import json
import base64
from pathlib import Path
from typing import Optional


def parse_nsh(filepath: str) -> dict:
    """
    Parse a .nsh config file and return normalized config data.
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
        "_encryption_info": None,
        "raw_data": None,
    }

    # Step 1: Try plain JSON
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            normalized["_encryption_info"] = "plain_json"
            return _normalize_nsh(data, normalized)
    except Exception:
        pass

    # Step 2: Try base64 -> JSON
    try:
        decoded = base64.b64decode(raw)
        data = json.loads(decoded)
        if isinstance(data, dict):
            normalized["_encryption_info"] = "base64_json"
            return _normalize_nsh(data, normalized)
    except Exception:
        pass

    # Step 3: Cannot decrypt
    normalized["_encryption_info"] = "encrypted_unable_to_decrypt"
    normalized["_warning"] = (
        "SocksHTTP .nsh files are encrypted. "
        "Try PANCHO7532/HCDecryptor on GitLab which supports SocksHTTP decryption, "
        "or extract config details from within the SocksHTTP app."
    )
    normalized["raw_data"] = {
        "file_size": len(raw),
        "hex_preview": raw[:64].hex(),
        "detected_header": raw[:10].hex() if len(raw) >= 10 else raw.hex(),
    }

    return normalized


def _normalize_nsh(raw: dict, normalized: dict) -> dict:
    """Normalize raw SocksHTTP data into consistent format."""
    field_map = {
        "host": "host", "server": "host",
        "port": "port", "serverport": "port", "server_port": "port",
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
        keys_lower = {k.lower() for k in raw.keys()}
        if any("ssh" in k for k in keys_lower):
            normalized["protocol"] = "ssh"
        else:
            normalized["protocol"] = "socks"

    return normalized
