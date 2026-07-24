"""
Phase-3 defensive probe — SNI/Host-header mismatch (domain-fronting) detection.

The offensive half of SNI Host Hunter finds hosts whose *SNI* an ISP zero-rates.
The defensive half asks the mirror question: **is that zero-rating bypassable by
domain fronting?** — i.e. can a client present a whitelisted SNI in the TLS
handshake but a *different* `Host` header in the HTTP request and still reach the
real target? If so, the ISP's SNI-based filter leaks; if the server/CDN rejects
the mismatch (e.g. `421 Misdirected Request`), the cross-check holds.

This module answers all three Phase-3 (backlog N16) angles with one probe:
  1. **SNI/Host mismatch** — connect with SNI=`sni`, send `Host: host`, observe.
  2. **TLS fingerprint comparison** — does the cert served change when the SNI
     changes (SNI-based virtual hosting) or stay the same (one default cert,
     fronting-friendly)?
  3. **Enforcement verdict** — `bypassable` / `enforced` / `indeterminate`.

Reference: ntop/nDPI issue #2573 (SNI/Host mismatch + domain fronting), Compass
Security "SNI Spoofing" (2025). Design doc §3.5.

Constraints (ADR-9): single-target, read-only, non-exploitative — it observes
what the server does with a mismatched Host; it never tunnels or relays traffic.
`classify_fronting` is pure so the verdict logic is unit-tested with no network.
"""

from __future__ import annotations

import asyncio
import re
import socket
import ssl
import time

from .models import FrontingVerdict, SniFrontingResult

# A hostname sent into a raw HTTP request line must not carry CR/LF (header
# injection) or spaces. This also doubles as a light sanity check.
_HOSTNAME_SAFE = re.compile(r"^[A-Za-z0-9._-]{1,253}$")

# HTTP status line, e.g. "HTTP/1.1 421 Misdirected Request" (also tolerates
# "HTTP/2" with no minor version, defensively).
_STATUS_RE = re.compile(rb"^HTTP/\d(?:\.\d)?\s+(\d{3})\s*([^\r\n]*)", re.IGNORECASE)


def classify_fronting(status: int | None, tls_handshake_ok: bool) -> FrontingVerdict:
    """Pure verdict from the mismatched-Host probe.

      TLS failed                 -> error
      no HTTP status             -> indeterminate
      421 Misdirected Request    -> enforced  (server cross-checks SNI vs Host)
      2xx / 3xx                  -> bypassable (mismatch was served)
      other (4xx non-421, 5xx)   -> indeterminate
    """
    if not tls_handshake_ok:
        return "error"
    if status is None:
        return "indeterminate"
    if status == 421:
        return "enforced"
    if 200 <= status < 400:
        return "bypassable"
    return "indeterminate"


def _safe_hostname(name: str) -> str:
    name = (name or "").strip().lower().lstrip("*.")
    if not _HOSTNAME_SAFE.match(name):
        raise ValueError(f"Invalid hostname: {name!r}")
    return name


def _cert_names(peercert: dict | None) -> tuple[str | None, list[str]]:
    """(commonName, [DNS SANs]) from a parsed peer cert dict."""
    if not peercert:
        return None, []
    cn = None
    for rdn in peercert.get("subject", ()):
        for k, v in rdn:
            if k == "commonName":
                cn = v
    sans = [v for typ, v in peercert.get("subjectAltName", ()) if typ == "DNS"]
    return cn, sans


def _name_matches(host: str, cert_name: str | None) -> bool:
    """Match a host against one cert name, honouring a single leading wildcard."""
    if not cert_name:
        return False
    cert_name = cert_name.lower()
    host = host.lower()
    if cert_name.startswith("*."):
        # *.example.com matches a.example.com but not example.com or a.b.example.com
        suffix = cert_name[1:]  # ".example.com"
        return host.endswith(suffix) and host.count(".") == cert_name.count(".")
    return host == cert_name


def host_covered_by_cert(host: str, cn: str | None, sans: list[str]) -> bool:
    """True if `host` is covered by the cert's CN or any SAN (wildcard-aware)."""
    names = list(sans) + ([cn] if cn else [])
    return any(_name_matches(host, n) for n in names)


async def _forward_dns(hostname: str, port: int, timeout: float) -> list[str]:
    loop = asyncio.get_running_loop()
    try:
        infos = await asyncio.wait_for(
            loop.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP), timeout)
    except (socket.gaierror, asyncio.TimeoutError, OSError):
        return []
    ips: list[str] = []
    for info in infos:
        ip = info[4][0]
        if ip not in ips:
            ips.append(ip)
    return ips


async def _capture_cert(ip: str, sni: str, port: int, timeout: float,
                        strict_hostname: bool) -> tuple[bool, str | None, list[str]]:
    """Handshake to `ip` with SNI=`sni` and return (ok, cert_cn, cert_sans).

    strict_hostname=True validates the cert matches the SNI (used for the real
    SNI). strict_hostname=False keeps chain validation but tolerates a
    hostname mismatch (used for the control SNI, where we deliberately send a
    name the server's cert may not cover, just to read what cert it serves).
    """
    ctx = ssl.create_default_context()
    ctx.check_hostname = strict_hostname
    ctx.verify_mode = ssl.CERT_REQUIRED
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, port, ssl=ctx, server_hostname=sni), timeout)
    except (ssl.SSLError, asyncio.TimeoutError, OSError):
        return False, None, []
    try:
        cn, sans = _cert_names(writer.get_extra_info("peercert"))
        return True, cn, sans
    finally:
        writer.close()
        try:
            await asyncio.wait_for(writer.wait_closed(), timeout)
        except (asyncio.TimeoutError, ssl.SSLError, OSError):
            pass


