"""
InjectX — Encryption Key Store

Centralizes ALL encryption keys for ALL formats.
This is the single source of truth — parsers and decryptors never hardcode keys.

Key source: Pancho7532/HCDecryptor cfg/keyFile.json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


# ── Default keys (from Pancho7532/HCDecryptor keyFile.json) ───────────────────

_DEFAULT_KEYS: dict = {
    "ePro": [
        [
            "ApkCusT0m_K3y",
            "d3V-3Pr0-T34m",
            "d3V-3Pr0-T3@M",
            "d3V:3Pr0@T3@M",
            "d3V:3Pr0:T3@M",
            "d3V:3Pr0-T3@M",
            "d3V^3Pr0-T3@M",
            "d3V(3Pr0-T3@M",
            "d3V(3Pr0)T3@M",
            "d3V-3Pr0_T3@M",
            "d3V-ePr0_T3@M",
            "d3V-ePr0_t3@M",
            "d3v-ePr0_t3@M",
            "d3v-ePr0-t34M",
            "d3v_ePr0_t34M",
            "d3v_ePr0_t3aM",
            "d3v_ePr0_t3am",
            "d3v_ePr0_bl4th",
            "no1_ePr0_bl4th",
            "keY_secReaT_hc_reborn",
            "keY_secReaT_hc_reborn1",
            "keY_secReaT_hc_reborn2",
            "keY_secReaT_hc_reborn3",
            "keY_secReaT_hc_reborn4",
            "keY_secReaT_hc_reborn5",
            "keY_secReaT_hc_reborn6",
            "keY_secReaT_hc",
            "keY_secReaT_hc1",
            "keY_secReaT_hc2",
            "keY_secReaT_hc_2",
            "hc_reborn7",
            "hc_reborn8",
            "hc_reborn9",
            "hc_reborn10",
            "keY_secReaT_te4",
            "keY_secReaT_te4Z",
            "keY_secReaT_te4Z9",
            "keY_secReaT_te4Z10",
            "keY_secReaT_te4Z11",
            "keY_secReaT_te54",
            "s3cr3T_k3Y_ePro",
            "s3cr3T_k3Y_ePr0_3NcRypT",
            "s3cr3T_k3y_ePr0_3NcRypT",
            "keY_secReaT_e",
            "keY_secReaT_ePr0",
            "keY_secReaT_ePr1",
            "keY_secReaT_ePr2",
            "keY_secReaT_ePr3",
            "keY_secReaT_ePr4",
            "hc_reborn_1",
            "hc_reborn_2",
            "hc_reborn_3",
            "hc_reborn_4",
            "hc_reborn_5",
            "hc_reborn_6",
            "hc_reborn_7",
            "hc_reborn_8",
            "hc_reborn_9",
            "hc_reborn_10",
            "hc_reborn___7",
            "hc_reborn_tester",
            "hc_reborn_tester_1",
            "hc_reborn_tester_2",
            "hc_reborn_tester_3",
            "hc_reborn_tester_4",
            "hc_reborn_tester_5",
            "hc_reborn_tester_6",
            "hc_reborn_tester_7",
            "hc_reborn_tester_8",
            "hc_reborn_tester_9",
            "hc_reborn_for_you",
            "hc_easypro_7",
            "hc35_easypro_8",
            "hc37_easypro@2020",
            "hc38_345yPr0@2020",
        ],
        [
            "HTTP_Custom_v233_hc_easypro_7",
            "HTTP_Custom_v233_hc35_easypro_8",
        ],
    ],
    "evozi": [
        [
            "fhIQ96q5VvemaL2m5X/t23+ErYQK740nsblplZvjq2w=",
            "Rnjg9Slfyas+na8yGwiXx40EXr+VIZUUz+9XD0koGBE=",
            "MiUQFV2nMl1kTKbmt9+LgO0gww7ZMuzLn+fisEz4+KQ=",
        ],
        [
            "c9zx/b+CUJBk4ACkHUlMAQ==",
            "Igeltafe0t7U6xfOkcmCZg==",
        ],
        [
            "CFHSIHTTPINISSCF",
            "V5HSIHTTPINISS20",
            "V5HSIHTTPINISS21",
            "SBHSIHTTPINISSLS",
            "OBHSIHTTPINIOCTO",
            "AYJZIHTTPINIECKC",
            "SBHSIHTTPINILITE",
        ],
    ],
    "slipk": [
        "dyv35182!",
        "dyv35224nossas!!",
        "fubgf777gf6",
        "fubvx788b46v",
        "fubvx788b46vcatsn",
        "fubvx788B4mev",
        "$$$@mfube11!!_$$))012b4u",
        "xcode788b46z",
        "chanika acid, gimsara htpcag!!",
    ],
    "tls": [
        "VCTCp8KqOl7CumzMicS4w77ihpPFi8Wn4oCdw6bCtHM=",
    ],
    "sip": [
        "GS4ECAgEBAkFWSlZOF9UFw==",
    ],
    "aot": [
        "zbNkuNCGSLivpEuep3BcNA==",
        "Js09DrhnszTmIZeCGM6fxg==",
    ],
    "npv2": [
        "@))$@)))0.6931471805599453",
    ],
    "vhd": [
        ["vmmEncryptionKey"],
        ["vmmV2RayInt36489"],
    ],
}


class KeyStore:
    """
    Centralized key store for all encryption keys.

    Keys can be loaded from:
    1. Built-in defaults (from Pancho7532 research)
    2. External JSON keyfile (for user-supplied keys)
    3. Runtime additions via add_key()
    """

    def __init__(self, keyfile_path: Optional[str] = None):
        self._keys: dict = dict(_DEFAULT_KEYS)
        if keyfile_path:
            self._load_keyfile(keyfile_path)

    def _load_keyfile(self, path: str) -> None:
        """Load keys from an external JSON keyfile, merging with defaults."""
        p = Path(path)
        if not p.exists():
            return
        try:
            with open(p, "r") as f:
                external = json.load(f)
            for category, keys in external.items():
                if category in self._keys:
                    if isinstance(self._keys[category], list) and isinstance(keys, list):
                        # Merge, avoiding duplicates
                        existing = set(str(k) for k in self._keys[category])
                        for k in keys:
                            if str(k) not in existing:
                                self._keys[category].append(k)
                else:
                    self._keys[category] = keys
        except Exception:
            pass

    # ── Accessors by format ────────────────────────────────────────────────

    @property
    def epro(self) -> list[list[str]]:
        """HTTP Custom / eProxy keys. [0]=standard keys, [1]=v233 keys."""
        return self._keys.get("ePro", [[], []])

    @property
    def evozi(self) -> list[list[str]]:
        """HTTP Injector keys. [0]=AES-256 keys, [1]=AES-128 keys, [2]=IVs."""
        return self._keys.get("evozi", [[], [], []])

    @property
    def slipk(self) -> list[str]:
        """SocksHTTP keys."""
        return self._keys.get("slipk", [])

    @property
    def tls(self) -> list[str]:
        """TLS Tunnel keys."""
        return self._keys.get("tls", [])

    @property
    def aot(self) -> list[str]:
        """HA Tunnel keys."""
        return self._keys.get("aot", [])

    @property
    def npv2(self) -> list[str]:
        """NapsternetV keys."""
        return self._keys.get("npv2", [])

    @property
    def vhd(self) -> list[list[str]]:
        """VHD keys. [0]=keys, [1]=IVs."""
        return self._keys.get("vhd", [[], []])

    @property
    def sip(self) -> list[str]:
        """SIP/Shadowsocks keys."""
        return self._keys.get("sip", [])

    def add_key(self, category: str, key: str) -> None:
        """Add a key to a category at runtime."""
        if category not in self._keys:
            self._keys[category] = []
        if isinstance(self._keys[category], list):
            self._keys[category].append(key)

    def get(self, category: str, default=None):
        """Generic getter."""
        return self._keys.get(category, default)
