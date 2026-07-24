"""Tests for snihunter.reverseip — reverse-IP lookup via HackerTarget + PTR.

Pure-function tests against fixture response strings — no HTTP. The async
`lookup()` function is exercised by the live curl pass.
"""
from __future__ import annotations

from snihunter.reverseip import parse_hackertarget_response


# ── parse_hackertarget_response ──────────────────────────────────────────────

def test_parse_typical_multi_host_response():
    body = "example.com\nwww.example.com\napi.example.com\n"
    hosts, err = parse_hackertarget_response(body)
    assert err is None
    assert hosts == ["example.com", "www.example.com", "api.example.com"]


def test_parse_single_host():
    hosts, err = parse_hackertarget_response("only-host.com\n")
    assert err is None
    assert hosts == ["only-host.com"]


def test_parse_rate_limit_returns_error():
    body = "API count exceeded"
    hosts, err = parse_hackertarget_response(body)
    assert hosts == []
    assert err == "API count exceeded"


def test_parse_error_marker_returns_error():
    body = "error getting ip"
    hosts, err = parse_hackertarget_response(body)
    assert hosts == []
    assert err == body


def test_parse_no_records_found_returns_empty():
    body = "no records found"
    hosts, err = parse_hackertarget_response(body)
    assert err is None
    assert hosts == []


def test_parse_skips_blank_lines():
    body = "a.com\n\n\nb.com\n"
    hosts, err = parse_hackertarget_response(body)
    assert hosts == ["a.com", "b.com"]


def test_parse_empty_body():
    hosts, err = parse_hackertarget_response("")
    assert hosts == []
    assert err is None


def test_parse_lowercases_hostnames():
    body = "Example.COM\nWWW.Example.com\n"
    hosts, _ = parse_hackertarget_response(body)
    assert all(h == h.lower() for h in hosts)


def test_parse_multiline_error_with_newlines_is_treated_as_hostnames():
    # If a body has newlines, we treat each line as a hostname even if one
    # line happens to contain an error marker — the marker check only fires
    # on single-line bodies (HackerTarget's actual error responses are
    # single-line).
    body = "error.example.com\napi.example.com\n"
    hosts, _ = parse_hackertarget_response(body)
    assert "error.example.com" in hosts
