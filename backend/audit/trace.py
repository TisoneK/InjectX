"""
InjectX — Audit Trace Logger

Records complete decrypt attempt history for forensic analysis.
Supports both in-memory and file-based persistence.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ir.models import DecryptTrace


class AuditLog:
    """
    Persistent audit log for decryption traces.

    Design invariant:
      - Every file processed gets a DecryptTrace
      - Traces are stored even if decryption fails
      - Traces survive application restart (file-backed)
    """

    def __init__(self, log_dir: Optional[str] = None):
        if log_dir:
            self._log_dir = Path(log_dir)
            self._log_dir.mkdir(parents=True, exist_ok=True)
        else:
            self._log_dir = None

        self._traces: dict[str, DecryptTrace] = {}

    def record(self, trace: DecryptTrace) -> None:
        """Record a decrypt trace."""
        key = f"{trace.filename}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
        self._traces[key] = trace

        if self._log_dir:
            self._persist(key, trace)

    def get(self, filename: str) -> list[DecryptTrace]:
        """Get all traces for a given filename."""
        return [t for k, t in self._traces.items() if filename in k]

    def get_all(self) -> dict[str, DecryptTrace]:
        """Get all recorded traces."""
        return dict(self._traces)

    def _persist(self, key: str, trace: DecryptTrace) -> None:
        """Persist trace to disk as JSON."""
        if not self._log_dir:
            return
        try:
            path = self._log_dir / f"{key}.json"
            # Pydantic v2: `.json()` is deprecated and `.json(indent=...)`
            # raises TypeError (`dumps_kwargs` no longer supported).
            # `model_dump_json(indent=...)` is the supported replacement
            # (Session 1 migrated `.dict()` → `model_dump()`; this completes
            # the v2 migration by handling the `.json()` form too).
            path.write_text(trace.model_dump_json(indent=2))
        except Exception:
            pass


# ── Singleton ─────────────────────────────────────────────────────────────────

_audit_log: Optional[AuditLog] = None


def get_audit_log(log_dir: Optional[str] = None) -> AuditLog:
    """Get or create the singleton AuditLog."""
    global _audit_log
    if _audit_log is None:
        _audit_log = AuditLog(log_dir)
    return _audit_log
