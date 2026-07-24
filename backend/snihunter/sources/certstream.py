"""
CertStream discovery source — real-time Certificate Transparency monitoring.

CertStream (CaliDog) is a free websocket feed that streams newly-issued
certificates from the CT log network in real time. `certstream-python`
(`pip install certstream`) is the maintained client.

For SNI Host Hunter this is the **watch mode**: subscribe to the live feed
for a short window (default 60s), collect every hostname that appears in a
newly-issued cert's SAN/CN for the target domain, and return them as
SniCandidates. This is the "phase 2" companion to crt.sh's *historical*
discovery — crt.sh gives you every cert ever issued; certstream gives you
the ones issued *while you watch*.

Design constraints:
  - certstream is an OPTIONAL dep — if it's not installed, `watch()` raises
    a clean ImportError the caller can surface as a 503, not a crash.
  - The certstream client uses a blocking `listen_for_certs()` with a
    callback. We run it in a thread and signal it to stop after `duration_s`
    via the library's `stop()` method.
  - As with crt.sh, hostnames are cleaned, deduped, and filtered to the
    target domain before being returned.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Optional

from ..models import SniCandidate
from .crtsh import _clean  # reuse the same hostname-normalisation + regex


def _extract_hostnames(message: dict) -> list[str]:
    """Pull every SAN/CN hostname out of a certstream message dict.

    CertStream's message shape (verified against CaliDog/certstream-python
    README + the certstream.dev API docs, 2026-07-24):
        {
          "message_type": "certificate_update",
          "data": {
            "cert_der": "...base64...",
            "leaf_cert": {
              "all_domains": ["example.com", "www.example.com", ...],
              "subject": {"CN": ["example.com"]},
            },
            "seen": 1234567890.0,
            "source": {...},
          }
        }
    `all_domains` already includes the CN + every SAN, deduped — so we just
    trust it. Falls back to `subject.CN` if `all_domains` is missing.
    """
    if not isinstance(message, dict):
        return []
    if message.get("message_type") != "certificate_update":
        return []
    data = message.get("data") or {}
    leaf = data.get("leaf_cert") or {}
    domains = leaf.get("all_domains") or []
    if not domains:
        # Fall back to subject CN if all_domains is absent (older feed shape).
        subj = leaf.get("subject") or {}
        cn = subj.get("CN") or subj.get("commonName") or []
        if isinstance(cn, str):
            cn = [cn]
        domains = cn
    return [str(d) for d in domains if isinstance(d, str)]


def filter_to_domain(hostnames: list[str], domain: str) -> list[str]:
    """Return only hostnames that are `domain` or a subdomain of it.

    Pure function — unit-tested directly.
    """
    domain = (domain or "").strip().lower().lstrip("*.")
    if not domain:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for h in hostnames:
        clean = _clean(h)
        if not clean or clean in seen:
            continue
        if clean == domain or clean.endswith("." + domain):
            seen.add(clean)
            out.append(clean)
    return out


async def watch(domain: str, duration_s: float = 60.0,
                on_candidate=None) -> list[SniCandidate]:
    """Subscribe to the CertStream feed for `duration_s` and collect new
    hostnames for `domain`. Returns the deduped SniCandidate list.

    `on_candidate(candidate)` is invoked for each new hostname as it's seen
    (live progress — mirrors `scan(on_result=...)`).

    Raises ImportError if the `certstream` package isn't installed. The
    caller (API layer) surfaces that as a 503 "CertStream not available".
    """
    try:
        import certstream  # type: ignore
    except ImportError as e:
        raise ImportError(
            "certstream is not installed. Run `pip install certstream` to "
            "enable real-time CT monitoring (Phase 2 SNI Host Hunter)."
        ) from e

    domain = (domain or "").strip().lower().lstrip("*.")
    if not domain:
        return []

    candidates: list[SniCandidate] = []
    seen: set[str] = set()
    out_lock = threading.Lock()
    stop_event = threading.Event()

    def _on_message(message: dict) -> None:
        if message.get("message_type") != "certificate_update":
            return
        for host in filter_to_domain(_extract_hostnames(message), domain):
            with out_lock:
                if host in seen:
                    continue
                seen.add(host)
                cand = SniCandidate(hostname=host, source="certstream")
                candidates.append(cand)
            if on_candidate is not None:
                try:
                    on_candidate(cand)
                except Exception:
                    pass  # a progress callback must never break the watch

    # certstream.listen_for_certs blocks. Run it in a thread, stop it after
    # duration_s via the thread-target's own stop handle.
    certstream_thread: list = []

    def _run() -> None:
        st = certstream.CertStreamClient(_on_message, skip_heartbeats=True)
        certstream_thread.append(st)
        # stop_event lets us break out early if the caller cancels.
        st.run()

    t = threading.Thread(target=_run, daemon=True)
    t.start()

    async def _waiter() -> None:
        # Poll the stop event so we can return early on cancellation.
        deadline = asyncio.get_event_loop().time() + duration_s
        while not stop_event.is_set():
            now = asyncio.get_event_loop().time()
            if now >= deadline:
                break
            await asyncio.sleep(min(0.5, deadline - now))

    try:
        await _waiter()
    finally:
        stop_event.set()
        if certstream_thread:
            try:
                certstream_thread[0].stop()
            except Exception:
                pass
        t.join(timeout=2.0)

    return list(candidates)


# Re-exported so callers can build candidates from external certstream feeds
# without a network round-trip (used by tests + the live-watch endpoint).
def build_candidates(hostnames: list[str], domain: str) -> list[SniCandidate]:
    """Turn a raw list of hostnames (e.g. from a certstream message) into
    deduped SniCandidates filtered to `domain`. Pure — no I/O."""
    out: list[SniCandidate] = []
    seen: set[str] = set()
    for host in filter_to_domain(hostnames, domain):
        if host in seen:
            continue
        seen.add(host)
        out.append(SniCandidate(hostname=host, source="certstream"))
    return out
