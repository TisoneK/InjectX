"""Exporters: .txt (working hosts only), .csv (all rows), .json (full job)."""

import json

from snihunter.export import export_job
from snihunter.models import SniProbeResult, SniScanJob


def _job():
    job = SniScanJob(job_id="j1", total=3)
    job.results = [
        SniProbeResult(hostname="good.com", target_ip="1.2.3.4", http_status=200,
                       verdict="working", server_header="cloudflare"),
        SniProbeResult(hostname="redir.com", target_ip="5.6.7.8", http_status=302,
                       verdict="redirect", http_redirect="https://other.com/"),
        SniProbeResult(hostname="dead.com", verdict="dead"),
    ]
    return job


def test_txt_only_working_hosts():
    body, media, name = export_job(_job(), "txt")
    assert media == "text/plain"
    assert name.endswith(".txt")
    assert body.strip() == "good.com"  # only the working host


def test_csv_has_all_rows():
    body, media, name = export_job(_job(), "csv")
    assert media == "text/csv"
    lines = [line for line in body.splitlines() if line.strip()]
    assert lines[0] == "hostname,ip,http_status,verdict,server,redirect"
    assert len(lines) == 4  # header + 3 results
    assert "good.com,1.2.3.4,200,working,cloudflare," in body


def test_json_roundtrips_job():
    body, media, name = export_job(_job(), "json")
    assert media == "application/json"
    data = json.loads(body)
    assert data["job_id"] == "j1"
    assert len(data["results"]) == 3


def test_unknown_format_raises():
    try:
        export_job(_job(), "xml")
        assert False, "expected ValueError"
    except ValueError:
        pass
