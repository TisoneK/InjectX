"""
InjectX — Parse Engine

Coordinates detection, decryption, and parsing into the versioned IR.
This replaces the old detect_and_read() with a proper pipeline:

  1. detect_with_features() → DetectResult
  2. router.dispatch() → DecryptedPayload
  3. normalize() → NormalizedConfig

Parsers NEVER call decryptors directly. The Scheme Router handles all crypto.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .detector import detect_format, detect_with_features
from ir.models import (
    NormalizedConfig,
    FormatEnum,
    ProtocolEnum,
    DecryptStatusEnum,
    SchemeEnum,
    DetectResult,
    DecryptedPayload,
)
from decrypt.router import get_router
from audit.trace import get_audit_log


def parse_config(filepath: str) -> NormalizedConfig:
    """
    Full pipeline: detect → decrypt → normalize.

    Returns a NormalizedConfig IR object (never a raw dict).
    """
    path = Path(filepath)

    # Step 1: Detect format with multi-feature classification
    detect_result = detect_with_features(filepath)

    # Step 2: Try decryption via scheme router (if applicable)
    router = get_router()
    raw = path.read_bytes()
    decrypt_payload = router.dispatch(
        format=detect_result.format,
        raw=raw,
        filepath=str(path),
        filename=path.name,
    )

    # Record audit trace
    audit = get_audit_log()
    audit.record(decrypt_payload.trace)

    # Step 3: Normalize based on format + decrypted data
    normalized = _normalize(
        detect_result=detect_result,
        decrypt_payload=decrypt_payload,
        raw=raw,
    )

    return normalized


def _normalize(
    detect_result: DetectResult,
    decrypt_payload: DecryptedPayload,
    raw: bytes,
) -> NormalizedConfig:
    """Route to format-specific normalizer with IR output."""

    fmt = detect_result.format
    data = decrypt_payload.json_data

    # If decryption succeeded, normalize the decrypted data
    if data is not None:
        normalized = _normalize_by_format(fmt, data)
    else:
        # No decrypted data — produce minimal IR with metadata
        normalized = NormalizedConfig(
            filepath=detect_result.filepath,
            filename=detect_result.filename,
            format=fmt,
            is_encrypted=detect_result.is_encrypted,
            decryption_status=decrypt_payload.status,
            scheme_used=decrypt_payload.scheme,
        )

        # For EHI (ZIP), try extracting JSON directly (non-encrypted)
        if fmt == FormatEnum.EHI:
            normalized = _normalize_ehi_unencrypted(detect_result.filepath, raw)
            normalized.decryption_status = DecryptStatusEnum.NOT_ENCRYPTED

        # For DARK — no decryptor available
        if fmt == FormatEnum.DARK:
            normalized.warnings.append(
                "DARK TUNNEL VPN .dark files use proprietary encryption. "
                "No public decryptor exists. Showing file metadata only."
            )

        # For unknown encrypted — show hex preview
        if fmt == FormatEnum.ENCRYPTED_UNKNOWN:
            normalized.warnings.append(
                "File appears encrypted but format could not be determined."
            )

    # Attach common metadata
    normalized.is_encrypted = detect_result.is_encrypted
    normalized.decryption_status = decrypt_payload.status
    normalized.scheme_used = decrypt_payload.scheme
    normalized.decrypt_trace = decrypt_payload.trace

    # Attach raw data for debugging (only when decryption failed)
    if decrypt_payload.status in (DecryptStatusEnum.FAILED, DecryptStatusEnum.NO_DECRYPTOR):
        normalized.raw_data = {
            "file_size": len(raw),
            "hex_preview": raw[:64].hex(),
            "features": detect_result.features.dict(),
        }

    return normalized


def _normalize_by_format(fmt: FormatEnum, data: dict) -> NormalizedConfig:
    """Route to format-specific normalizer."""

    if fmt == FormatEnum.EHI:
        return _normalize_ehi(data)
    elif fmt == FormatEnum.HC:
        return _normalize_hc(data)
    elif fmt == FormatEnum.HAT:
        return _normalize_hat(data)
    elif fmt == FormatEnum.TLS:
        return _normalize_tls(data)
    elif fmt == FormatEnum.NPV:
        return _normalize_npv(data)
    elif fmt == FormatEnum.NSH:
        return _normalize_nsh(data)
    elif fmt == FormatEnum.VHD:
        return _normalize_vhd(data)
    else:
        # Generic fallback
        return NormalizedConfig(
            filepath="",
            filename="",
            format=fmt,
            raw_data=data,
        )


# ── Field Mapping ─────────────────────────────────────────────────────────────

_UNIVERSAL_FIELD_MAP: dict[str, str] = {
    # Host/Server
    "host": "host", "server": "host", "serveraddress": "host",
    "server_address": "host", "add": "host", "address": "host",
    "remotehost": "host", "targethost": "host",
    "sshserver": "ssh_server", "ssh_server": "ssh_server",
    "sshhost": "ssh_host", "ssh_host": "ssh_server",
    # Port
    "port": "port", "serverport": "port", "server_port": "port",
    "sshport": "ssh_port", "ssh_port": "ssh_port",
    "remoteport": "port", "remote_port": "port",
    # SSH Auth
    "sshuser": "ssh_user", "ssh_user": "ssh_user", "username": "ssh_user",
    "user": "ssh_user", "login": "ssh_user", "sshusername": "ssh_user",
    "sshpass": "ssh_pass", "ssh_pass": "ssh_pass", "password": "ssh_pass",
    "sshpassword": "ssh_pass", "sshkey": "ssh_key", "privatekey": "ssh_key",
    "ssl_file": "ssh_key",
    # Proxy
    "proxyip": "proxy_host", "proxy_ip": "proxy_host", "proxyhost": "proxy_host",
    "proxy_host": "proxy_host", "proxyaddress": "proxy_host",
    "proxyremoto": "proxy_host", "proxyurl": "proxy_host",
    "proxyport": "proxy_port", "proxy_port": "proxy_port",
    "proxyremotoporta": "proxy_port",
    # Payload
    "payload": "payload", "httppayload": "payload", "custompayload": "payload",
    "injectpayload": "payload", "custom_payload": "payload",
    # SNI/Bug Host
    "sni": "sni", "servername": "sni", "server_name": "sni",
    "snivalue": "sni", "snihostname": "sni", "hostsnissl": "sni",
    "customsni": "sni", "adv_ssl_spoofhost": "sni",
    "bughost": "bug_host", "bug_host": "bug_host",
    "customhost": "bug_host", "custom_host": "bug_host",
    # DNS
    "dns": "dns", "dnsserver": "dns", "dns_server": "dns",
    "dnsresolver": "dns", "primarydns": "dns",
    "remotedns": "remote_dns", "remote_dns": "remote_dns",
    "dnsresolversecondary": "remote_dns", "secondarydns": "remote_dns",
    # Connection type
    "connectiontype": "connection_type", "tunneltype": "tunnel_type",
    "connection_mode": "connection_type",
    "tunnelmode": "tunnel_mode", "injecttype": "inject_type",
    "tunnel_type": "tunnel_type",
    # SSL
    "ssl": "ssl_enabled", "sslenabled": "ssl_enabled", "tls": "ssl_enabled",
}


def _apply_field_map(raw: dict, field_map: dict[str, str] | None = None) -> dict:
    """Apply universal field mapping to normalize key names."""
    mapping = field_map or _UNIVERSAL_FIELD_MAP
    result: dict[str, any] = {}
    custom_headers: dict[str, any] = {}

    for raw_key, value in raw.items():
        key_lower = raw_key.lower().replace("-", "_").replace(" ", "_")
        if key_lower in mapping:
            target = mapping[key_lower]
            if target not in result or result[target] is None:
                result[target] = value
        elif "header" in key_lower:
            if isinstance(value, str):
                custom_headers[raw_key] = value
            elif isinstance(value, dict):
                custom_headers.update(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and "name" in item and "value" in item:
                        custom_headers[item["name"]] = item["value"]

    if custom_headers:
        result["custom_headers"] = custom_headers

    return result


def _detect_protocol(data: dict) -> ProtocolEnum:
    """Detect protocol from field names."""
    keys_lower = {k.lower() for k in data.keys()}

    if any("v2ray" in k for k in keys_lower) or any("vless" in k for k in keys_lower):
        return ProtocolEnum.V2RAY
    if any("vmess" in k for k in keys_lower):
        return ProtocolEnum.VMESS
    if any("hysteria" in k for k in keys_lower):
        return ProtocolEnum.HYSTERIA
    if any("xray" in k for k in keys_lower):
        return ProtocolEnum.XRAY
    if any("shadowsocks" in k for k in keys_lower):
        return ProtocolEnum.SHADOWSOCKS
    if any("trojan" in k for k in keys_lower):
        return ProtocolEnum.TROJAN
    if any("ws" in k for k in keys_lower) or "websocket" in keys_lower:
        return ProtocolEnum.WEBSOCKET
    if any("ssl" in k for k in keys_lower):
        return ProtocolEnum.SSL
    if any("ssh" in k for k in keys_lower):
        return ProtocolEnum.SSH
    return ProtocolEnum.SSH  # Default


def _parse_payload(payload: str) -> list[dict]:
    """Parse HTTP payload into structured header lines."""
    if not payload:
        return []
    headers = []
    current = {}
    for line in payload.strip().split("\n"):
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


# ── Format-Specific Normalizers ───────────────────────────────────────────────

def _normalize_ehi(data: dict) -> NormalizedConfig:
    """Normalize HTTP Injector config data."""
    mapped = _apply_field_map(data)
    config = NormalizedConfig(
        filepath="", filename="",
        format=FormatEnum.EHI,
        is_encrypted=True,
        decryption_status=DecryptStatusEnum.SUCCESS,
    )

    for key, value in mapped.items():
        if hasattr(config, key) and getattr(config, key) is None:
            setattr(config, key, value)

    config.protocol = _detect_protocol(data) if config.protocol is None else config.protocol

    # Extract V2Ray nested config
    v2ray_fields = {k: v for k, v in data.items() if any(vk in k.lower() for vk in ["v2ray", "vless", "vmess"])}
    if v2ray_fields:
        config.v2ray = v2ray_fields

    if config.payload:
        config.payload_parsed = _parse_payload(config.payload)

    return config


def _normalize_ehi_unencrypted(filepath: str, raw: bytes) -> NormalizedConfig:
    """Handle non-encrypted EHI (ZIP with plain JSON)."""
    import zipfile as zf

    config = NormalizedConfig(filepath=filepath, filename=Path(filepath).name, format=FormatEnum.EHI)

    if zf.is_zipfile(filepath):
        with zf.ZipFile(filepath, "r") as archive:
            for name in archive.namelist():
                if name.endswith(".json"):
                    try:
                        content = archive.read(name).decode("utf-8")
                        import json
                        data = json.loads(content)
                        if isinstance(data, dict):
                            mapped = _apply_field_map(data)
                            for key, value in mapped.items():
                                if hasattr(config, key) and getattr(config, key) is None:
                                    setattr(config, key, value)
                            config.protocol = _detect_protocol(data)
                            if config.payload:
                                config.payload_parsed = _parse_payload(config.payload)
                    except Exception:
                        continue

    return config


def _normalize_hc(data: dict) -> NormalizedConfig:
    """Normalize HTTP Custom config data (post-decryption)."""
    mapped = _apply_field_map(data)
    config = NormalizedConfig(filepath="", filename="", format=FormatEnum.HC, is_encrypted=True, decryption_status=DecryptStatusEnum.SUCCESS)

    # Handle delimited format ([splitConfig] or [pisahConk])
    if "_raw_delimited" in data:
        raw_text = data["_raw_delimited"]
        delimiter = data.get("_delimiter", "[splitConfig]")
        parts = raw_text.split(delimiter)
        parts = [p.strip() for p in parts if p.strip()]

        # Map delimited parts to fields (order matters)
        hc_field_order = [
            "payload", "proxy_host", "blocked_root", "lock_payload",
            "expire_date", "contains_notes", "note", "ssh_server",
            "mobile_data", "unlock_proxy", "openvpn_config", "vpn_addr",
            "sni", "connect_ssh", "udpgw_port", "lock_payload_2",
            "hwid_enabled", "hwid_value", "note2", "unlock_user_pass",
            "ssl_payload_mode", "password_protected", "password_value",
        ]
        for i, part in enumerate(parts):
            if i < len(hc_field_order):
                field = hc_field_order[i]
                if hasattr(config, field) and getattr(config, field) is None:
                    setattr(config, field, part)

        config.host = config.ssh_server  # HC uses sshAddr as primary host
        config.protocol = ProtocolEnum.SSH

    else:
        for key, value in mapped.items():
            if hasattr(config, key) and getattr(config, key) is None:
                setattr(config, key, value)
        config.protocol = _detect_protocol(data) if config.protocol is None else config.protocol

    if config.payload:
        config.payload_parsed = _parse_payload(config.payload)

    return config


def _normalize_hat(data: dict) -> NormalizedConfig:
    """Normalize HA Tunnel Plus config data (post-decryption)."""
    config = NormalizedConfig(filepath="", filename="", format=FormatEnum.HAT, is_encrypted=True, decryption_status=DecryptStatusEnum.SUCCESS)

    # Three known structures: "profile", "profilev4", "configuration"
    profile = data.get("profile") or data.get("profilev4") or data.get("configuration") or data
    mapped = _apply_field_map(profile if isinstance(profile, dict) else data)

    for key, value in mapped.items():
        if hasattr(config, key) and getattr(config, key) is None:
            setattr(config, key, value)

    config.protocol = _detect_protocol(profile if isinstance(profile, dict) else data)

    # Protection metadata
    protextras = data.get("protextras")
    if protextras:
        config.warnings.append(f"Config has protection: {list(protextras.keys())}")

    if config.payload:
        config.payload_parsed = _parse_payload(config.payload)

    return config


def _normalize_tls(data: dict) -> NormalizedConfig:
    """Normalize TLS Tunnel config data (post-decryption)."""
    config = NormalizedConfig(filepath="", filename="", format=FormatEnum.TLS, is_encrypted=True, decryption_status=DecryptStatusEnum.SUCCESS)

    # TLS Tunnel uses specific field names from the colon-separated format
    config.host = data.get("ssh_server")
    config.port = data.get("ssh_port")
    config.ssh_server = data.get("ssh_server")
    config.ssh_port = data.get("ssh_port")
    config.ssh_user = data.get("ssh_user")
    config.ssh_pass = data.get("ssh_pass")
    config.payload = data.get("payload")
    config.sni = data.get("sni")
    config.dns = data.get("dns_server")
    config.proxy_host = data.get("proxy_url")
    config.proxy_port = data.get("proxy_port")
    config.protocol = ProtocolEnum.TLS_VPN

    if data.get("connection_method"):
        config.connection_type = data["connection_method"]
    if data.get("dns_type"):
        config.tunnel_type = data["dns_type"]

    if config.payload:
        config.payload_parsed = _parse_payload(config.payload)

    return config


def _normalize_npv(data: dict) -> NormalizedConfig:
    """Normalize NapsternetV config data (post-decryption)."""
    config = NormalizedConfig(filepath="", filename="", format=FormatEnum.NPV, is_encrypted=True, decryption_status=DecryptStatusEnum.SUCCESS)

    # NPV uses a vmess object with configType
    vmess = data.get("vmess", {})
    if isinstance(vmess, dict):
        config.host = vmess.get("address")
        config.port = vmess.get("port")
        config.sni = vmess.get("sni")

        config_type = vmess.get("configType")
        if str(config_type) == "0":
            config.protocol = ProtocolEnum.VMESS
        elif str(config_type) == "3":
            config.protocol = ProtocolEnum.VLESS
        elif str(config_type) == "4":
            config.protocol = ProtocolEnum.TROJAN
        elif str(config_type) == "1":
            config.protocol = ProtocolEnum.SHADOWSOCKS
        elif str(config_type) == "2":
            config.protocol = ProtocolEnum.SOCKS

        # V2Ray fields
        v2ray = {}
        for field in ["id", "alterId", "network", "path", "requestHost", "security", "sni", "allowInsecure"]:
            if field in vmess:
                v2ray[field] = vmess[field]
        if v2ray:
            config.v2ray = v2ray

    # Security metadata
    security = data.get("security", {})
    if isinstance(security, dict):
        if security.get("blockRooted"):
            config.warnings.append("Config blocks rooted devices")
        if security.get("password"):
            config.warnings.append("Config is password-protected")

    return config


def _normalize_nsh(data: dict) -> NormalizedConfig:
    """Normalize SocksHTTP config data (post-decryption)."""
    mapped = _apply_field_map(data)
    config = NormalizedConfig(filepath="", filename="", format=FormatEnum.NSH, is_encrypted=True, decryption_status=DecryptStatusEnum.SUCCESS)

    for key, value in mapped.items():
        if hasattr(config, key) and getattr(config, key) is None:
            setattr(config, key, value)

    config.protocol = ProtocolEnum.SOCKS

    if config.payload:
        config.payload_parsed = _parse_payload(config.payload)

    return config


def _normalize_vhd(data: dict) -> NormalizedConfig:
    """Normalize VHD (V2Ray/NapsternetV) config data (post-decryption)."""
    config = NormalizedConfig(filepath="", filename="", format=FormatEnum.VHD, is_encrypted=True, decryption_status=DecryptStatusEnum.SUCCESS)

    # Extract from V2Ray/Xray outboundBean structure
    outbound = data.get("outboundBean", {})
    if isinstance(outbound, dict):
        settings = outbound.get("settings", {})
        stream = outbound.get("streamSettings", {})

        if isinstance(settings, dict):
            vnext = settings.get("vnext", [])
            if isinstance(vnext, list) and len(vnext) > 0:
                first = vnext[0]
                config.host = first.get("address")
                config.port = first.get("port")
                users = first.get("users", [])
                if isinstance(users, list) and len(users) > 0:
                    user = users[0]
                    config.ssh_user = user.get("id")
                    config.v2ray = user

        if isinstance(stream, dict):
            config.sni = stream.get("tlsSettings", {}).get("serverName")
            ws = stream.get("wsSettings", {})
            if ws:
                config.websocket = ws

        protocol = outbound.get("protocol", "")
        if "vmess" in protocol.lower():
            config.protocol = ProtocolEnum.VMESS
        elif "vless" in protocol.lower():
            config.protocol = ProtocolEnum.VLESS
        elif "trojan" in protocol.lower():
            config.protocol = ProtocolEnum.TROJAN
        else:
            config.protocol = ProtocolEnum.V2RAY

    # Security metadata
    if data.get("hardwareLock"):
        config.warnings.append("Config is HWID-locked")
    if data.get("passwordLock"):
        config.warnings.append("Config is password-locked")

    return config
