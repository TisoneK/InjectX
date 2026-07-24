"""
InjectX — SNI Host Hunter IR Models

A **parallel** IR surface, deliberately kept separate from
`ir.models.NormalizedConfig` (the config-file IR). A scan job is a
multi-host, multi-step process with a different cardinality and lifecycle
than a single parsed config file — folding it into NormalizedConfig would
break that IR's "one file on disk" invariant. See
`.context/memory/features/sni-host-hunter.md` §5.3 for the rationale and
ADR-6/7/8 in `plans/decisions.md`.

The bridge back to the config IR is the existing `sni` field on
NormalizedConfig: a discovered bug host gets written there when the user
picks "use this host" (a Phase 2 feature).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field


def _utcnow_iso() -> str:
    """Current UTC time as an ISO-8601 string (matches ir.models convention)."""
    return datetime.now(timezone.utc).isoformat()


# Verdict taxonomy for a probed host.
#   working  — reached the real server (2xx, or 4xx that still proves we hit it)
#   redirect — 3xx to somewhere that does NOT look like an ISP captive portal
#   blocked  — 3xx to an ISP captive/top-up/no-balance portal (bug host is dead)
#   dead     — DNS or TLS failed; the host isn't reachable at all
#   unknown  — not yet probed / indeterminate
Verdict = Literal["working", "redirect", "blocked", "dead", "unknown"]


class SniCandidate(BaseModel):
    """One hostname discovered as a potential bug host."""
    hostname: str
    source: Literal["crt.sh", "seedlist", "certstream", "manual"]
    discovered_at: str = Field(default_factory=_utcnow_iso)  # ISO-8601 UTC
    # Optional context carried from the discovery source (crt.sh fields).
    issuer_ca_id: Optional[int] = None
    not_before: Optional[str] = None
    not_after: Optional[str] = None


class SniProbeResult(BaseModel):
    """Result of probing one hostname (TLS handshake + HTTP GET + DNS checks)."""
    hostname: str
    # What we probed
    target_ip: Optional[str] = None
    port: int = 443
    timeout_s: float = 5.0
    # Outcomes
    tls_handshake_ok: bool = False
    http_status: Optional[int] = None
    http_redirect: Optional[str] = None       # Location header if 3xx
    server_header: Optional[str] = None        # Server: cloudflare, nginx, ...
    cert_cn: Optional[str] = None              # Subject CN from the server cert
    cert_sans: list[str] = []
    # DNS cross-checks
    forward_dns: list[str] = []                # A/AAAA records for hostname
    reverse_dns: Optional[str] = None          # PTR for target_ip
    dns_consistent: Optional[bool] = None      # forward_dns contains target_ip?
    # Verdict
    verdict: Verdict = "unknown"
    notes: list[str] = []
    probed_at: str = Field(default_factory=_utcnow_iso)
    elapsed_ms: float = 0.0


# Verdict taxonomy for the Phase-3 defensive fronting probe.
#   bypassable    — the server served a mismatched Host over an unrelated SNI:
#                   an ISP SNI-whitelist / web filter here is bypassable by
#                   domain fronting (its zero-rating would leak).
#   enforced      — the server/CDN cross-checks SNI vs Host (e.g. 421
#                   Misdirected Request, or rejects the mismatch): the filter
#                   holds.
#   indeterminate — reached the server but the response was ambiguous.
#   error         — DNS/TLS failed; nothing to conclude.
FrontingVerdict = Literal["bypassable", "enforced", "indeterminate", "error"]


class SniFrontingResult(BaseModel):
    """Result of a Phase-3 defensive probe: does sending a TLS SNI that differs
    from the HTTP Host header get through (domain fronting)? Also captures a
    TLS-cert fingerprint comparison across SNIs. See ADR-9 + design doc §3.5.

    Single-target, read-only, non-exploitative (ADR-9) — it reports what the
    server did with a mismatched Host; it never tunnels or relays traffic.
    """
    sni: str                                   # SNI sent in the TLS handshake
    host_header: str                           # HTTP Host header sent
    target_ip: Optional[str] = None            # IP we connected to (sni's A record)
    port: int = 443
    timeout_s: float = 5.0
    # TLS handshake with SNI = sni
    tls_handshake_ok: bool = False
    sni_cert_cn: Optional[str] = None
    sni_cert_sans: list[str] = []
    # Fingerprint comparison: cert served for a control SNI (the host_header)
    # against the SAME IP. If it differs, the server does SNI-based virtual
    # hosting (fronting is harder); if it matches, one default cert answers
    # every SNI (fronting-friendly).
    control_cert_cn: Optional[str] = None
    cert_changes_with_sni: Optional[bool] = None
    # Whether the host_header's cert is covered by the SNI cert (SAN/CN match) —
    # a domain-fronting precondition on shared infrastructure.
    host_covered_by_sni_cert: Optional[bool] = None
    # Raw HTTP GET / with the mismatched Host header
    http_status: Optional[int] = None
    server_header: Optional[str] = None
    http_reason: Optional[str] = None          # status reason phrase, if any
    # DNS cross-checks (what an ISP-side reverse-DNS/consistency check sees)
    sni_forward_dns: list[str] = []
    host_forward_dns: list[str] = []
    dns_consistent: Optional[bool] = None       # sni & host share an IP?
    # Verdict
    verdict: FrontingVerdict = "indeterminate"
    notes: list[str] = []
    probed_at: str = Field(default_factory=_utcnow_iso)
    elapsed_ms: float = 0.0


class SniScanJob(BaseModel):
    """A scan in progress or completed."""
    job_id: str
    created_at: str = Field(default_factory=_utcnow_iso)
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    status: Literal["queued", "running", "stopped", "done", "failed"] = "queued"
    # Inputs
    seed_domain: Optional[str] = None          # for `sni find <domain>`
    seedlist_path: Optional[str] = None        # for `sni scan <seedlist>`
    candidates: list[SniCandidate] = []
    # Config
    concurrency: int = 50
    timeout_s: float = 5.0
    cloudflare_only: bool = False
    # Progress
    total: int = 0
    done: int = 0
    found: int = 0                             # count of verdict == "working"
    # Results
    results: list[SniProbeResult] = []
    error: Optional[str] = None
