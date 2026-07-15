"""
InjectX — Intermediate Representation (IR) Package

The IR is the versioned contract between the crypto layer, the parser layer,
and the UI layer. Every component produces or consumes IR objects — never raw dicts.

Architecture invariant:
  detector → IR(DetectResult)
  decryptor → IR(DecryptedPayload)
  parser → IR(NormalizedConfig)
  API → IR as JSON
"""

from .models import (
    IR_VERSION,
    DetectResult,
    DecryptedPayload,
    DecryptAttempt,
    DecryptTrace,
    NormalizedConfig,
    FormatEnum,
    ProtocolEnum,
    DecryptStatusEnum,
    SchemeEnum,
)

__all__ = [
    "IR_VERSION",
    "DetectResult",
    "DecryptedPayload",
    "DecryptAttempt",
    "DecryptTrace",
    "NormalizedConfig",
    "FormatEnum",
    "ProtocolEnum",
    "DecryptStatusEnum",
    "SchemeEnum",
]
