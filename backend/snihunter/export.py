"""
Scan-result exporters: .txt / .csv / .json.

  .txt  — one working host per line (the drop-into-a-config-SNI-field format)
  .csv  — hostname,ip,status,verdict,server,redirect  (SNIbugtester's columns)
  .json — the full SniScanJob, model_dump()'d

`.txt` intentionally exports only verdict == "working" hosts — that's the list a
user pastes back into a config's `sni` field. `.csv`/`.json` carry every result.
"""

from __future__ import annotations

import csv
import io
import json

from .models import SniScanJob


def to_txt(job: SniScanJob) -> str:
    """Working hosts, one per line."""
    return "\n".join(r.hostname for r in job.results if r.verdict == "working") + "\n"


def to_csv(job: SniScanJob) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["hostname", "ip", "http_status", "verdict", "server", "redirect"])
    for r in job.results:
        w.writerow([
            r.hostname,
            r.target_ip or "",
            r.http_status if r.http_status is not None else "",
            r.verdict,
            r.server_header or "",
            r.http_redirect or "",
        ])
    return buf.getvalue()


def to_json(job: SniScanJob) -> str:
    return json.dumps(job.model_dump(), indent=2)


def export_job(job: SniScanJob, fmt: str) -> tuple[str, str, str]:
    """Return (body, media_type, suggested_filename) for the given format."""
    fmt = (fmt or "txt").lower()
    if fmt == "txt":
        return to_txt(job), "text/plain", f"sni-{job.job_id}.txt"
    if fmt == "csv":
        return to_csv(job), "text/csv", f"sni-{job.job_id}.csv"
    if fmt == "json":
        return to_json(job), "application/json", f"sni-{job.job_id}.json"
    raise ValueError(f"Unsupported export format: {fmt}")
