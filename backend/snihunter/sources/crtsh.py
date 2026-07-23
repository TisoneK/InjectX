"""
crt.sh discovery source.

Queries Sectigo's Certificate Transparency search (crt.sh) for every
certificate ever issued for a domain and its subdomains, and returns the
deduped SAN/CN list as SniCandidates. One async HTTP GET per domain.

Reference (verified 2026-07-24, re-verified 2026-07-24 Session 24):
  https://crt.sh/?q=%.<domain>&output=json
  `name_value` is a "\n"-separated list of SANs; `common_name` is the CN.
crt.sh remains the canonical, free, CT-log aggregator in 2026 — see
`.context/memory/features/sni-host-hunter.md` §3.1.
"""

from __future__ import annotations

import re

import httpx

from ..models import SniCandidate

# `%` is the SQL wildcard crt.sh uses; `%.domain` matches every subdomain.
CRT_SH_URL = "https://crt.sh/?q=%25.{domain}&output=json"

# Conservative hostname sanity check — rejects obvious junk (emails,
# whitespace, IPs-as-names) before a name reaches the prober.
_HOSTNAME_RE = re.compile(r"^(?=.{1,253}$)([a-z0-9_-]{1,63}\.)+[a-z]{2,63}$")


def _clean(name: str) -> str | None:
    """Normalise one CT name into a bare probeable hostname, or None."""
    name = name.strip().lower()
    if not name:
        return None
    # Strip a leading wildcard label ("*.example.com" -> "example.com").
    if name.startswith("*."):
        name = name[2:]
    # crt.sh occasionally returns email SANs in name_value; skip them.
    if "@" in name or " " in name:
        return None
    if not _HOSTNAME_RE.match(name):
        return None
    return name


def parse_crtsh_rows(rows: list[dict]) -> list[SniCandidate]:
    """Turn raw crt.sh JSON rows into a deduped SniCandidate list.

    Split out from the network call so it can be unit-tested against fixture
    JSON with no HTTP (see backend/tests/test_crtsh_source.py).
    """
    seen: set[str] = set()
    out: list[SniCandidate] = []
    for row in rows:
        # name_value holds the SANs ("\n"-separated); common_name the CN.
        names = list(row.get("name_value", "").split("\n"))
        cn = row.get("common_name")
        if cn:
            names.append(cn)
        for raw in names:
            host = _clean(raw)
            if not host or host in seen:
                continue
            seen.add(host)
            out.append(SniCandidate(
                hostname=host,
                source="crt.sh",
                issuer_ca_id=row.get("issuer_ca_id"),
                not_before=row.get("not_before"),
                not_after=row.get("not_after"),
            ))
    return out


async def discover(domain: str, timeout: float = 30.0) -> list[SniCandidate]:
    """Query crt.sh for `domain` and return deduped SniCandidates.

    Raises httpx.HTTPError on network/HTTP failure — the caller decides how
    to surface it (the API layer wraps it into a 502/failed job).
    """
    domain = domain.strip().lower().lstrip("*.")
    if not domain:
        return []
    url = CRT_SH_URL.format(domain=domain)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True,
                                 headers={"User-Agent": "InjectX-SNIHunter"}) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        rows = resp.json()
    if not isinstance(rows, list):
        return []
    return parse_crtsh_rows(rows)
