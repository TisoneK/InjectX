"""crt.sh row parsing — dedupe, wildcard stripping, SAN splitting, junk
rejection. Tests the pure `parse_crtsh_rows` against fixture JSON (no HTTP)."""

from snihunter.sources.crtsh import parse_crtsh_rows


def test_multi_line_name_value_split():
    rows = [{"name_value": "a.example.com\nb.example.com", "common_name": "example.com"}]
    hosts = [c.hostname for c in parse_crtsh_rows(rows)]
    assert hosts == ["a.example.com", "b.example.com", "example.com"]


def test_wildcard_is_stripped():
    rows = [{"name_value": "*.example.com"}]
    hosts = [c.hostname for c in parse_crtsh_rows(rows)]
    assert hosts == ["example.com"]


def test_dedupe_across_rows():
    rows = [
        {"name_value": "a.example.com\nexample.com"},
        {"name_value": "example.com\nA.EXAMPLE.COM"},  # case-insensitive dupe
    ]
    hosts = [c.hostname for c in parse_crtsh_rows(rows)]
    assert hosts == ["a.example.com", "example.com"]


def test_email_and_junk_rejected():
    rows = [{"name_value": "admin@example.com\nnot a host\nvalid.example.com"}]
    hosts = [c.hostname for c in parse_crtsh_rows(rows)]
    assert hosts == ["valid.example.com"]


def test_issuer_metadata_propagates():
    rows = [{"name_value": "example.com", "issuer_ca_id": 7,
             "not_before": "2026-01-01", "not_after": "2026-04-01"}]
    c = parse_crtsh_rows(rows)[0]
    assert c.source == "crt.sh"
    assert c.issuer_ca_id == 7
    assert c.not_before == "2026-01-01"


def test_empty_rows():
    assert parse_crtsh_rows([]) == []
