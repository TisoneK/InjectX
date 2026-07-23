"""
Seed-list loader.

Loads a per-ISP seed list of candidate hostnames from disk. Three formats:

  .txt  — one hostname per line; `#` starts a comment; blank lines ignored.
  .csv  — a `domain` (or `hostname`/`host`) column; optional `cloudflare` col.
  .json — an array of strings, OR of objects {"domain"/"hostname", "cloudflare"}.

The `cloudflare_only` filter keeps only entries flagged cloudflare:true — only
meaningful for the .csv/.json formats that carry the flag (SNIbugtester's model).

Bundled seedlists ship in-tree under data/seedlists/ (ADR-8). This module only
PARSES an already-validated path — path/extension/size validation is the API
layer's job (`_validate_seedlist_path` in main.py), mirroring how config parsing
trusts `_validate_config_path`.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from ..models import SniCandidate

# Bundled seedlists live next to this package.
SEEDLISTS_DIR = Path(__file__).resolve().parent.parent / "data" / "seedlists"


def _mk(hostname: str) -> SniCandidate:
    return SniCandidate(hostname=hostname.strip().lower().lstrip("*."), source="seedlist")


def _parse_txt(text: str) -> list[tuple[str, bool]]:
    out: list[tuple[str, bool]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # allow "host  # inline comment"
        line = line.split("#", 1)[0].strip()
        if line:
            out.append((line, False))
    return out


def _truthy(v) -> bool:
    return str(v).strip().lower() in ("1", "true", "yes", "y", "on")


def _parse_csv(text: str) -> list[tuple[str, bool]]:
    out: list[tuple[str, bool]] = []
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return out
    cols = {c.lower(): c for c in reader.fieldnames}
    host_col = cols.get("domain") or cols.get("hostname") or cols.get("host")
    cf_col = cols.get("cloudflare") or cols.get("cf")
    if not host_col:
        # Headerless single-column CSV — treat every first cell as a host.
        for row in csv.reader(io.StringIO(text)):
            if row and row[0].strip() and not row[0].startswith("#"):
                out.append((row[0].strip(), False))
        return out
    for row in reader:
        host = (row.get(host_col) or "").strip()
        if not host:
            continue
        cf = _truthy(row.get(cf_col)) if cf_col else False
        out.append((host, cf))
    return out


def _parse_json(text: str) -> list[tuple[str, bool]]:
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("JSON seedlist must be an array")
    out: list[tuple[str, bool]] = []
    for item in data:
        if isinstance(item, str):
            if item.strip():
                out.append((item.strip(), False))
        elif isinstance(item, dict):
            host = item.get("domain") or item.get("hostname") or item.get("host")
            if host and str(host).strip():
                out.append((str(host).strip(), _truthy(item.get("cloudflare"))))
    return out


def load_seedlist(path: str | Path, cloudflare_only: bool = False) -> list[SniCandidate]:
    """Parse a seedlist file into deduped SniCandidates.

    `cloudflare_only` keeps only cloudflare-flagged entries (csv/json only).
    Raises ValueError on an unsupported extension or malformed content.
    """
    p = Path(path)
    ext = p.suffix.lower()
    text = p.read_text(encoding="utf-8", errors="replace")

    if ext == ".txt":
        pairs = _parse_txt(text)
    elif ext == ".csv":
        pairs = _parse_csv(text)
    elif ext == ".json":
        pairs = _parse_json(text)
    else:
        raise ValueError(f"Unsupported seedlist extension: {ext}")

    seen: set[str] = set()
    out: list[SniCandidate] = []
    for host, cf in pairs:
        if cloudflare_only and not cf:
            continue
        cand = _mk(host)
        if not cand.hostname or cand.hostname in seen:
            continue
        seen.add(cand.hostname)
        out.append(cand)
    return out


def list_bundled_seedlists() -> list[dict]:
    """List the seedlists shipped in-tree under data/seedlists/."""
    if not SEEDLISTS_DIR.exists():
        return []
    out: list[dict] = []
    for p in sorted(SEEDLISTS_DIR.glob("*")):
        if not p.is_file() or p.name.startswith(".") or p.name == "README.md":
            continue
        if p.suffix.lower() not in (".txt", ".csv", ".json"):
            continue
        try:
            n = len(load_seedlist(p))
        except Exception:
            n = 0
        out.append({
            "name": p.name,
            "path": str(p),
            "ext": p.suffix.lower(),
            "hosts": n,
            "size": p.stat().st_size,
        })
    return out
