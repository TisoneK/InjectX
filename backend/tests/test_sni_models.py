"""IR construction + serialization for the SNI Host Hunter models."""

from snihunter.models import SniCandidate, SniProbeResult, SniScanJob


def test_candidate_defaults():
    c = SniCandidate(hostname="example.com", source="seedlist")
    assert c.hostname == "example.com"
    assert c.source == "seedlist"
    assert c.discovered_at  # auto-filled ISO timestamp
    assert c.issuer_ca_id is None


def test_candidate_roundtrip():
    c = SniCandidate(hostname="a.example.com", source="crt.sh", issuer_ca_id=42)
    d = c.model_dump()
    assert d["hostname"] == "a.example.com"
    assert d["issuer_ca_id"] == 42
    assert SniCandidate(**d) == c


def test_probe_result_default_verdict():
    r = SniProbeResult(hostname="example.com")
    assert r.verdict == "unknown"
    assert r.port == 443
    assert r.forward_dns == []
    assert r.probed_at


def test_scan_job_progress_fields():
    job = SniScanJob(job_id="abc123", total=3)
    assert job.status == "queued"
    assert job.done == 0
    assert job.found == 0
    assert job.concurrency == 50
    d = job.model_dump()
    assert d["job_id"] == "abc123"
    assert d["results"] == []
