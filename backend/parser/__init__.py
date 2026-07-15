"""
InjectX — Universal VPN Config Parser v0.4

Architecture: Detector → Scheme Router → Decryptor → Parser → NormalizedConfig IR

Key changes from v0.3:
  - Parsers no longer call decryptors directly — they use the Scheme Router
  - All output is versioned IR (NormalizedConfig with ir_version)
  - Detection uses multi-feature classifier (not just entropy)
  - Decryption uses confidence-based selection (not first-JSON-wins)
  - Full audit trail of all decrypt attempts
"""

from .detector import detect_format, detect_with_features
from .parse_engine import parse_config

__all__ = [
    "detect_format",
    "detect_with_features",
    "parse_config",
]
