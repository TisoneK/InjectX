"""
InjectX — SNI Host Hunter package.

Discovers candidate SNI "bug hosts" (via Certificate Transparency logs and
bundled per-ISP seed lists), probes them (TLS handshake + HTTP + DNS
cross-checks), classifies each into a verdict, and exports the working set for
pasting back into a config's `sni` field.

Public surface:
  discover(domain)            -> list[SniCandidate]     (crt.sh)
  watch(domain, ...)          -> list[SniCandidate]     (certstream, Phase 2)
  load_seedlist(path, cf_only)-> list[SniCandidate]     (bundled/user seed file)
  probe_one(host, ...)        -> SniProbeResult
  scan(hosts, ...)            -> list[SniProbeResult]
  check_ech(host, ...)        -> dict                   (RFC 9848 HTTPS-RR, Phase 2)
  reverseip.lookup(ip, ...)   -> dict                   (Phase 2)
  portcheck.check_ports(host) -> dict                   (Phase 2)
  apply_sni_to_config_id(...) -> NormalizedConfig       ("use as SNI", Phase 2)
  sni_job_store               -> SniJobStore singleton

Design + rationale: `.context/memory/features/sni-host-hunter.md`.
Constraints: ADR-6/7/8 in `.context/memory/plans/decisions.md`.
"""

from __future__ import annotations

from .apply import apply_sni, apply_sni_to_config_id
from .dns_check import check_ech, extract_ech_config, is_ech_capable
from .models import SniCandidate, SniProbeResult, SniScanJob, Verdict
from .portcheck import check_ports, probe_port
from .probe import SNI_MAX_CONCURRENCY, classify_http, probe_one, scan
from .reverseip import lookup as reverseip_lookup
from .sources.certstream import watch as watch_certstream
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
    "watch_certstream",
    "load_seedlist",
    "list_bundled_seedlists",
    "check_ech",
    "extract_ech_config",
    "is_ech_capable",
    "reverseip_lookup",
    "check_ports",
    "probe_port",
    "apply_sni",
    "apply_sni_to_config_id",
    "sni_job_store",
]

