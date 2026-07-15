"""
InjectX — Decryption Package

The decrypt package implements the Scheme Router pattern:
  format → extractor → encrypted_blob → scheme_router → decryptor → DecryptedPayload

This decouples format-specific parsing from crypto logic.
Adding a new key or scheme never requires touching a parser.
"""

from .router import SchemeRouter, get_router
from .keys import KeyStore

__all__ = [
    "SchemeRouter",
    "get_router",
    "KeyStore",
]
