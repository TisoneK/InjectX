"""
InjectX — SNI Host Hunter package.

Discovers candidate SNI "bug hosts" (via Certificate Transparency logs and
bundled per-ISP seed lists), probes them (TLS handshake + HTTP + DNS
cross-checks), classifies each into a verdict, and exports the working set for
pasting back into a config's `sni` field.

Public surface:
  discover(domain)            -> list[SniCandidate]     (crt.sh)
  load_seedlist(path, cf_only)-> list[SniCandidate]     (bundled/user seed file)
  probe_one(host, ...)        -> SniProbeResult
  scan(hosts, ...)            -> list[SniProbeResult]
  sni_job_store               -> SniJobStore singleton

Design + rationale: `.context/memory/features/sni-host-hunter.md`.
Constraints: ADR-6/7/8 in `.context/memory/plans/decisions.md`.
"""

from __future__ import annotations

from .models import SniCandidate, SniProbeResult, SniScanJob, Verdict
from .probe import SNI_MAX_CONCURRENCY, classify_http, probe_one, scan
from .sources.crtsh import discover
from .sources.seedlist import list_bundled_seedlists, load_seedlist
from .store import sni_job_store

__all__ = [
    "SniCandidate",
    "SniProbeResult",
    "SniScanJob",
    "Verdict",
    "SNI_MAX_CONCURRENCY",
    "classify_http",
    "probe_one",
    "scan",
    "discover",
    "load_seedlist",
    "list_bundled_seedlists",
    "sni_job_store",
]
