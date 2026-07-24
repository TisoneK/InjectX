"""Tests for snihunter.apply — "use as SNI" override logic.

Pure-function tests against synthetic NormalizedConfig objects — no disk
re-parse. The async `apply_sni_to_config_id()` (which does the re-parse) is
exercised by the live curl pass against a real HC config.
"""
from __future__ import annotations

from ir.models import FormatEnum, NormalizedConfig
from snihunter.apply import apply_sni


def _make_config(sni: str | None = None, all_fields: dict | None = None) -> NormalizedConfig:
    cfg = NormalizedConfig(
        filepath="/tmp/fake.hc",
        filename="fake.hc",
        format=FormatEnum.HC,
    )
    if sni is not None:
        cfg.sni = sni
    if all_fields is not None:
        cfg.raw_data = {"_all_fields": dict(all_fields)}
    return cfg


# ── apply_sni ────────────────────────────────────────────────────────────────

def test_apply_sni_sets_top_level_field():
    cfg = _make_config(sni="old.example.com")
    out = apply_sni(cfg, "new.example.com")
    assert out.sni == "new.example.com"


def test_apply_sni_preserves_original_under_raw_data():
    cfg = _make_config(sni="old.example.com")
    out = apply_sni(cfg, "new.example.com")
    assert out.raw_data["_original_sni"] == "old.example.com"


def test_apply_sni_idempotent_on_original():
    cfg = _make_config(sni="old.example.com")
    out = apply_sni(cfg, "new.example.com")
    # Apply a second time — _original_sni should still be the very first value.
    out2 = apply_sni(out, "newer.example.com")
    assert out2.raw_data["_original_sni"] == "old.example.com"
    assert out2.sni == "newer.example.com"


def test_apply_sni_patches_all_fields_sni_keys():
    cfg = _make_config(sni="old.example.com",
                       all_fields={"sni": "old.example.com",
                                    "serverName": "old.example.com",
                                    "payload": "GET / HTTP/1.1"})
    out = apply_sni(cfg, "new.example.com")
    af = out.raw_data["_all_fields"]
    assert af["sni"] == "new.example.com"
    assert af["serverName"] == "new.example.com"
    assert af["payload"] == "GET / HTTP/1.1"  # untouched


def test_apply_sni_patches_all_sni_aliases():
    aliases = ["sni", "servername", "server_name", "snivalue", "snihostname",
               "hostsnissl", "customsni", "adv_ssl_spoofhost"]
    cfg = _make_config(sni="old.example.com",
                       all_fields={a: "old.example.com" for a in aliases})
    out = apply_sni(cfg, "new.example.com")
    af = out.raw_data["_all_fields"]
    for a in aliases:
        assert af[a] == "new.example.com", f"{a} not patched"


def test_apply_sni_adds_warning_with_before_after():
    cfg = _make_config(sni="old.example.com")
    out = apply_sni(cfg, "new.example.com")
    assert any("old.example.com" in w and "new.example.com" in w for w in out.warnings)


def test_apply_sni_adds_warning_when_no_original():
    cfg = _make_config(sni=None)
    out = apply_sni(cfg, "new.example.com")
    assert any("new.example.com" in w for w in out.warnings)
    assert out.sni == "new.example.com"


def test_apply_sni_no_warning_when_same_value():
    cfg = _make_config(sni="same.example.com")
    before = len(cfg.warnings)
    out = apply_sni(cfg, "same.example.com")
    assert len(out.warnings) == before  # no new warning


def test_apply_sni_rejects_empty_value():
    cfg = _make_config(sni="old.example.com")
    import pytest
    with pytest.raises(ValueError):
        apply_sni(cfg, "")
    with pytest.raises(ValueError):
        apply_sni(cfg, "   ")


def test_apply_sni_lowercases_and_strips():
    cfg = _make_config(sni="old.example.com")
    out = apply_sni(cfg, "  NEW.Example.COM  ")
    assert out.sni == "new.example.com"


def test_apply_sni_works_with_no_raw_data():
    cfg = NormalizedConfig(filepath="/tmp/x.hc", filename="x.hc", format=FormatEnum.HC)
    cfg.sni = "old.example.com"
    out = apply_sni(cfg, "new.example.com")
    assert out.sni == "new.example.com"
    assert out.raw_data == {"_original_sni": "old.example.com"}


def test_apply_sni_preserves_other_raw_data_keys():
    cfg = _make_config(sni="old.example.com")
    cfg.raw_data = {"_all_fields": {"sni": "old.example.com", "host": "1.2.3.4"},
                    "_debug": "keep me"}
    out = apply_sni(cfg, "new.example.com")
    assert out.raw_data["_debug"] == "keep me"
    assert out.raw_data["_all_fields"]["host"] == "1.2.3.4"
    assert out.raw_data["_all_fields"]["sni"] == "new.example.com"
    assert out.raw_data["_original_sni"] == "old.example.com"
