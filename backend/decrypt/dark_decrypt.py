"""
InjectX — DARK Tunnel (.dark) decoding (Scheme I1)

Prior sessions recorded DARK as "proprietary encryption, no public
decryptor." That is wrong for the outer envelope: a .dark file is

    darktunnel://<base64(JSON)>

where the JSON is plaintext. It exposes at least ``type`` (VLESS / VMESS
/ TROJAN / SSH / …) and ``name``, and — when the author did NOT lock the
config — the full server/credential fields directly.

What IS encrypted is the optional ``encryptedLockedConfig`` field: DARK
Tunnel's "locked config" DRM. The author locks a config so a recipient
can import and use it but cannot read or re-share the underlying
server/credentials. That blob is URL-safe-base64 over ~3 KB of
high-entropy ciphertext with a key that is not in the file (device- or
server-bound), so it is not recoverable here — the same "no key, no
plaintext" wall as a rotated AES key.

So scheme I1 decodes everything the file actually exposes and reports
whether the credential body is locked:
  - locked (``encryptedLockedConfig`` present)  → status PARTIAL
  - unlocked (server fields present in the JSON) → status SUCCESS
"""

from __future__ import annotations

import base64
import binascii
import json
import time

from ir.models import (
    DecryptedPayload,
    DecryptAttempt,
    DecryptStatusEnum,
    DecryptTrace,
    SchemeEnum,
)

_SCHEME_PREFIXES = ("darktunnel://", "dark://", "dt://")


def _b64_tolerant(s: str) -> bytes:
    """Decode base64 that may use the URL-safe alphabet and drop padding."""
    s = s.strip().replace("-", "+").replace("_", "/")
    s += "=" * ((-len(s)) % 4)
    return base64.b64decode(s)


def decrypt_dark(
    scheme: SchemeEnum,
    raw: bytes,
    trace: DecryptTrace,
    live_log=None,
) -> DecryptedPayload:
    """Decode a DARK Tunnel .dark envelope (scheme I1)."""
    start = time.monotonic()

    def _fail(msg: str) -> DecryptedPayload:
        trace.add_attempt(DecryptAttempt(
            scheme=SchemeEnum.I1,
            key_label="dark_envelope",
            result="fail",
            confidence=0.0,
            elapsed_ms=(time.monotonic() - start) * 1000,
            error_message=msg,
        ))
        if live_log:
            live_log.add("DARK", msg, "warn")
        return DecryptedPayload(
            scheme=SchemeEnum.I1,
            confidence=0.0,
            status=DecryptStatusEnum.FAILED,
        )

    try:
        content = raw.decode("utf-8", errors="strict").strip()
    except UnicodeDecodeError:
        return _fail("File is not UTF-8 text (not a darktunnel:// envelope)")

    body = content
    for prefix in _SCHEME_PREFIXES:
        if body.startswith(prefix):
            body = body[len(prefix):]
            break
    else:
        # No known scheme prefix — the JSON may still be raw or base64.
        pass

    if live_log:
        live_log.add("DARK", "Decoding darktunnel:// base64 envelope…", "info")

    data = None
    try:
        data = json.loads(_b64_tolerant(body))
    except (binascii.Error, ValueError):
        # Fall back to plain JSON (some exports aren't base64-wrapped).
        try:
            data = json.loads(content)
        except ValueError:
            return _fail("Envelope is neither base64(JSON) nor plain JSON")

    if not isinstance(data, dict):
        return _fail("Decoded envelope is not a JSON object")

    locked = bool(data.get("encryptedLockedConfig"))
    # Confidence: we fully decoded the envelope. Cap below 1.0 when the
    # credential body is locked, since the useful config stays sealed.
    confidence = 0.5 if locked else 0.9
    status = DecryptStatusEnum.PARTIAL if locked else DecryptStatusEnum.SUCCESS

    trace.add_attempt(DecryptAttempt(
        scheme=SchemeEnum.I1,
        key_label="dark_envelope",
        result="success",
        confidence=confidence,
        elapsed_ms=(time.monotonic() - start) * 1000,
    ))
    if live_log:
        kind = "locked (credentials sealed)" if locked else "unlocked"
        live_log.add("DARK", f"Envelope decoded · type={data.get('type')} · {kind}", "info")

    return DecryptedPayload(
        scheme=SchemeEnum.I1,
        confidence=confidence,
        status=status,
        json_data=data,
        key_label="dark_envelope",
    )
