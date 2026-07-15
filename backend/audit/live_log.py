"""
InjectX — Live Log Buffer

Thread-safe in-memory log buffer that decryptors write to as they work.
The frontend polls /api/logs?since=N to stream entries in real-time.

Entries are kept in-memory only (never persisted) and capped at 500 to
bound memory use.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Optional


class LiveLog:
    """In-memory live log buffer, safe for concurrent read/write."""

    def __init__(self, max_entries: int = 500):
        self._entries: list[dict] = []
        self._counter = 0
        self._lock = threading.Lock()
        self._max = max_entries

    def add(self, tag: str, msg: str, type: str = "info", target: str = "") -> dict:
        """Add a log entry. Returns the entry."""
        with self._lock:
            self._counter += 1
            entry = {
                "id": self._counter,
                "tag": tag,
                "msg": msg,
                "type": type,
                "target": target,
                "ts": datetime.now(timezone.utc).isoformat(),
            }
            self._entries.append(entry)
            if len(self._entries) > self._max:
                # Trim oldest, but keep counter monotonic so `since` filters work
                self._entries = self._entries[-self._max:]
            return entry

    def since(self, n: int = 0) -> list[dict]:
        """Return all entries with id > n."""
        with self._lock:
            return [e for e in self._entries if e["id"] > n]

    def all(self) -> list[dict]:
        with self._lock:
            return list(self._entries)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
            self._counter = 0

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._entries)


# Singleton
_live_log: Optional[LiveLog] = None


def get_live_log() -> LiveLog:
    global _live_log
    if _live_log is None:
        _live_log = LiveLog()
    return _live_log
