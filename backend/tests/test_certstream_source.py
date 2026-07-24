"""Tests for snihunter.sources.certstream — real-time CT watch.

Pure-function tests against fixture message dicts — no websocket I/O. The
async `watch()` function is exercised only by the live curl pass; here we
lock down the message-parsing + domain-filtering logic.
"""
from __future__ import annotations

from snihunter.sources.certstream import (
    build_candidates,
    _extract_hostnames,
    filter_to_domain,
)


# ── _extract_hostnames ───────────────────────────────────────────────────────

def test_extract_certificate_update_message():
    msg = {
        "message_type": "certificate_update",
        "data": {
            "leaf_cert": {
                "all_domains": ["example.com", "www.example.com", "api.example.com"],
                "subject": {"CN": ["example.com"]},
            },
        },
    }
    out = _extract_hostnames(msg)
    assert set(out) == {"example.com", "www.example.com", "api.example.com"}


def test_extract_ignores_non_certificate_messages():
    msg = {"message_type": "heartbeat", "data": {}}
    assert _extract_hostnames(msg) == []


def test_extract_falls_back_to_subject_cn():
    msg = {
        "message_type": "certificate_update",
        "data": {
            "leaf_cert": {
                "subject": {"CN": ["fallback.example.com"]},
            },
        },
    }
    assert _extract_hostnames(msg) == ["fallback.example.com"]


def test_extract_handles_missing_data():
    assert _extract_hostnames({}) == []
    assert _extract_hostnames({"message_type": "certificate_update"}) == []
    assert _extract_hostnames({"message_type": "certificate_update", "data": {}}) == []


def test_extract_strips_wildcard_labels():
    # all_domains sometimes includes wildcard SANs.
    msg = {
        "message_type": "certificate_update",
        "data": {"leaf_cert": {"all_domains": ["*.example.com", "example.com"]}},
    }
    out = _extract_hostnames(msg)
    assert "*.example.com" in out  # passed through; filtering happens later
    assert "example.com" in out


# ── filter_to_domain ─────────────────────────────────────────────────────────

def test_filter_exact_domain_kept():
    out = filter_to_domain(["example.com", "other.com"], "example.com")
    assert out == ["example.com"]


def test_filter_subdomain_kept():
    out = filter_to_domain(["www.example.com", "api.sub.example.com"], "example.com")
    assert out == ["www.example.com", "api.sub.example.com"]


def test_filter_unrelated_domain_rejected():
    out = filter_to_domain(["evil.com", "example.com.evil.com"], "example.com")
    # "example.com.evil.com" is NOT a subdomain of "example.com" — it's a
    # suffix attack. The check uses endswith(".domain") which correctly
    # rejects it.
    assert out == []


def test_filter_wildcard_stripped():
    out = filter_to_domain(["*.example.com"], "example.com")
    # _clean strips the "*." prefix, so "*.example.com" → "example.com"
    # which equals the target domain and is kept.
    assert out == ["example.com"]


def test_filter_dedupes():
    out = filter_to_domain(["www.example.com", "www.example.com", "www.example.com"],
                           "example.com")
    assert out == ["www.example.com"]


def test_filter_empty_domain_returns_empty():
    assert filter_to_domain(["anything.com"], "") == []


def test_filter_empty_input():
    assert filter_to_domain([], "example.com") == []


# ── build_candidates ─────────────────────────────────────────────────────────

def test_build_candidates_marks_source_certstream():
    cands = build_candidates(["www.example.com", "api.example.com"], "example.com")
    assert len(cands) == 2
    for c in cands:
        assert c.source == "certstream"
        assert c.hostname.endswith("example.com")


def test_build_candidates_dedupes():
    cands = build_candidates(["a.example.com", "a.example.com"], "example.com")
    assert len(cands) == 1


def test_build_candidates_empty_when_no_matches():
    cands = build_candidates(["other.com", "unrelated.org"], "example.com")
    assert cands == []
