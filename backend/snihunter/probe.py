"""
Active SNI prober.

For each candidate hostname:
  1. forward DNS   (A/AAAA)
  2. TLS handshake with SNI = hostname, capturing the server cert
  3. HTTP GET, classifying status/redirect into a verdict
  4. reverse DNS + forward/reverse consistency check

`classify_http` is a PURE function (no I/O) so the verdict logic is unit-tested
directly (backend/tests/test_sni_probe_result.py). The captive-portal heuristic
mirrors what BugScanX-Go's "DirectNon302" mode encodes: a working bug host
returns a real server response, while a dead one bounces to an ISP top-up /
no-balance portal — see `.context/memory/features/sni-host-hunter.md` §3.2/§3.5.

Abuse constraints (ADR-6): concurrency is hard-capped at SNI_MAX_CONCURRENCY and
each unique hostname is probed at most once per job. This is a research/
verification tool, not a network scanner.
"""

from __future__ import annotations

import asyncio
import socket
import ssl
import time
from pathlib import Path

import httpx

from .models import SniProbeResult, Verdict

# ADR-6: hard ceiling on concurrent probes. Requests above this are clamped.
SNI_MAX_CONCURRENCY = 200

# Captive-portal redirect indicators. Loaded from data/portal_indicators.txt so
# a user can add their ISP's pattern without a code change. Falls back to a
# built-in list if the file is missing.
_INDICATORS_FILE = Path(__file__).resolve().parent / "data" / "portal_indicators.txt"
_DEFAULT_INDICATORS = [
    "captive", "portal", "no-balance", "nobalance", "topup", "top-up",
    "data.bundles", "databundles", "internetsuppressed", "suppressed",
    "outofbundle", "out-of-bundle", "selfcare", "recharge", "unsubscribed",
]


def _load_indicators() -> list[str]:
    try:
        lines = _INDICATORS_FILE.read_text(encoding="utf-8").splitlines()
    except OSError:
        return list(_DEFAULT_INDICATORS)
    out = []
    for line in lines:
        line = line.split("#", 1)[0].strip().lower()
        if line:
            out.append(line)
    return out or list(_DEFAULT_INDICATORS)


_PORTAL_INDICATORS = _load_indicators()


def looks_like_captive_portal(url: str | None, indicators: list[str] | None = None) -> bool:
    """True if a redirect Location looks like an ISP captive/top-up portal."""
    if not url:
        return False
    inds = indicators if indicators is not None else _PORTAL_INDICATORS
    low = url.lower()
    return any(ind in low for ind in inds)


def classify_http(status: int | None, redirect_location: str | None = None,
                  indicators: list[str] | None = None) -> Verdict:
    """Pure verdict classifier from an HTTP response.

      2xx                          -> working  (reached the real server)
      4xx                          -> working  (403/404 still proves we hit it)
      3xx to a captive portal      -> blocked
      3xx elsewhere                -> redirect
      5xx / None                   -> dead
    """
    if status is None:
        return "dead"
    if 200 <= status < 300:
        return "working"
    if 300 <= status < 400:
        if looks_like_captive_portal(redirect_location, indicators):
            return "blocked"
        return "redirect"
    if 400 <= status < 500:
        return "working"
    return "dead"


async def _forward_dns(hostname: str, port: int) -> list[str]:
    loop = asyncio.get_running_loop()
    infos = await loop.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
    # Dedupe while preserving order (IPv4 first typically).
    ips: list[str] = []
    for info in infos:
        ip = info[4][0]
        if ip not in ips:
            ips.append(ip)
    return ips


async def _reverse_dns(ip: str) -> str | None:
    loop = asyncio.get_running_loop()
    try:
        name, _, _ = await loop.run_in_executor(None, socket.gethostbyaddr, ip)
        return name
    except (socket.herror, socket.gaierror, OSError):
        return None


def _extract_cert(peercert: dict) -> tuple[str | None, list[str]]:
    cn = None
    for rdn in peercert.get("subject", ()):  # ((("commonName", "x"),), ...)
        for k, v in rdn:
            if k == "commonName":
                cn = v
    sans = [v for typ, v in peercert.get("subjectAltName", ()) if typ == "DNS"]
    return cn, sans


