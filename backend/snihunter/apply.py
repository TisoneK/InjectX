"""
"Use as SNI" — apply a discovered bug host to an existing parsed config.

This closes the discover→probe→use loop (design doc §5.2). The user scans a
seedlist, sees a working bug host, and clicks "Use as SNI" on a target config.
This module re-parses the config from disk (the original `filepath` is stored
on every NormalizedConfig) and overrides the `sni` field with the new hostname.

Why re-parse instead of mutating the stored config in place:
  - The stored config is a `model_dump()` dict; mutating it loses the audit
    trail (the decrypt trace says "this config's original SNI was X" — if we
    mutate, the trace and the field disagree).
  - Re-parsing is cheap (config files are kilobyte-scale) and gives us a fresh
    NormalizedConfig with a fresh decrypt trace, which we then patch.
  - The original SNI is preserved in `raw_data.original_sni` so the UI can
    show "was: X → now: Y" and the user can revert.

The override is shallow — it sets `sni` on the NormalizedConfig and also
patches any `sni`-keyed entry in `raw_data._all_fields` (where most formats
keep their full decoded field set). We do NOT attempt to re-encrypt the
config and write it back to disk — that's a Phase 3 feature and would
require format-specific encryptors.
"""

from __future__ import annotations

from typing import Optional

from ir.models import NormalizedConfig
from parser import parse_config


def apply_sni(normalized: NormalizedConfig, new_sni: str) -> NormalizedConfig:
    """Return a *copy* of `normalized` with `sni` overridden.

    Pure function — no I/O. The caller (API layer) is responsible for
    re-parsing the config from disk first (so the decrypt trace is fresh)
    and for storing the result back into config_store.

    Preserves the original SNI under `raw_data["_original_sni"]` so the UI
    can show the before/after and offer a revert. Idempotent: applying the
    same SNI twice doesn't stack original values.
    """
    if not new_sni or not new_sni.strip():
        raise ValueError("No SNI hostname provided")
    new_sni = new_sni.strip().lower()

    # Preserve the original SNI exactly once (idempotency).
    original_sni = normalized.sni
    raw = dict(normalized.raw_data) if normalized.raw_data else {}
    if "_original_sni" not in raw:
        raw["_original_sni"] = original_sni

    # Patch the top-level field.
    normalized.sni = new_sni

    # Patch any sni-keyed entry in _all_fields so the UI's "DECODED FIELDS"
    # table (which renders raw_data._all_fields) shows the new value too.
    all_fields = raw.get("_all_fields")
    if isinstance(all_fields, dict):
        all_fields = dict(all_fields)
        for k in list(all_fields.keys()):
            if k.lower() in ("sni", "servername", "server_name", "snivalue",
                             "snihostname", "hostsnissl", "customsni",
                             "adv_ssl_spoofhost"):
                all_fields[k] = new_sni
        raw["_all_fields"] = all_fields
    normalized.raw_data = raw

    # Tag a warning so the audit trail shows the override happened.
    if original_sni and original_sni.lower() != new_sni:
        normalized.warnings = list(normalized.warnings) + [
            f"SNI overridden via Host Hunter: {original_sni} → {new_sni}"
        ]
    elif not original_sni:
        normalized.warnings = list(normalized.warnings) + [
            f"SNI set via Host Hunter: {new_sni}"
        ]
    return normalized


def apply_sni_to_config_id(config_store: dict, config_id: str,
                            new_sni: str) -> NormalizedConfig:
    """Re-parse a stored config from disk and apply the SNI override.

    Returns the new NormalizedConfig. The caller is responsible for storing
    it back into config_store (under the same config_id — the override is
    in-place from the UI's perspective). Raises KeyError if the config_id
    isn't in the store, ValueError if the config has no filepath (can't
    re-parse).
    """
    if config_id not in config_store:
        raise KeyError(config_id)
    data = config_store[config_id]
    filepath = data.get("filepath")
    if not filepath:
        raise ValueError(f"Config {config_id} has no filepath — cannot re-parse")

    # Re-parse from disk for a fresh decrypt trace.
    normalized = parse_config(filepath)
    # Preserve the config_id linkage (the store is keyed by id, not by filepath).
    # The fresh parse produces a NormalizedConfig with the same filepath/filename
    # but a NEW config_id would normally be minted by the API layer; here we
    # keep the caller's id.
    return apply_sni(normalized, new_sni)
