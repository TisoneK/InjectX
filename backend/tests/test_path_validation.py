"""Regression tests for `_validate_config_path` — the API-boundary guard that
keeps `/api/config/parse` and `/api/config/detect` from becoming an
arbitrary-file-read oracle.

The critical case is the symlink bypass: a link named `x.ehi` pointing at a
file with a disallowed extension (`/etc/passwd`) must be rejected, because the
resolved target — not the link's name — decides whether the read is allowed.
"""

from pathlib import Path
import importlib
import sys

import pytest


def _load_main(tmp_path, monkeypatch):
    # Isolate UPLOAD_DIR so importing main doesn't touch the real ~/.injectx.
    monkeypatch.setenv("INJECTX_UPLOAD_DIR", str(tmp_path / "uploads"))
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    sys.modules.pop("main", None)
    return importlib.import_module("main")


def _raises_status(main, filepath, status):
    with pytest.raises(main.HTTPException) as exc:
        main._validate_config_path(filepath)
    assert exc.value.status_code == status


def test_rejects_disallowed_extension(tmp_path, monkeypatch):
    main = _load_main(tmp_path, monkeypatch)
    passwd = tmp_path / "secret.txt"
    passwd.write_text("root:x:0:0")
    _raises_status(main, str(passwd), 400)


def test_rejects_relative_path(tmp_path, monkeypatch):
    main = _load_main(tmp_path, monkeypatch)
    _raises_status(main, "foo.ehi", 400)


def test_rejects_empty_path(tmp_path, monkeypatch):
    main = _load_main(tmp_path, monkeypatch)
    _raises_status(main, "", 400)


def test_rejects_missing_file(tmp_path, monkeypatch):
    main = _load_main(tmp_path, monkeypatch)
    _raises_status(main, str(tmp_path / "nope.ehi"), 404)


def test_rejects_symlink_to_disallowed_target(tmp_path, monkeypatch):
    """The core bypass: a .ehi symlink pointing at a non-config file."""
    main = _load_main(tmp_path, monkeypatch)
    secret = tmp_path / "secret.txt"
    secret.write_text("root:x:0:0")
    link = tmp_path / "evil.ehi"
    link.symlink_to(secret)
    _raises_status(main, str(link), 400)


def test_accepts_symlink_to_allowed_target(tmp_path, monkeypatch):
    """A legitimate same-extension symlink must still resolve and pass."""
    main = _load_main(tmp_path, monkeypatch)
    real = tmp_path / "real.ehi"
    real.write_bytes(b"PK\x03\x04dummy")
    link = tmp_path / "link.ehi"
    link.symlink_to(real)
    resolved = main._validate_config_path(str(link))
    assert resolved == real.resolve()


def test_accepts_plain_allowed_file(tmp_path, monkeypatch):
    main = _load_main(tmp_path, monkeypatch)
    cfg = tmp_path / "config.ehi"
    cfg.write_bytes(b"PK\x03\x04dummy")
    resolved = main._validate_config_path(str(cfg))
    assert resolved == cfg.resolve()


def test_rejects_empty_allowed_file(tmp_path, monkeypatch):
    main = _load_main(tmp_path, monkeypatch)
    cfg = tmp_path / "empty.ehi"
    cfg.write_bytes(b"")
    _raises_status(main, str(cfg), 400)
