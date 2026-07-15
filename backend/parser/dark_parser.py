"""
DARK (DARK TUNNEL VPN) config parser.

⚠️ RESEARCH FINDINGS:
There are TWO different "Dark Tunnel" apps on the Play Store:

1. DarkTunnel (net.darktunnel.app) — by the DarkTunnel team
   - Supports: SSH, SSH through DNSTT (SlowDNS), VMess, VLess, Trojan, Shadowsocks
   - Configs are created inside the app, limited export capability
   - No standard file extension for exported configs

2. DARK TUNNEL VPN (com.victo.dt) — by a different developer
   - Supports: SSH, Proxy, SSL Tunnel, DNS Tunnel, Xray, Hysteria
   - Uses .dark config files for import/export
   - Config files are encrypted
   - Community creates/shares .dark files on Facebook groups and Telegram

There are YouTube tutorials on "decrypting Dark Tunnel config" files,
suggesting they use custom encryption similar to HC files.

PANCHO7532/HCDecryptor on GitLab may also support .dark files.
"""

import zipfile
import json
import base64
from pathlib import Path
from typing import Optional


def parse_dark(filepath: str) -> dict:
    """
    Parse a .dark/.drak config file and return normalized config data.
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
        "tunnel_mode": None,
        "inject_type": None,
        "payload_generator": None,
        "handshake": None,
        "v2ray": None,
        "websocket": None,
        "hysteria": None,
        "xray": None,
        "ssl_enabled": None,
        "_encryption_info": None,
        "raw_data": None,
    }

    # Step 1: Try plain JSON
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            normalized["_encryption_info"] = "plain_json"
            return _normalize_dark(data, normalized)
    except Exception:
        pass

    # Step 2: Try base64 → JSON
    try:
        decoded = base64.b64decode(raw)
        data = json.loads(decoded)
        if isinstance(data, dict):
            normalized["_encryption_info"] = "base64_json"
            return _normalize_dark(data, normalized)
    except Exception:
        pass

    # Step 3: Try base64 with common prefixes
    for prefix in [b"dark://", b"DARK:", b"dt://", b"DARKTUNNEL:"]:
        if raw.startswith(prefix):
            try:
                decoded = base64.b64decode(raw[len(prefix):])
                data = json.loads(decoded)
                if isinstance(data, dict):
                    normalized["_encryption_info"] = f"prefixed_base64 ({prefix.decode()})"
                    return _normalize_dark(data, normalized)
            except Exception:
                continue

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
            return _normalize_dark(raw_data, normalized)

    # Step 5: Cannot decrypt
    normalized["_encryption_info"] = "encrypted_unable_to_decrypt"
    normalized["_warning"] = (
        "DARK TUNNEL VPN .dark config files are encrypted. "
        "YouTube tutorials show methods to decrypt them. "
        "Try PANCHO7532/HCDecryptor on GitLab which supports multiple tunnel app formats, "
        "or extract config details from within the DARK TUNNEL VPN app."
    )
    normalized["raw_data"] = {
        "file_size": len(raw),
        "hex_preview": raw[:64].hex(),
        "detected_header": raw[:10].hex() if len(raw) >= 10 else raw.hex(),
    }

    # Check for known headers
    if raw[:5] == b"HCUST":
        normalized["raw_data"]["format"] = "HCUST-based encryption (same as HTTP Custom)"
    elif raw[:3] == b"DT\x00":
        normalized["raw_data"]["format"] = "DarkTunnel native format"
    else:
        normalized["raw_data"]["format"] = "unknown encryption"

    return normalized


def _normalize_dark(raw: dict, normalized: dict) -> dict:
    """Normalize raw DARK TUNNEL VPN JSON data into consistent format."""
    field_map = {
        "host": "host", "server": "host",
        "remotehost": "host", "remote_host": "host",
        "bughost": "bug_host", "bug_host": "bug_host", "bugHost": "bug_host",
        "targethost": "host",
        "port": "port", "remoteport": "port", "remote_port": "port",
        "sshserver": "ssh_server", "ssh_server": "ssh_server", "sshServer": "ssh_server",
        "sshhost": "ssh_server", "ssh_host": "ssh_server",
        "sshport": "ssh_port", "ssh_port": "ssh_port", "sshPort": "ssh_port",
        "sshuser": "ssh_user", "ssh_user": "ssh_user", "sshUser": "ssh_user",
        "username": "ssh_user",
        "sshpass": "ssh_pass", "ssh_pass": "ssh_pass", "sshPass": "ssh_pass",
        "password": "ssh_pass",
        "sshkey": "ssh_key", "ssh_key": "ssh_key",
        "payload": "payload", "httppayload": "payload", "httpPayload": "payload",
        "injectpayload": "payload",
        "proxyip": "proxy_host", "proxy_ip": "proxy_host", "proxyIp": "proxy_host",
        "proxyhost": "proxy_host", "proxy_host": "proxy_host",
        "proxyport": "proxy_port", "proxy_port": "proxy_port", "proxyPort": "proxy_port",
        "dns": "dns", "dnsserver": "dns",
        "remotedns": "remote_dns", "remote_dns": "remote_dns", "remoteDns": "remote_dns",
        "sni": "sni", "servername": "sni",
        "tunnelmode": "tunnel_mode", "tunnel_mode": "tunnel_mode", "tunnelMode": "tunnel_mode",
        "mode": "tunnel_mode",
        "injecttype": "inject_type", "inject_type": "inject_type", "injectType": "inject_type",
        "payloadgenerator": "payload_generator", "payload_generator": "payload_generator",
        "payloadGenerator": "payload_generator",
        "handshake": "handshake",
        "ssl": "ssl_enabled", "sslenabled": "ssl_enabled", "tls": "ssl_enabled",
        # Xray / Hysteria fields
        "xrayconfig": "xray", "xray_config": "xray",
        "hysteriaconfig": "hysteria", "hysteria_config": "hysteria",
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
        if any(k in keys_lower for k in ["hysteriaconfig", "hysteria_config", "hysteria"]):
            normalized["protocol"] = "hysteria"
        elif any("v2ray" in k for k in keys_lower) or any("vless" in k for k in keys_lower) or any("xray" in k for k in keys_lower):
            normalized["protocol"] = "xray"
        elif any("ws" in k for k in keys_lower):
            normalized["protocol"] = "websocket"
        elif any("ssh" in k for k in keys_lower):
            normalized["protocol"] = "ssh"
        else:
            normalized["protocol"] = "ssh"

    if normalized["payload"]:
        normalized["payload_parsed"] = _parse_dark_payload(normalized["payload"])

    return normalized


def _parse_dark_payload(payload: str) -> list:
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
