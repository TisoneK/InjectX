"""Tests for snihunter.dns_check — ECH capability detection (RFC 9848).

Pure-function tests against synthetic RR-shaped objects — no real DNS I/O.
The async `check_ech()` function is exercised only by the live curl pass
(see the session review); here we lock down the parsing logic.
"""
from __future__ import annotations

import base64

from snihunter.dns_check import (
    _is_plausible_ech_value,
    extract_ech_config,
    is_ech_capable,
)


class _FakeParam(dict):
    """A dict that also matches keys case-insensitively (mimics dnspython's
    SvcParamKey enum-keyed params dict)."""

    def __contains__(self, key):  # type: ignore[override]
        return super().__contains__(key) or any(
            str(k).lower() == str(key).lower() for k in self.keys()
        )

    def items(self):  # type: ignore[override]
        return super().items()


class _FakeRR:
    """Minimal stand-in for a dnspython SVCB/HTTPS RR with a .params dict."""

    def __init__(self, params):
        self.params = params


def _ech_b64(payload: bytes) -> str:
    return base64.b64encode(payload).decode("ascii")


# ── _is_plausible_ech_value ──────────────────────────────────────────────────

def test_ech_value_real_config():
    # A real ECHConfigList: 2-byte length + ECHConfig (version 0xfe, 1-byte
    # config_id, 2-byte kem_id, 2-byte cipher_suites_len, ...). Anything ≥5
    # bytes passes.
    assert _is_plausible_ech_value(_ech_b64(b"\x00\x05\xfe\x01\x00\x20" + b"\x00" * 32))


def test_ech_value_empty_string_rejected():
    assert not _is_plausible_ech_value("")
    assert not _is_plausible_ech_value("   ")


def test_ech_value_too_short_rejected():
    # 3 bytes decodes fine but is too short to be a real ECHConfigList.
    assert not _is_plausible_ech_value(_ech_b64(b"\x00\x01\xfe"))


def test_ech_value_urlsafe_base64_accepted():
    payload = b"\x00\x10" + b"\xfe\x01" + b"\x00" * 20
    urlsafe = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    assert _is_plausible_ech_value(urlsafe)


def test_ech_value_garbage_rejected():
    assert not _is_plausible_ech_value("not-base64!@#")
    assert not _is_plausible_ech_value("====")


# ── extract_ech_config ───────────────────────────────────────────────────────

def test_extract_ech_string_key():
    rr = _FakeRR({"ech": _ech_b64(b"\x00\x10" + b"\xfe\x01" + b"\x00" * 20)})
    out = extract_ech_config([rr])
    assert out is not None
    assert out.startswith("A")  # base64 of 0x00


def test_extract_ech_enum_like_key():
    # Simulate a SvcParamKey enum-keyed dict by using an object whose str()
    # is "ech".
    class K:
        def __init__(self, s): self.s = s
        def __str__(self): return self.s
        def __hash__(self): return hash(self.s)
        def __eq__(self, o): return str(o) == self.s
    rr = _FakeRR({K("ECH"): _ech_b64(b"\x00\x10" + b"\xfe\x01" + b"\x00" * 20)})
    out = extract_ech_config([rr])
    assert out is not None


def test_extract_ech_empty_value_returns_none():
    rr = _FakeRR({"ech": ""})
    assert extract_ech_config([rr]) is None


def test_extract_ech_no_ech_param_returns_none():
    rr = _FakeRR({"port": "443", "alpn": ["h2", "http/1.1"]})
    assert extract_ech_config([rr]) is None


def test_extract_ech_list_valued_param():
    # Some dnspython versions return list-valued params.
    rr = _FakeRR({"ech": [_ech_b64(b"\x00\x10" + b"\xfe\x01" + b"\x00" * 20)]})
    out = extract_ech_config([rr])
    assert out is not None


def test_extract_ech_multiple_rrs_first_wins():
    rr1 = _FakeRR({"ech": ""})  # empty — skipped
    rr2 = _FakeRR({"ech": _ech_b64(b"\x00\x10" + b"\xfe\x01" + b"\x00" * 20)})
    out = extract_ech_config([rr1, rr2])
    assert out is not None


# ── is_ech_capable ───────────────────────────────────────────────────────────

def test_is_ech_capable_with_valid_ech():
    rr = _FakeRR({"ech": _ech_b64(b"\x00\x10" + b"\xfe\x01" + b"\x00" * 20)})
    assert is_ech_capable([rr]) is True


def test_is_ech_capable_empty_list():
    assert is_ech_capable([]) is False


def test_is_ech_capable_no_ech_param():
    rr = _FakeRR({"alpn": ["h2"]})
    assert is_ech_capable([rr]) is False


def test_is_ech_capable_empty_ech_value():
    rr = _FakeRR({"ech": ""})
    assert is_ech_capable([rr]) is False


def test_is_ech_capable_short_ech_value():
    rr = _FakeRR({"ech": _ech_b64(b"\x00\x01")})  # 2 bytes — too short
    assert is_ech_capable([rr]) is False
