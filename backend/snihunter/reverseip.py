"""
Reverse IP lookup — "what other domains are hosted on this IP?" (BugScanX #4).

Given an IP address, return the list of hostnames that resolve to it. This is
the dual of forward DNS and is useful for SNI Host Hunter because an ISP's
zero-rating whitelist is often the *whole IP*, not just one SNI — so finding
sibling hostnames on the same IP can surface more bug-host candidates.

Per ADR-6, this uses PUBLIC APIs only — no active scanning. Two sources:

  1. HackerTarget's free reverse-IP endpoint
     `https://api.hackertarget.com/reverseiplookup/?q=<IP>`
     Returns plain text, one hostname per line. Free tier is rate-limited
     (~50 queries/day from one client IP, no auth). The API surfaces
     rate-limiting as a plain-text error string starting with "error" or
     "API count exceeded".

  2. PTR (reverse DNS) via stdlib `socket.gethostbyaddr` — always available,
     returns exactly one hostname (the canonical PTR) or none.

The module exposes both as async functions and a combined `lookup()` that
tries HackerTarget first and falls back to PTR. Each result is tagged with
its source so the UI can show "via HackerTarget" vs "via PTR".

This module is network-only; the parsing logic is split into pure functions
(`parse_hackertarget_response`) so it's unit-tested with fixture strings
and no HTTP.
"""

from __future__ import annotations

import asyncio
import socket
from typing import Literal

import httpx

from .models import SniCandidate

HACKERTARGET_URL = "https://api.hackertarget.com/reverseiplookup/?q={ip}"

# Rate-limit / error indicators HackerTarget surfaces as plain text.
_HT_ERROR_MARKERS = ("error", "api count exceeded", "limit", "try again")


ReverseIpSource = Literal["hackertarget", "ptr"]


def parse_hackertarget_response(body: str) -> tuple[list[str], str | None]:
    """Parse a HackerTarget reverse-IP plain-text response.

    Returns (hostnames, error). On a rate-limit/error response, returns
    ([], "<the error string>"). Pure — unit-tested directly.
    """
    if not body:
        return [], None
    body = body.strip()
    low = body.lower()
    # HackerTarget surfaces rate-limiting as a short plain-text message.
    if any(mark in low for mark in _HT_ERROR_MARKERS) and "\n" not in body:
        return [], body
    # Otherwise: one hostname per line (skip blanks + obvious junk).
    out: list[str] = []
    for line in body.splitlines():
        line = line.strip().lower()
        if not line:
            continue
        # HackerTarget occasionally returns "no records found" etc.
        if "no " in line and "found" in line:
            continue
        out.append(line)
    return out, None


async def _hackertarget(ip: str, timeout: float = 10.0) -> list[SniCandidate]:
    """Query HackerTarget for sibling hostnames on `ip`. Returns [] on any
    error or rate-limit (the caller falls back to PTR)."""
    url = HACKERTARGET_URL.format(ip=ip)
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True,
                                     headers={"User-Agent": "InjectX-SNIHunter"}) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            hosts, _err = parse_hackertarget_response(resp.text)
    except (httpx.HTTPError, ValueError):
        return []
    out: list[SniCandidate] = []
    seen: set[str] = set()
    for h in hosts:
        if h in seen:
            continue
        seen.add(h)
        out.append(SniCandidate(hostname=h, source="certstream",
                                 discovered_at=__import__("datetime").datetime.now(
                                     __import__("datetime").timezone.utc).isoformat()))
    return out


async def _ptr(ip: str) -> list[SniCandidate]:
    """Reverse DNS via gethostbyaddr — returns 0 or 1 hostname."""
    loop = asyncio.get_running_loop()
    try:
        name, _, _ = await loop.run_in_executor(None, socket.gethostbyaddr, ip)
    except (socket.herror, socket.gaierror, OSError):
        return []
    if not name:
        return []
    from datetime import datetime, timezone
    return [SniCandidate(hostname=name.lower(),
                          source="certstream",
                          discovered_at=datetime.now(timezone.utc).isoformat())]


async def lookup(ip: str, timeout: float = 10.0) -> dict:
    """Reverse-IP lookup combining HackerTarget + PTR.

    Returns a dict shaped for the API:

        {
          "ip": "...",
          "hostnames": ["a.com", "b.com", ...],   # deduped, lowercased
          "source": "hackertarget" | "ptr" | "none",
          "via_hackertarget": bool,               # whether HT returned data
          "via_ptr": bool,                        # whether PTR returned data
          "error": str | None,
        }
    """
    out = {
        "ip": ip,
        "hostnames": [],
        "source": "none",
        "via_hackertarget": False,
        "via_ptr": False,
        "error": None,
    }
    if not ip:
        out["error"] = "no IP provided"
        return out

    # Try HackerTarget first — it returns the full sibling list.
    ht = await _hackertarget(ip, timeout=timeout)
    if ht:
        out["hostnames"] = [c.hostname for c in ht]
        out["source"] = "hackertarget"
        out["via_hackertarget"] = True
        return out

    # Fall back to PTR — returns at most one hostname.
    ptr = await _ptr(ip)
    if ptr:
        out["hostnames"] = [c.hostname for c in ptr]
        out["source"] = "ptr"
        out["via_ptr"] = True
        return out

    out["error"] = "no reverse-IP data (HackerTarget empty/rate-limited, PTR empty)"
    return out