async def _raw_http_get(ip: str, sni: str, host_header: str, port: int,
                        timeout: float) -> tuple[int | None, str | None, str | None]:
    """Send `GET / HTTP/1.1` with a mismatched `Host` header over a TLS
    connection whose SNI is `sni`. Returns (status, reason, server_header).

    Raw sockets because httpx couples SNI and Host to the URL — decoupling them
    is the whole point of a fronting probe.
    """
    ctx = ssl.create_default_context()
    ctx.check_hostname = True          # the connection itself validates against sni
    ctx.verify_mode = ssl.CERT_REQUIRED
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, port, ssl=ctx, server_hostname=sni), timeout)
    except (ssl.SSLError, asyncio.TimeoutError, OSError):
        return None, None, None
    try:
        # host_header is pre-sanitised (_safe_hostname) so no CRLF injection.
        req = (
            f"GET / HTTP/1.1\r\n"
            f"Host: {host_header}\r\n"
            f"User-Agent: InjectX-SNIHunter\r\n"
            f"Accept: */*\r\n"
            f"Connection: close\r\n\r\n"
        ).encode("latin-1", "ignore")
        writer.write(req)
        await asyncio.wait_for(writer.drain(), timeout)

        data = b""
        # Read just the response head (status line + headers).
        while b"\r\n\r\n" not in data and len(data) < 65536:
            chunk = await asyncio.wait_for(reader.read(4096), timeout)
            if not chunk:
                break
            data += chunk
        return _parse_http_head(data)
    except (asyncio.TimeoutError, ssl.SSLError, OSError):
        return None, None, None
    finally:
        writer.close()
        try:
            await asyncio.wait_for(writer.wait_closed(), timeout)
        except (asyncio.TimeoutError, ssl.SSLError, OSError):
            pass


def _parse_http_head(data: bytes) -> tuple[int | None, str | None, str | None]:
    """Parse an HTTP/1.x response head into (status, reason, server_header)."""
    if not data:
        return None, None, None
    head = data.split(b"\r\n\r\n", 1)[0]
    lines = head.split(b"\r\n")
    m = _STATUS_RE.match(lines[0])
    if not m:
        return None, None, None
    status = int(m.group(1))
    reason = m.group(2).decode("latin-1", "ignore").strip() or None
    server = None
    for line in lines[1:]:
        if b":" in line:
            k, _, v = line.partition(b":")
            if k.strip().lower() == b"server":
                server = v.decode("latin-1", "ignore").strip() or None
                break
    return status, reason, server


async def probe_fronting(sni: str, host: str, port: int = 443,
                         timeout: float = 5.0) -> SniFrontingResult:
    """Run the defensive fronting probe for one (sni, host) pair (ADR-9).

    Raises ValueError if either name is not a valid hostname.
    """
    sni = _safe_hostname(sni)
    host = _safe_hostname(host)
    t0 = time.monotonic()
    result = SniFrontingResult(sni=sni, host_header=host, port=port, timeout_s=timeout)
    try:
        # DNS for both names — the ISP-side reverse/consistency signal.
        result.sni_forward_dns = await _forward_dns(sni, port, timeout)
        result.host_forward_dns = await _forward_dns(host, port, timeout)
        if result.sni_forward_dns and result.host_forward_dns:
            shared = set(result.sni_forward_dns) & set(result.host_forward_dns)
            result.dns_consistent = bool(shared)
            if shared:
                result.notes.append("sni and host share an IP — co-located, fronting trivially possible")

        if not result.sni_forward_dns:
            result.verdict = "error"
            result.notes.append("SNI DNS resolution failed")
            return result
        result.target_ip = result.sni_forward_dns[0]

        # Cert served for the real SNI (strict — must validate against sni).
        ok, cn, sans = await _capture_cert(result.target_ip, sni, port, timeout, True)
        result.tls_handshake_ok = ok
        result.sni_cert_cn, result.sni_cert_sans = cn, sans
        if not ok:
            result.verdict = "error"
            result.notes.append("TLS handshake with SNI failed")
            return result
        result.host_covered_by_sni_cert = host_covered_by_cert(host, cn, sans)
        if result.host_covered_by_sni_cert:
            result.notes.append("sni's cert already covers host (shared cert / same CDN tenant)")

        # Control cert: same IP, SNI=host — does the cert change with the SNI?
        c_ok, c_cn, c_sans = await _capture_cert(result.target_ip, host, port, timeout, False)
        if c_ok:
            result.control_cert_cn = c_cn
            result.cert_changes_with_sni = (c_cn != cn) or (set(c_sans) != set(sans))
            if result.cert_changes_with_sni is False:
                result.notes.append("cert does not change with SNI — one default cert answers every SNI")
            else:
                result.notes.append("cert changes with SNI — SNI-based virtual hosting")

        # The actual fronting test: mismatched Host over the SNI connection.
        status, reason, server = await _raw_http_get(result.target_ip, sni, host, port, timeout)
        result.http_status = status
        result.http_reason = reason
        result.server_header = server

        result.verdict = classify_fronting(status, result.tls_handshake_ok)
        if result.verdict == "enforced":
            result.notes.append("server returned 421 Misdirected Request — SNI/Host cross-check enforced")
        elif result.verdict == "bypassable":
            result.notes.append(f"server served Host '{host}' over SNI '{sni}' (status {status}) — filter bypassable")
    finally:
        result.elapsed_ms = (time.monotonic() - t0) * 1000.0
    return result
