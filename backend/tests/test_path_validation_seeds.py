"""Regression tests for `_validate_seedlist_path` — the API-boundary guard for
/api/sni/scan seedlist paths. Extends the test_path_validation.py pattern with
the seedlist extension set (.txt/.csv/.json) and the 5 MiB cap.

The critical case is the same symlink bypass ADR-5 fixed for config paths: a
`.txt` symlink pointing at a disallowed target must be rejected on the RESOLVED
extension, not the link's name.
"""

from pathlib import Path
import importlib
import sys

import pytest


def _load_main(tmp_path, monkeypatch):
    monkeypatch.setenv("INJECTX_UPLOAD_DIR", str(tmp_path / "uploads"))
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    sys.modules.pop("main", None)
    return importlib.import_module("main")


def _raises_status(main, filepath, status):
    with pytest.raises(main.HTTPException) as exc:
        main._validate_seedlist_path(filepath)
    assert exc.value.status_code == status


def test_accepts_plain_txt(tmp_path, monkeypatch):
    main = _load_main(tmp_path, monkeypatch)
    p = tmp_path / "hosts.txt"
    p.write_text("example.com\n")
    assert main._validate_seedlist_path(str(p)) == p.resolve()


def test_rejects_config_extension(tmp_path, monkeypatch):
    # A config extension is NOT a seedlist extension — must be rejected.
    main = _load_main(tmp_path, monkeypatch)
    p = tmp_path / "x.ehi"
    p.write_bytes(b"PK\x03\x04")
    _raises_status(main, str(p), 400)


def test_rejects_relative_path(tmp_path, monkeypatch):
    main = _load_main(tmp_path, monkeypatch)
    _raises_status(main, "hosts.txt", 400)


def test_rejects_missing_file(tmp_path, monkeypatch):
    main = _load_main(tmp_path, monkeypatch)
    _raises_status(main, str(tmp_path / "nope.txt"), 404)


def test_rejects_symlink_to_disallowed_target(tmp_path, monkeypatch):
    main = _load_main(tmp_path, monkeypatch)
    secret = tmp_path / "secret.ehi"
    secret.write_bytes(b"PK\x03\x04")
    link = tmp_path / "evil.txt"
    link.symlink_to(secret)
    _raises_status(main, str(link), 400)


def test_rejects_empty_seedlist(tmp_path, monkeypatch):
    main = _load_main(tmp_path, monkeypatch)
    p = tmp_path / "empty.txt"
    p.write_text("")
    _raises_status(main, str(p), 400)


def test_rejects_oversize_seedlist(tmp_path, monkeypatch):
    main = _load_main(tmp_path, monkeypatch)
    p = tmp_path / "big.txt"
    p.write_bytes(b"a.com\n" * (main.MAX_SEEDLIST_BYTES // 6 + 10))
    _raises_status(main, str(p), 413)
