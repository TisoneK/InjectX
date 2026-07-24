"""
Open-port checker — TCP connect probe on a small fixed port set (BugScanX #7).

For a probed bug-host IP, knowing which common web ports are open tells you
whether the host is reachable on alternate ports (80, 8080, 8443) that might
bypass SNI-based billing or reach a different service. This is a *per-host*
check, NOT an IP-range scanner — ADR-6 forbids the latter.

Port set is deliberately small and fixed (the user can extend via the
`ports=` arg, but the default covers the web ports a bug host would serve).
The probe is a plain TCP connect with the same timeout as the TLS prober;
no banner-grabbing, no fingerprinting.
"""

from __future__ import annotations

import asyncio
from typing import Iterable

# Default port set — common web ports a bug host might serve. Kept small so
# the check is fast (4 parallel connects at ~5s timeout = ~5s wall clock).
DEFAULT_PORTS = (80, 443, 8080, 8443)

# ADR-6: never probe more than this many ports per host. The default set is
# well under; the cap is a backstop against a caller passing a huge list.
MAX_PORTS_PER_HOST = 32


async def probe_port(host: str, port: int, timeout: float = 3.0) -> bool:
    """True if a TCP connect to host:port succeeds within `timeout`."""
    try:
        fut = asyncio.open_connection(host, port)
        reader, writer = await asyncio.wait_for(fut, timeout=timeout)
        writer.close()
        try:
            await asyncio.wait_for(writer.wait_closed(), timeout=1.0)
        except (asyncio.TimeoutError, OSError):
            pass
        return True
    except (asyncio.TimeoutError, OSError, ConnectionError):
        return False


async def check_ports(host: str, ports: Iterable[int] | None = None,
                      timeout: float = 3.0) -> dict:
    """Probe a host on a fixed port set. Returns:

        {
          "host": "...",
          "ports": {"80": true, "443": true, "8080": false, ...},
          "open": [80, 443],
          "closed": [8080, 8443],
          "error": str | None,
        }
    """
    port_list = list(ports) if ports is not None else list(DEFAULT_PORTS)
    # ADR-6 backstop — never probe more than MAX_PORTS_PER_HOST.
    if len(port_list) > MAX_PORTS_PER_HOST:
        port_list = port_list[:MAX_PORTS_PER_HOST]

    out = {
        "host": host,
        "ports": {},
        "open": [],
        "closed": [],
        "error": None,
    }
    if not host:
        out["error"] = "no host provided"
        return out

    # Probe all ports concurrently — at this scale (≤32) we don't need a
    # semaphore.
    async def _one(p: int) -> tuple[int, bool]:
        return p, await probe_port(host, p, timeout=timeout)

    results = await asyncio.gather(*[_one(p) for p in port_list])
    for port, is_open in results:
        out["ports"][str(port)] = is_open
        (out["open"] if is_open else out["closed"]).append(port)
    out["open"].sort()
    out["closed"].sort()
    return out
