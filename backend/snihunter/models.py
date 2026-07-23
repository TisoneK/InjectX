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
