"""Phase-3 defensive probe — pure logic (no network): the fronting verdict
matrix, wildcard cert matching, HTTP-head parsing, and hostname sanitisation."""

import pytest

from snihunter.defensive import (
    _name_matches,
    _parse_http_head,
    _safe_hostname,
    classify_fronting,
    host_covered_by_cert,
)
from snihunter.models import SniFrontingResult


# ── classify_fronting ─────────────────────────────────────────────────────────

def test_tls_failure_is_error():
    assert classify_fronting(200, tls_handshake_ok=False) == "error"
    assert classify_fronting(None, tls_handshake_ok=False) == "error"


def test_no_status_is_indeterminate():
    assert classify_fronting(None, tls_handshake_ok=True) == "indeterminate"


def test_421_is_enforced():
    # Misdirected Request — the canonical SNI/Host cross-check signal.
    assert classify_fronting(421, tls_handshake_ok=True) == "enforced"


def test_2xx_3xx_is_bypassable():
    assert classify_fronting(200, tls_handshake_ok=True) == "bypassable"
    assert classify_fronting(301, tls_handshake_ok=True) == "bypassable"
    assert classify_fronting(302, tls_handshake_ok=True) == "bypassable"


def test_other_4xx_5xx_is_indeterminate():
    # A 403 "domain not configured" is ambiguous, not clearly enforcement.
    assert classify_fronting(403, tls_handshake_ok=True) == "indeterminate"
    assert classify_fronting(404, tls_handshake_ok=True) == "indeterminate"
    assert classify_fronting(500, tls_handshake_ok=True) == "indeterminate"


# ── wildcard cert matching ────────────────────────────────────────────────────

def test_exact_name_match():
    assert _name_matches("example.com", "example.com")
    assert not _name_matches("example.com", "other.com")


def test_wildcard_matches_one_label():
    assert _name_matches("a.example.com", "*.example.com")
    # wildcard covers exactly one label — not the apex, not two labels deep
    assert not _name_matches("example.com", "*.example.com")
    assert not _name_matches("a.b.example.com", "*.example.com")


def test_host_covered_by_cert_via_san():
    assert host_covered_by_cert("a.example.com", "example.com", ["*.example.com"])
    assert host_covered_by_cert("example.com", "example.com", [])
    assert not host_covered_by_cert("evil.com", "example.com", ["*.example.com"])


# ── HTTP head parsing ─────────────────────────────────────────────────────────

def test_parse_status_and_server():
    raw = b"HTTP/1.1 200 OK\r\nServer: cloudflare\r\nContent-Type: text/html\r\n\r\n<html>"
    status, reason, server = _parse_http_head(raw)
    assert status == 200
    assert reason == "OK"
    assert server == "cloudflare"


def test_parse_421():
    raw = b"HTTP/1.1 421 Misdirected Request\r\nServer: nginx\r\n\r\n"
    status, reason, server = _parse_http_head(raw)
    assert status == 421
    assert reason == "Misdirected Request"
    assert server == "nginx"


def test_parse_no_server_header():
    status, reason, server = _parse_http_head(b"HTTP/2 204 No Content\r\n\r\n")
    assert status == 204
    assert server is None


def test_parse_garbage_returns_none():
    assert _parse_http_head(b"") == (None, None, None)
    assert _parse_http_head(b"not http at all") == (None, None, None)


# ── hostname sanitisation (header-injection guard) ────────────────────────────

def test_safe_hostname_strips_wildcard_and_lowercases():
    assert _safe_hostname("*.Example.COM") == "example.com"


def test_safe_hostname_rejects_crlf_injection():
    # A Host with CRLF would let an attacker inject headers into the raw request.
    with pytest.raises(ValueError):
        _safe_hostname("example.com\r\nX-Injected: 1")
    with pytest.raises(ValueError):
        _safe_hostname("has space.com")
    with pytest.raises(ValueError):
        _safe_hostname("")


# ── model default ─────────────────────────────────────────────────────────────

def test_fronting_result_defaults():
    r = SniFrontingResult(sni="a.com", host_header="b.com")
    assert r.verdict == "indeterminate"
    assert r.port == 443
    assert r.probed_at
