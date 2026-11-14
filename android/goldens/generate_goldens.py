#!/usr/bin/env python3
"""Golden-vector generator for the InjectX Android (Kotlin) port.

Runs the EXISTING Python backend (`backend/parser/parse_engine.parse_config`)
over every bundled sample config in `assets/configs/` and writes one
deterministic JSON fixture per file under `android/goldens/fixtures/`.

The Kotlin port's tests load these fixtures and assert byte-identical
normalized output (ADR-10 §golden-vector parity). The Python backend is the
reference implementation; this script is the bridge.

Determinism: volatile fields (timestamps, elapsed_ms) are stripped and the
absolute `filepath` is rewritten to its repo-relative form, so re-running on
any machine yields identical fixtures (diffable in git).

Run (from repo root):
    backend/.venv/bin/python android/goldens/generate_goldens.py
or any Python with the backend deps installed:
    PYTHONPATH=backend python3 android/goldens/generate_goldens.py
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND = os.path.join(REPO_ROOT, "backend")
CONFIGS = os.path.join(REPO_ROOT, "assets", "configs")
OUT = os.path.join(REPO_ROOT, "android", "goldens", "fixtures")

# backend uses package-relative imports (`from ir.models import ...`,
# `import parser`), so backend/ must be the first entry on the path.
sys.path.insert(0, BACKEND)

from parser.parse_engine import parse_config  # noqa: E402

# Fields whose values are wall-clock / timing dependent — not part of the
# semantic result, so excluded from the golden so re-runs stay identical.
VOLATILE_KEYS = {"timestamp", "elapsed_ms", "total_elapsed_ms"}


def _scrub(obj):
    """Recursively drop volatile keys so fixtures are byte-stable."""
    if isinstance(obj, dict):
        return {k: _scrub(v) for k, v in obj.items() if k not in VOLATILE_KEYS}
    if isinstance(obj, list):
        return [_scrub(v) for v in obj]
    return obj


def _rel(path: str) -> str:
    try:
        return os.path.relpath(path, REPO_ROOT).replace(os.sep, "/")
    except ValueError:
        return os.path.basename(path)


def _sample_files():
    for root, _dirs, files in os.walk(CONFIGS):
        for name in sorted(files):
            if name == "README.md" or name == ".gitkeep":
                continue
            yield os.path.join(root, name)


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    index = []
    errors = 0
    for path in sorted(_sample_files()):
        rel = _rel(path)
        fmt_dir = os.path.basename(os.path.dirname(path))
        # ASCII-only, collision-free fixture names: sample names carry emoji /
        # Cyrillic / super-subscripts that break Gradle's resource copy and are
        # not portable, so slug = fmt + ASCII-scrubbed stem + short path hash.
        stem = re.sub(r"[^A-Za-z0-9.]+", "_", os.path.basename(path)).strip("_")
        digest = hashlib.sha1(rel.encode("utf-8")).hexdigest()[:8]
        slug = f"{fmt_dir}__{stem}__{digest}"
        try:
            cfg = parse_config(path)
            data = cfg.model_dump(mode="json")
            # Normalize machine-specific identity so the fixture is portable.
            data["filepath"] = rel
            data = _scrub(data)
            fixture = {"source": rel, "normalized": data}
            status = data.get("decryption_status")
            scheme = data.get("scheme_used")
            fmt = data.get("format")
        except Exception as exc:  # noqa: BLE001 — a sample that throws is a real signal
            fixture = {"source": rel, "error": f"{type(exc).__name__}: {exc}"}
            status = "EXCEPTION"
            scheme = None
            fmt = None
            errors += 1

        out_path = os.path.join(OUT, slug + ".json")
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(fixture, fh, indent=2, ensure_ascii=False, sort_keys=True)
            fh.write("\n")
        index.append(
            {"fixture": slug + ".json", "source": rel, "format": fmt,
             "decryption_status": status, "scheme_used": scheme}
        )
        print(f"  {slug:<48} format={fmt} status={status} scheme={scheme}")

    with open(os.path.join(OUT, "index.json"), "w", encoding="utf-8") as fh:
        json.dump({"count": len(index), "errors": errors, "fixtures": index},
                  fh, indent=2, ensure_ascii=False, sort_keys=True)
        fh.write("\n")

    print(f"\nWrote {len(index)} fixtures to {_rel(OUT)} ({errors} raised exceptions).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