async def probe_one(hostname: str, port: int = 443, timeout: float = 5.0) -> SniProbeResult:
    """Probe one hostname end-to-end and return a fully-filled SniProbeResult."""
    t0 = time.monotonic()
    result = SniProbeResult(hostname=hostname, port=port, timeout_s=timeout)
    try:
        # 1) forward DNS
        try:
            result.forward_dns = await asyncio.wait_for(_forward_dns(hostname, port), timeout)
        except (socket.gaierror, asyncio.TimeoutError, OSError):
            result.verdict = "dead"
            result.notes.append("DNS resolution failed")
            return result
        if not result.forward_dns:
            result.verdict = "dead"
            result.notes.append("no A/AAAA records")
            return result
        result.target_ip = result.forward_dns[0]

        # 2) TLS handshake with SNI = hostname
        ctx = ssl.create_default_context()
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(hostname, port, ssl=ctx, server_hostname=hostname),
                timeout=timeout,
            )
            result.tls_handshake_ok = True
            peercert = writer.get_extra_info("peercert")
            if peercert:
                result.cert_cn, result.cert_sans = _extract_cert(peercert)
            writer.close()
            try:
                await asyncio.wait_for(writer.wait_closed(), timeout)
            except (asyncio.TimeoutError, ssl.SSLError, OSError):
                pass
        except (ssl.SSLError, asyncio.TimeoutError, OSError) as e:
            result.verdict = "dead"
            result.notes.append(f"TLS handshake failed: {type(e).__name__}")
            return result

        # 3) HTTP GET over TLS — status + redirect
        try:
            async with httpx.AsyncClient(timeout=timeout, verify=True,
                                         follow_redirects=False) as client:
                r = await client.get(f"https://{hostname}/",
                                     headers={"User-Agent": "InjectX-SNIHunter"})
            result.http_status = r.status_code
            result.server_header = r.headers.get("server")
            if 300 <= r.status_code < 400:
                result.http_redirect = r.headers.get("location")
            result.verdict = classify_http(result.http_status, result.http_redirect)
            if result.verdict == "blocked":
                result.notes.append("redirect looks like an ISP captive portal")
        except httpx.HTTPError as e:
            # TLS worked but HTTP didn't — reachable, but not a clean bug host.
            result.verdict = "redirect" if result.tls_handshake_ok else "dead"
            result.notes.append(f"HTTP probe failed: {type(e).__name__}")

        # 4) reverse DNS + consistency
        if result.target_ip:
            result.reverse_dns = await _reverse_dns(result.target_ip)
            result.dns_consistent = result.target_ip in result.forward_dns
    finally:
        result.elapsed_ms = (time.monotonic() - t0) * 1000.0
    return result


def _dedupe_hostnames(hostnames: list[str]) -> list[str]:
    """ADR-6: probe each unique hostname at most once per job."""
    seen: set[str] = set()
    out: list[str] = []
    for h in hostnames:
        h = (h or "").strip().lower()
        if h and h not in seen:
            seen.add(h)
            out.append(h)
    return out


async def scan(hostnames: list[str], concurrency: int = 50, timeout: float = 5.0,
               on_result=None, stop_flag: asyncio.Event | None = None) -> list[SniProbeResult]:
    """Probe a list of hostnames concurrently.

    - concurrency is clamped to [1, SNI_MAX_CONCURRENCY] (ADR-6).
    - hostnames are deduped so each host is probed at most once.
    - `on_result(result)` is invoked after each probe (progress streaming).
    - `stop_flag` (asyncio.Event) short-circuits remaining probes when set.
    """
    hosts = _dedupe_hostnames(hostnames)
    concurrency = max(1, min(int(concurrency), SNI_MAX_CONCURRENCY))
    sem = asyncio.Semaphore(concurrency)
    results: list[SniProbeResult] = []

    async def _one(host: str) -> None:
        if stop_flag is not None and stop_flag.is_set():
            return
        async with sem:
            if stop_flag is not None and stop_flag.is_set():
                return
            res = await probe_one(host, timeout=timeout)
            results.append(res)
            if on_result is not None:
                on_result(res)

    await asyncio.gather(*[_one(h) for h in hosts])
    return results
