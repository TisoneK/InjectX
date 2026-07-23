"""
In-memory scan-job store.

Mirrors the `config_store` pattern in main.py (a module-level dict) but wraps
it in a small class with a lock and per-job stop flags, so a running scan can
be cancelled and its progress polled by the UI. Jobs are never persisted — the
store is cleared on backend restart, same as config_store.
"""

from __future__ import annotations

import asyncio
import threading

from .models import SniScanJob

# Cap the number of retained jobs so a long-running backend can't grow the
# store without bound (mirrors backlog N5's concern for config_store). Oldest
# finished jobs are evicted first.
MAX_JOBS = 100


class SniJobStore:
    """Thread-safe store for scan jobs + their asyncio stop flags."""

    def __init__(self) -> None:
        self._jobs: dict[str, SniScanJob] = {}
        self._stop_flags: dict[str, asyncio.Event] = {}
        self._lock = threading.Lock()

    def add(self, job: SniScanJob) -> None:
        with self._lock:
            self._jobs[job.job_id] = job
            self._evict_locked()

    def get(self, job_id: str) -> SniScanJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self) -> list[SniScanJob]:
        with self._lock:
            # Newest first (created_at is ISO-8601, lexically sortable).
            return sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)

    def stop_flag(self, job_id: str) -> asyncio.Event:
        """Get (creating if needed) the stop flag for a job."""
        with self._lock:
            ev = self._stop_flags.get(job_id)
            if ev is None:
                ev = asyncio.Event()
                self._stop_flags[job_id] = ev
            return ev

    def request_stop(self, job_id: str) -> bool:
        """Signal a running job to stop. Returns True if the job exists."""
        with self._lock:
            if job_id not in self._jobs:
                return False
            ev = self._stop_flags.get(job_id)
            if ev is None:
                ev = asyncio.Event()
                self._stop_flags[job_id] = ev
            ev.set()
            return True

    def _evict_locked(self) -> None:
        if len(self._jobs) <= MAX_JOBS:
            return
        # Evict oldest finished jobs first; never evict a running/queued one.
        finished = [j for j in self._jobs.values()
                    if j.status in ("done", "stopped", "failed")]
        finished.sort(key=lambda j: j.created_at)
        for j in finished:
            if len(self._jobs) <= MAX_JOBS:
                break
            self._jobs.pop(j.job_id, None)
            self._stop_flags.pop(j.job_id, None)

    def clear(self) -> None:
        with self._lock:
            self._jobs.clear()
            self._stop_flags.clear()


# Module-level singleton (same pattern as ir.audit.live_log.get_live_log).
sni_job_store = SniJobStore()
