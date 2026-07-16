"""ZIVPN (.ziv) decryption (scheme H1).

The current password was extracted from ZIVPN Tunnel v2.1.5 (class o3.a:
concatenated 'SecurePart1'..'SecurePart5', PBKDF2-SHA256 1000 iters,
AES-128-GCM over salt.iv.ct). These tests pin that the bundled samples
decode and that the ZIVPN UDP-mode server surfaces as host.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ir.models import DecryptStatusEnum, SchemeEnum  # noqa: E402
from parser.parse_engine import parse_config  # noqa: E402

ZIV_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "configs" / "ziv"
ZIV_SAMPLES = sorted(ZIV_DIR.glob("*.ziv")) if ZIV_DIR.exists() else []


@pytest.mark.skipif(not ZIV_SAMPLES, reason="no .ziv samples bundled")
@pytest.mark.parametrize("sample", ZIV_SAMPLES, ids=lambda p: p.name)
def test_ziv_sample_decrypts(sample):
    nc = parse_config(str(sample))
    assert nc.decryption_status == DecryptStatusEnum.SUCCESS.value
    assert nc.scheme_used == SchemeEnum.H1.value
    # These bundled samples are ZIVPN UDP-mode configs -> server as host.
    assert nc.host and "zivpn.com" in nc.host
