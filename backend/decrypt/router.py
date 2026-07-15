"""
InjectX — Scheme Router

The scheme router decouples format detection from crypto logic.

Flow:
  parser → extract encrypted blob → router.dispatch(format, raw_bytes)
         → router tries all applicable schemes → returns DecryptedPayload(max_confidence)

This replaces the old pattern of:
  hc_parser → hc_decrypt (hardcoded coupling)

With:
  hc_parser → router.dispatch("hc", raw_bytes) → DecryptedPayload

Adding a new key or scheme never requires touching a parser.
"""

from __future__ import annotations

import os
import time
from typing import Optional

from ir.models import (
    DecryptedPayload,
    DecryptAttempt,
    DecryptStatusEnum,
    DecryptTrace,
    FormatEnum,
    SchemeEnum,
)
from .keys import KeyStore
from .hc_decrypt import decrypt_hc
from .hc_v27_decrypt import decrypt_hc_v27
from .ehi_decrypt import decrypt_ehi
from .ehi_v2_decrypt import decrypt_ehi_v2
from .npv_decrypt import decrypt_npv
from .nsh_decrypt import decrypt_nsh
from .hat_decrypt import decrypt_hat
from .tls_decrypt import decrypt_tls
from .vhd_decrypt import decrypt_vhd
from .ziv_decrypt import decrypt_ziv
from .dark_decrypt import decrypt_dark


# ── Format → Applicable Schemes mapping ───────────────────────────────────────

FORMAT_SCHEMES: dict[FormatEnum, list[SchemeEnum]] = {
    # HC: try newest scheme first (v2.7+ ChaCha20), then legacy A1-A4
    FormatEnum.HC:  [SchemeEnum.A5, SchemeEnum.A1, SchemeEnum.A2, SchemeEnum.A3, SchemeEnum.A4],
    # EHI: try newest scheme first (v2 Argon2+ChaCha20), then legacy B1
    FormatEnum.EHI: [SchemeEnum.B2, SchemeEnum.B1],
    FormatEnum.NPV: [SchemeEnum.C1],
    FormatEnum.NSH: [SchemeEnum.D1],
    FormatEnum.HAT: [SchemeEnum.E1],
    FormatEnum.TLS: [SchemeEnum.F1],
    FormatEnum.VHD: [SchemeEnum.G1],
    FormatEnum.ZIV: [SchemeEnum.H1],
    # DARK: outer darktunnel:// base64(JSON) envelope is plaintext (I1);
    # the inner encryptedLockedConfig blob stays locked (no key in file).
    FormatEnum.DARK: [SchemeEnum.I1],
    FormatEnum.DARKTUNNEL: [SchemeEnum.I1],
    FormatEnum.LNK: [],            # No public decryptor (format recognized, payload encrypted)
    FormatEnum.OVPN: [],           # Plain text
    FormatEnum.CONF: [],           # Plain text
    FormatEnum.ENCRYPTED_UNKNOWN: [],
    FormatEnum.UNKNOWN: [],
}


