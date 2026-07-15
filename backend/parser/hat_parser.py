"""
HAT (HA Tunnel Plus) config parser.

⚠️ CRITICAL FINDING FROM RESEARCH:
HA Tunnel Plus .hat files are ENCRYPTED text files, not plain JSON.

From the Google Play Store description:
"The configuration file has the .hat extension, it is an encrypted text file
containing all the information that was defined before exporting it."

When importing, the app decrypts the file internally. The encryption scheme
is proprietary to the HA Tunnel Plus app by ArtOfTech.

This parser attempts:
1. Try common decryption patterns (base64, AES with known keys)
2. Try plain JSON / base64 (older versions may have used simpler encoding)
3. Report encrypted status if decryption fails

HA Tunnel Plus supports: SSH, WebSocket, V2Ray (VMess/VLess), SSL/TLS
"""

import zipfile
import json
import base64
from pathlib import Path
from typing import Optional


def parse_hat(filepath: str) -> dict:
    """
    Parse an .hat config file and return normalized config data.
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
        "custom_sni": None,
        "direct_connect": None,
        "_encryption_info": None,
        "raw_data": None,
    }

    # Step 1: Try plain JSON
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            normalized["_encryption_info"] = "plain_json"
            return _normalize_hat(data, normalized)
    except Exception:
        pass

    # Step 2: Try base64 → JSON
    try:
        decoded = base64.b64decode(raw)
        data = json.loads(decoded)
        if isinstance(data, dict):
            normalized["_encryption_info"] = "base64_json"
            return _normalize_hat(data, normalized)
    except Exception:
        pass

    # Step 3: Try ZIP archive
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
            return _normalize_hat(raw_data, normalized)

    # Step 4: Try UTF-8 text parse for semi-readable configs
    try:
        text = raw.decode("utf-8", errors="ignore")
        # Some versions export as key=value pairs
        if "=" in text and "\n" in text:
            kv_data = {}
            for line in text.strip().split("\n"):
                if "=" in line:
                    k, _, v = line.partition("=")
                    kv_data[k.strip()] = v.strip()
            if len(kv_data) >= 3:
                normalized["_encryption_info"] = "key_value_text"
                return _normalize_hat(kv_data, normalized)
    except Exception:
        pass

    # Step 5: Cannot decrypt
    normalized["_encryption_info"] = "encrypted_unable_to_decrypt"
    normalized["_warning"] = (
        "HA Tunnel Plus .hat files are encrypted. "
        "The app description confirms: 'it is an encrypted text file containing "
        "all the information that was defined before exporting it.' "
        "Try PANCHO7532/HCDecryptor on GitLab which may support HAT files, "
        "or extract config details from within the app directly."
    )
    normalized["raw_data"] = {
        "file_size": len(raw),
        "hex_preview": raw[:64].hex(),
        "detected_header": raw[:10].hex() if len(raw) >= 10 else raw.hex(),
    }

    return normalized


def _normalize_hat(raw: dict, normalized: dict) -> dict:
    """Normalize raw HA Tunnel JSON data into consistent format."""
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
        "payload": "payload", "httppayload": "payload", "httpPayload": "payload",
        "custompayload": "payload", "custom_payload": "payload",
        "proxyip": "proxy_host", "proxy_ip": "proxy_host", "proxyIp": "proxy_host",
        "proxyhost": "proxy_host", "proxy_host": "proxy_host",
        "proxyport": "proxy_port", "proxy_port": "proxy_port", "proxyPort": "proxy_port",
        "dns": "dns", "dnsserver": "dns", "dns_server": "dns",
        "remotedns": "remote_dns", "remote_dns": "remote_dns", "remoteDns": "remote_dns",
        "sni": "sni", "servername": "sni", "server_name": "sni",
        "customsni": "custom_sni", "custom_sni": "custom_sni", "customSni": "custom_sni",
        "connectiontype": "connection_type", "connectionType": "connection_type",
        "connection_type": "connection_type",
        "tunneltype": "tunnel_type", "tunnelType": "tunnel_type", "tunnel_type": "tunnel_type",
        "directconnect": "direct_connect", "direct_connect": "direct_connect",
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
        keys_lower = {k.lower() for k in raw.keys()}
        if any("v2ray" in k for k in keys_lower):
            normalized["protocol"] = "v2ray"
        elif any("ws" in k for k in keys_lower):
            normalized["protocol"] = "websocket"
        elif any("ssh" in k for k in keys_lower):
            normalized["protocol"] = "ssh"
        else:
            normalized["protocol"] = "ssh"

    if normalized["payload"]:
        normalized["payload_parsed"] = _parse_hat_payload(normalized["payload"])

    return normalized


def _parse_hat_payload(payload: str) -> list:
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
