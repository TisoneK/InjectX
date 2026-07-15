from pathlib import Path
import importlib
import sys


def test_backend_uses_environment_overrides(monkeypatch, tmp_path):
    monkeypatch.setenv("INJECTX_HOST", "0.0.0.0")
    monkeypatch.setenv("INJECTX_PORT", "9876")
    monkeypatch.setenv("INJECTX_UPLOAD_DIR", str(tmp_path / "uploads"))

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    sys.modules.pop("main", None)

    module = importlib.import_module("main")

    assert module.HOST == "0.0.0.0"
    assert module.PORT == 9876
    assert module.UPLOAD_DIR == tmp_path / "uploads"
    assert module.UPLOAD_DIR.exists()
