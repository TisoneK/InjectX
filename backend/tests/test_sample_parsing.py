"""Happy-path smoke tests over the real sample configs in assets/configs/**.

These exercise the full detect -> route -> decrypt -> normalize pipeline
against the actual files the project ships (13 HC, 6 EHI, 6 ZIV, 4 DARK,
2 TLS at the time of writing). They do NOT assert decryption success — some
formats' keys have been rotated in newer app builds (TLS/ZIV) or have no
public decryptor (DARK), so a "locked" result is a valid outcome. What they
DO assert is the contract every parser must honour regardless of decrypt
result:

  * `parse_config` returns a `NormalizedConfig` and never raises on a
    real, well-formed sample.
  * The detected `format` matches the file's extension (the primary
    detection signal), so a mis-registered extension map is caught.
  * `filename` survives normalization — format-specific normalizers build
    a fresh IR object with an empty filename, and `parse_config` restores
    it. Session 7 shipped a regression where this was blanked; this guards
    against a repeat.

This is the per-format coverage backlog item N3 asked for. Add a new
format's samples under assets/configs/<fmt>/ and they are picked up here
automatically.
"""

from pathlib import Path
import sys

import pytest

# Match the sys.path shim the other backend tests use so `parser`/`ir`
# import whether pytest is run from backend/ or the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from parser import parse_config  # noqa: E402
from parser.detector import EXTENSION_MAP  # noqa: E402
from ir.models import NormalizedConfig  # noqa: E402

ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "configs"

_SKIP_NAMES = {".gitkeep", "README.md"}


def _sample_files() -> list[Path]:
    if not ASSETS_DIR.exists():
        return []
    files = []
    for path in sorted(ASSETS_DIR.rglob("*")):
        if not path.is_file() or path.name in _SKIP_NAMES:
            continue
        if path.suffix.lower() not in EXTENSION_MAP:
            continue
        files.append(path)
    return files


_SAMPLES = _sample_files()


@pytest.mark.skipif(not _SAMPLES, reason="no sample configs under assets/configs/")
@pytest.mark.parametrize("sample", _SAMPLES, ids=lambda p: str(p.relative_to(ASSETS_DIR)))
def test_sample_parses_without_error(sample: Path):
    """Every shipped sample parses to a NormalizedConfig with the right format."""
    result = parse_config(str(sample))

    assert isinstance(result, NormalizedConfig)

    expected = EXTENSION_MAP[sample.suffix.lower()]
    fmt = result.format if isinstance(result.format, str) else result.format.value
    expected_val = expected if isinstance(expected, str) else expected.value
    assert fmt == expected_val, (
        f"{sample.name}: detected {fmt!r}, expected {expected_val!r} from extension"
    )

    # Filename must survive normalization (guards the Session 7 regression
    # where format-specific normalizers blanked it).
    assert result.filename == sample.name


def test_at_least_one_sample_per_present_format():
    """Sanity check that the sample tree still covers the formats it did.

    Not every format has samples, but the ones with a subdirectory of
    files should each contribute at least one parametrized case above —
    this catches an accidental wipe of the assets tree.
    """
    if not _SAMPLES:
        pytest.skip("no sample configs under assets/configs/")
    formats = {
        (EXTENSION_MAP[p.suffix.lower()]) for p in _SAMPLES
    }
    assert len(formats) >= 2, "expected samples spanning multiple formats"
