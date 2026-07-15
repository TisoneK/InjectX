"""DARK Tunnel envelope decode (scheme I1).

Prior sessions treated .dark as "proprietary, no decryptor." In fact the
outer darktunnel://base64(JSON) envelope is plaintext and exposes type +
name; only the optional encryptedLockedConfig blob is sealed. These
tests pin that behaviour against the bundled samples.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ir.models import DecryptStatusEnum, ProtocolEnum, SchemeEnum  # noqa: E402
from parser.parse_engine import parse_config  # noqa: E402

DARK_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "configs" / "dark"
DARK_SAMPLES = sorted(DARK_DIR.glob("*.dark")) if DARK_DIR.exists() else []


@pytest.mark.skipif(not DARK_SAMPLES, reason="no .dark samples bundled")
@pytest.mark.parametrize("sample", DARK_SAMPLES, ids=lambda p: p.name)
def test_dark_envelope_decodes(sample):
    nc = parse_config(str(sample))

    # Envelope decoded via scheme I1 (not the old NO_DECRYPTOR path).
    assert nc.scheme_used == SchemeEnum.I1.value
    # type -> a recognised protocol (these samples are VLESS/VMESS/TROJAN).
    assert nc.protocol in {
        ProtocolEnum.VLESS.value,
        ProtocolEnum.VMESS.value,
        ProtocolEnum.TROJAN.value,
    }
    # name always survives the envelope decode.
    assert nc.raw_data and nc.raw_data.get("name")


@pytest.mark.skipif(not DARK_SAMPLES, reason="no .dark samples bundled")
def test_dark_locked_config_is_partial(sample=None):
    # All bundled samples are author-locked -> PARTIAL, with a warning.
    nc = parse_config(str(DARK_SAMPLES[0]))
    assert nc.decryption_status == DecryptStatusEnum.PARTIAL.value
    assert nc.raw_data.get("locked") is True
    assert any("LOCKED" in w for w in nc.warnings)
