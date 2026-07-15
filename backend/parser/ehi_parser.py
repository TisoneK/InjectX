"""
EHI (HTTP Injector) config parser.

EHI files are ZIP archives containing JSON config files.
However, newer versions may use obfuscation/encryption.

From research:
- The .ehi file is a ZIP archive renamed to .ehi
- Inside the ZIP there's typically an HttpInjector.json or similar
- Some EHI files are "locked" (obfuscated) to prevent viewing payloads
- Unlocking methods exist for both rooted and non-rooted devices
- The ZIP may contain: payload, SSH credentials, proxy settings, DNS
- Stack Overflow confirms EHI files are "not readable" as plain text
  (https://stackoverflow.com/questions/49951966)

Pancho7532's HCDecryptor also supports HTTP Injector decryption.
"""

import zipfile
import json
import base64
from pathlib import Path
from typing import Optional


def parse_ehi(filepath: str) -> dict:
    """
    Parse an .ehi config file and return normalized config data.

    Returns:
        dict with normalized fields
    """
    path = Path(filepath)

    if not zipfile.is_zipfile(path):
        # Might be raw JSON or base64 — try those (rare)
        return _parse_ehi_non_zip(filepath)

    raw_data = {}
    is_obfuscated = False

    with zipfile.ZipFile(path, "r") as zf:
        for name in zf.namelist():
            if name.endswith(".json"):
                try:
                    content = zf.read(name).decode("utf-8")
                    data = json.loads(content)
                    if isinstance(data, dict):
                        raw_data.update(data)
                except json.JSONDecodeError:
                    # JSON failed — might be obfuscated
                    is_obfuscated = True
                    raw_bytes = zf.read(name)
                    # Try base64 decode
                    try:
                        decoded = base64.b64decode(raw_bytes)
                        data = json.loads(decoded)
                        if isinstance(data, dict):
                            raw_data.update(data)
                            is_obfuscated = False
                    except Exception:
                        raw_data["_obfuscated_content"] = raw_bytes.hex()[:200]
                except Exception:
                    continue
            elif name.endswith((".txt", ".cfg", ".payload")):
                try:
                    content = zf.read(name).decode("utf-8")
                    try:
                        data = json.loads(content)
                        if isinstance(data, dict):
                            raw_data.update(data)
                    except Exception:
                        raw_data[name] = content
                except Exception:
                    continue

    if not raw_data:
        raise ValueError("No readable JSON config found inside EHI archive. File may be locked/obfuscated.")

    normalized = _normalize_ehi(raw_data)
    if is_obfuscated:
        normalized["_warning"] = "EHI file appears obfuscated/locked. Some fields may be missing."
    return normalized


def _parse_ehi_non_zip(filepath: str) -> dict:
    """Handle EHI configs that aren't ZIP (rare)."""
    path = Path(filepath)
    raw = path.read_bytes()

    # Try plain JSON
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return _normalize_ehi(data)
    except Exception:
        pass

    # Try base64 → JSON
    try:
        decoded = base64.b64decode(raw)
        data = json.loads(decoded)
        if isinstance(data, dict):
            return _normalize_ehi(data)
    except Exception:
        pass

    raise ValueError("Cannot parse EHI file — not a ZIP, JSON, or base64-encoded JSON. May be encrypted.")


def _normalize_ehi(raw: dict) -> dict:
    """Normalize raw EHI JSON data into a consistent format."""
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
        "ssh_key": None,
        "proxy_host": None,
        "proxy_port": None,
        "dns": None,
        "remote_dns": None,
        "custom_headers": {},
        "v2ray": None,
        "websocket": None,
        "raw_data": raw,
    }

    field_map = {
        "host": "host", "server": "host",
        "sshserver": "ssh_server", "ssh_server": "ssh_server", "sshServer": "ssh_server",
        "serveraddress": "host", "serverAddress": "host",
        "port": "port",
        "sshport": "ssh_port", "ssh_port": "ssh_port", "sshPort": "ssh_port",
        "serverport": "port", "serverPort": "port",
        "sshuser": "ssh_user", "ssh_user": "ssh_user", "sshUser": "ssh_user",
        "username": "ssh_user", "user": "ssh_user",
        "sshpass": "ssh_pass", "ssh_pass": "ssh_pass", "sshPass": "ssh_pass",
        "password": "ssh_pass", "pass": "ssh_pass",
        "sshkey": "ssh_key", "ssh_key": "ssh_key", "privatekey": "ssh_key",
        "payload": "payload", "httppayload": "payload", "httpPayload": "payload",
        "custompayload": "payload",
        "proxyip": "proxy_host", "proxy_ip": "proxy_host", "proxyIp": "proxy_host",
        "proxyhost": "proxy_host", "proxy_host": "proxy_host",
        "proxyport": "proxy_port", "proxy_port": "proxy_port", "proxyPort": "proxy_port",
        "dns": "dns", "dns_server": "dns", "dnsserver": "dns",
        "remotedns": "remote_dns", "remote_dns": "remote_dns", "remoteDns": "remote_dns",
        "sni": "sni", "servername": "sni", "server_name": "sni",
        "protocol": "protocol", "connectiontype": "protocol", "connectionType": "protocol",
        "tunneltype": "protocol", "tunnelType": "protocol",
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
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and "name" in item and "value" in item:
                        normalized["custom_headers"][item["name"]] = item["value"]

    if normalized["protocol"] is None:
        normalized["protocol"] = _detect_protocol(raw)

    normalized["v2ray"] = _extract_v2ray(raw)
    normalized["websocket"] = _extract_websocket(raw)

    if normalized["payload"]:
        normalized["payload_parsed"] = _parse_payload(normalized["payload"])

    return normalized


def _detect_protocol(raw: dict) -> str:
    keys_lower = {k.lower() for k in raw.keys()}
    if any("v2ray" in k for k in keys_lower) or any("vless" in k for k in keys_lower):
        return "v2ray"
    if any("ws" in k for k in keys_lower) or "websocket" in keys_lower:
        return "websocket"
    if any("ssl" in k for k in keys_lower) or "tls" in keys_lower:
        return "ssl"
    if any("ssh" in k for k in keys_lower):
        return "ssh"
    return "ssh"


def _extract_v2ray(raw: dict) -> Optional[dict]:
    v2ray_fields = {}
    for key, value in raw.items():
        if any(vk in key.lower() for vk in ["v2ray", "vless", "vmess"]):
            v2ray_fields[key] = value
    return v2ray_fields if v2ray_fields else None


def _extract_websocket(raw: dict) -> Optional[dict]:
    ws_fields = {}
    for key, value in raw.items():
        if any(wk in key.lower() for wk in ["ws", "websocket"]):
            ws_fields[key] = value
    return ws_fields if ws_fields else None


def _parse_payload(payload: str) -> list:
    if not payload:
        return []
    headers = []
    lines = payload.strip().split("\n")
    current = {}
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith(("GET ", "POST ", "PUT ", "CONNECT ", "HEAD ", "OPTIONS ", "PATCH ")):
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
