"""Tests for the runtime keyfile mechanism.

Extracted keys reach the decryptors two ways:
  1. KeyStore(keyfile_path) merges an external JSON file over defaults.
  2. get_router() picks up INJECTX_KEYFILE when no path is passed.

This guards the wiring in decrypt/router.get_router — previously
KeyStore._load_keyfile existed but nothing ever passed a path, so a
supplied keyfile was silently ignored.
"""

import importlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _write_keyfile(tmp_path: Path, data: dict) -> str:
    p = tmp_path / "keys.json"
    p.write_text(json.dumps(data))
    return str(p)


def test_keystore_merges_external_keyfile(tmp_path):
    from decrypt.keys import KeyStore

    new_tls_key = "TESTKEY_rotated_tls_build_9000_aGVsbG8="
    path = _write_keyfile(tmp_path, {"tls": [new_tls_key]})

    ks = KeyStore(path)

    # The extracted key is present AND the built-in default is retained.
    assert new_tls_key in ks.tls
    assert "VCTCp8KqOl7CumzMicS4w77ihpPFi8Wn4oCdw6bCtHM=" in ks.tls


def test_get_router_reads_injectx_keyfile_env(monkeypatch, tmp_path):
    new_aot_key = "TESTKEY_rotated_hat_key_MTIzNDU2Nzg5MA=="
    path = _write_keyfile(tmp_path, {"aot": [new_aot_key]})
    monkeypatch.setenv("INJECTX_KEYFILE", path)

    # Reset the module-level singleton so get_router rebuilds with the env.
    router_mod = importlib.import_module("decrypt.router")
    router_mod._router = None

    router = router_mod.get_router()
    assert new_aot_key in router.keys.aot

    # Clean up the singleton so other tests get the default keystore.
    router_mod._router = None