class SchemeRouter:
    """
    Crypto router: dispatches encrypted blobs to the correct decryptor(s)
    and returns the highest-confidence result.

    Architecture invariant:
      - Parsers NEVER call decryptors directly
      - Parsers call router.dispatch(format, raw_bytes)
      - Router returns DecryptedPayload with confidence scoring
    """

    def __init__(self, key_store: Optional[KeyStore] = None):
        self.keys = key_store or KeyStore()

    def dispatch(
        self,
        format: FormatEnum,
        raw: bytes,
        filepath: str = "",
        filename: str = "",
    ) -> DecryptedPayload:
        """
        Try all applicable schemes for the given format.
        Returns the DecryptedPayload with the highest confidence score.

        If no schemes apply (plain text or no decryptor), returns
        a DecryptedPayload with appropriate status.
        """
        schemes = FORMAT_SCHEMES.get(format, [])
        trace = DecryptTrace(
            filepath=filepath,
            filename=filename,
            format=format,
        )

        # No schemes → no decryptor or not encrypted
        if not schemes:
            if format in (FormatEnum.DARK, FormatEnum.ENCRYPTED_UNKNOWN):
                return DecryptedPayload(
                    scheme=SchemeEnum.UNSUPPORTED,
                    confidence=0.0,
                    status=DecryptStatusEnum.NO_DECRYPTOR,
                    trace=trace,
                )
            return DecryptedPayload(
                scheme=SchemeEnum.NONE,
                confidence=1.0,
                status=DecryptStatusEnum.NOT_ENCRYPTED,
                trace=trace,
            )

        # Try all applicable schemes, collect results
        candidates: list[DecryptedPayload] = []
        total_start = time.monotonic()

        for scheme in schemes:
            payload = self._try_scheme(scheme, format, raw, filepath, filename, trace)
            # Keep PARTIAL too: a partially-recovered payload (e.g. a DARK
            # envelope whose credential body is locked, or a low-confidence
            # TLS decode) still carries useful fields and must not be
            # dropped in favour of a bare FAILED result.
            if payload.status in (
                DecryptStatusEnum.SUCCESS,
                DecryptStatusEnum.PARTIAL,
            ) and payload.confidence > 0.0:
                candidates.append(payload)

        total_elapsed = (time.monotonic() - total_start) * 1000
        trace.total_elapsed_ms = total_elapsed

        # Select best candidate by confidence
        if candidates:
            best = max(candidates, key=lambda p: p.confidence)
            best.trace = trace
            return best

        # All schemes failed
        return DecryptedPayload(
            scheme=schemes[0] if schemes else SchemeEnum.UNSUPPORTED,
            confidence=0.0,
            status=DecryptStatusEnum.FAILED,
            trace=trace,
        )

    def _try_scheme(
        self,
        scheme: SchemeEnum,
        format: FormatEnum,
        raw: bytes,
        filepath: str,
        filename: str,
        trace: DecryptTrace,
    ) -> DecryptedPayload:
        """Dispatch to the correct decryptor function for the given scheme."""
        start = time.monotonic()

        try:
            # A-series: HTTP Custom
            if scheme == SchemeEnum.A5:
                # v2.7+ multi-layer — no keys needed (constants baked in)
                from audit.live_log import get_live_log
                result = decrypt_hc_v27(scheme, raw, trace, live_log=get_live_log())
            elif scheme in (SchemeEnum.A1, SchemeEnum.A2, SchemeEnum.A3, SchemeEnum.A4):
                result = decrypt_hc(scheme, raw, self.keys, trace)

            # B-series: HTTP Injector
            elif scheme == SchemeEnum.B2:
                # v2 (v6.3+) Argon2 + ChaCha20 — no keys needed
                from audit.live_log import get_live_log
                result = decrypt_ehi_v2(scheme, raw, trace, live_log=get_live_log())
            elif scheme == SchemeEnum.B1:
                result = decrypt_ehi(scheme, raw, self.keys, trace)

            # C-series: NapsternetV
            elif scheme == SchemeEnum.C1:
                result = decrypt_npv(scheme, raw, self.keys, trace)

            # D-series: SocksHTTP
            elif scheme == SchemeEnum.D1:
                result = decrypt_nsh(scheme, raw, self.keys, trace)

            # E-series: HA Tunnel
            elif scheme == SchemeEnum.E1:
                result = decrypt_hat(scheme, raw, self.keys, trace)

            # F-series: TLS Tunnel
            elif scheme == SchemeEnum.F1:
                result = decrypt_tls(scheme, raw, self.keys, trace)

            # G-series: VHD
            elif scheme == SchemeEnum.G1:
                result = decrypt_vhd(scheme, raw, self.keys, trace)

            # H-series: ZIVPN
            elif scheme == SchemeEnum.H1:
                from audit.live_log import get_live_log
                result = decrypt_ziv(scheme, raw, trace, live_log=get_live_log())

            # I-series: DARK Tunnel
            elif scheme == SchemeEnum.I1:
                from audit.live_log import get_live_log
                result = decrypt_dark(scheme, raw, trace, live_log=get_live_log())

            else:
                result = DecryptedPayload(
                    scheme=scheme,
                    confidence=0.0,
                    status=DecryptStatusEnum.NO_DECRYPTOR,
                )

        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            trace.add_attempt(DecryptAttempt(
                scheme=scheme,
                result="error",
                confidence=0.0,
                error_message=str(e),
                elapsed_ms=elapsed,
            ))
            result = DecryptedPayload(
                scheme=scheme,
                confidence=0.0,
                status=DecryptStatusEnum.FAILED,
            )

        return result


# ── Singleton Router ──────────────────────────────────────────────────────────

_router: Optional[SchemeRouter] = None


def get_router(keyfile_path: Optional[str] = None) -> SchemeRouter:
    """Get or create the singleton SchemeRouter instance.

    If no keyfile path is passed explicitly, fall back to the
    ``INJECTX_KEYFILE`` environment variable. This is how freshly
    extracted keys reach the decryptors without a code change: point
    ``INJECTX_KEYFILE`` at a JSON file whose top-level keys match the
    KeyStore categories (e.g. ``{"tls": ["<base64-key>"], "aot": [...]}``)
    and they are merged over the built-in defaults. When the app authors
    rotate a key, drop the new one in that file — no rebuild needed.
    """
    global _router
    if _router is None:
        if keyfile_path is None:
            keyfile_path = os.environ.get("INJECTX_KEYFILE") or None
        _router = SchemeRouter(KeyStore(keyfile_path))
    return _router
