"""
ECH capability detection via DNS SVCB/HTTPS records (RFC 9848).

RFC 9848 ("Bootstrapping TLS Encrypted ClientHello with DNS") specifies that a
server advertises its ECH configuration by publishing a SVCB or HTTPS resource
record whose `ech=` service parameter carries a base64-encoded `ECHConfigList`.

For SNI Host Hunter, detecting ECH capability is a *negative signal* for bug-
host viability: an ECH-capable host hides its real SNI from the network path,
which means an ISP doing SNI-based zero-rating can't see the hostname it would
match against its whitelist — so the host is *less useful* as a bug host. We
flag ECH-capable hosts distinctly in the results (design doc §3.3, §5.2).

We use dnspython (added to requirements.txt in Phase 2) to query the HTTPS RR
asynchronously. dnspython 2.6+ has full SVCB/HTTPS RR support including the
`ech` SvcParamKey. The query falls back to the SVCB RR if HTTPS is empty.

This module is deliberately small and side-effect-free apart from DNS I/O, so
it can be unit-tested against fixture DNS responses with no network.
"""

from __future__ import annotations

import asyncio
import base64
from typing import Any, Optional

# dnspython is an optional-at-runtime dep so the rest of the package keeps
# working if it's not installed (e.g. someone runs only Phase 1 code paths).
# The import is deferred to first use so importing `dns_check` never crashes.
_dns: Any = None


def _dns_module() -> Any:
    """Lazy-load dnspython. Raises ImportError on first real use if absent."""
    global _dns
    if _dns is None:
        import dns.resolver  # noqa: F401  (the public surface)
        import dns.name
        import dns.rdatatype
        _dns = type("M", (), {"resolver": dns.resolver,
                              "name": dns.name,
                              "rdatatype": dns.rdatatype})
    return _dns


# An ECH config list is base64 of one or more ECHConfig structs. We don't need
# to parse the inner structure (RFC 9849 §4) — presence of a non-empty `ech=`
# value is enough to flag the host as ECH-capable for our purposes.
def _is_plausible_ech_value(raw: str) -> bool:
    """True if an `ech=` SvcParam value looks like a real ECHConfigList.

    Per RFC 9848 the value is base64url (without padding) of ECHConfigList.
    Empty string means "ECH config advertised but list is empty" — we treat
    that as *not* ECH-capable (the server is signalling it knows about ECH
    but has nothing to offer). A non-empty base64 string decodes to ≥ 5 bytes
    (the ECHConfig version + length + at least a config_id).
    """
    if not raw:
        return False
    cleaned = raw.strip().rstrip("=")
    if not cleaned:
        return False
    # Must be valid base64 (standard or url-safe) — validate=True rejects
    # garbage like "not-base64!@#" instead of silently dropping bad chars.
    for alphabet in (cleaned, cleaned.replace("-", "+").replace("_", "/")):
        # Re-pad to a multiple of 4 for strict decoding.
        padded = alphabet + "=" * (-len(alphabet) % 4)
        if not padded:
            continue
        try:
            decoded = base64.b64decode(padded, validate=True)
        except (ValueError, base64.binascii.Error):
            continue
        # ECHConfigList starts with 2-byte length, then ECHConfig(s).
        # Each ECHConfig starts with 1-byte version (0xfe for draft, 0x0
        # for RFC 9849), then 1-byte config_id, then 1-byte KEM, etc.
        # Anything ≥ 5 bytes is plausibly an ECHConfigList.
        if len(decoded) >= 5:
            return True
    return False


def extract_ech_config(https_records: list[Any]) -> Optional[str]:
    """Pull the raw `ech=` value out of a list of SVCB/HTTPS RR objects.

    Returns the first non-empty `ech` value found (as a base64 string), or
    None if no record advertises ECH. Pure function — no I/O — so it's
    unit-tested directly against synthetic RR-shaped objects (see
    test_dns_check.py).

    Handles three key shapes dnspython has used over versions:
      1. A `ParamKey` enum keyed dict — str(key) yields "5", but key.name
         yields "ECH". The value is an ECHParam object with a `.to_text()`
         method that returns the base64 string.
      2. A plain string key ("ech") — value is a base64 string.
      3. A case-variant string key ("ECH").
    """
    for rr in https_records:
        params = getattr(rr, "params", None) or {}
        for k, v in params.items():
            name = ""
            if hasattr(k, "name"):
                name = str(k.name).lower()        # ParamKey.ECH.name == "ECH"
            elif hasattr(k, "value") and str(k).isdigit():
                # ParamKey with numeric str() — try the enum's _name_map.
                # SvcParamKey.ECH.value == 5 per the IANA SVCB registry.
                try:
                    from dns.rdtypes.IN.SVCB import ParamKey  # type: ignore
                    if k == ParamKey.ECH:
                        name = "ech"
                except Exception:
                    pass
            else:
                name = str(k).lower()
            if name != "ech":
                continue
            val = v[0] if isinstance(v, (list, tuple)) and v else v
            # ECHParam object — call to_text() for the base64 string form.
            if hasattr(val, "to_text") and not isinstance(val, str):
                try:
                    val = val.to_text().strip().strip('"')
                except Exception:
                    continue
            if val and str(val).strip():
                return str(val)
    return None


def is_ech_capable(https_records: list[Any]) -> bool:
    """True if any HTTPS/SVCB record advertises a non-empty ECH config."""
    ech = extract_ech_config(https_records)
    return bool(ech and _is_plausible_ech_value(ech))


async def check_ech(hostname: str, timeout: float = 3.0) -> dict:
    """Query a hostname's HTTPS + SVCB RRs and report ECH capability.

    Returns a dict shaped for direct attachment to a SniProbeResult's notes /
    a UI tile:

        {
          "hostname": "...",
          "ech_capable": bool,
          "ech_config": str | None,   # raw base64, for debugging
          "https_rr_count": int,
          "svcb_rr_count": int,
          "error": str | None,
        }

    Network failures (SERVFAIL, NXDOMAIN, timeout, no dnspython) are returned
    as `error` strings, NOT raised — ECH detection is best-effort and must
    never break a scan.
    """
    out = {
        "hostname": hostname,
        "ech_capable": False,
        "ech_config": None,
        "https_rr_count": 0,
        "svcb_rr_count": 0,
        "error": None,
    }
    try:
        m = _dns_module()
    except ImportError as e:
        out["error"] = f"dnspython not installed: {e}"
        return out

    loop = asyncio.get_running_loop()

    def _query(rdtype: str) -> list:
        # Use a fresh resolver per call so timeouts/resolvers don't leak.
        r = m.resolver.Resolver()
        r.lifetime = timeout
        r.timeout = timeout
        try:
            answers = r.resolve(hostname, rdtype, raise_on_no_answer=False)
        except m.resolver.NXDOMAIN:
            return []
        except m.resolver.NoNameservers:
            return []
        except m.resolver.LifetimeTimeout:
            raise asyncio.TimeoutError()
        except Exception:
            return []
        rrset = answers.rrset
        return list(rrset) if rrset else []

    try:
        https_rrs = await asyncio.wait_for(
            loop.run_in_executor(None, _query, "HTTPS"), timeout)
        out["https_rr_count"] = len(https_rrs)
        ech = extract_ech_config(https_rrs)
        if ech and _is_plausible_ech_value(ech):
            out["ech_capable"] = True
            out["ech_config"] = ech
            return out
        # Fall back to SVCB if HTTPS had no ECH.
        svcb_rrs = await asyncio.wait_for(
            loop.run_in_executor(None, _query, "SVCB"), timeout)
        out["svcb_rr_count"] = len(svcb_rrs)
        ech = extract_ech_config(svcb_rrs)
        if ech and _is_plausible_ech_value(ech):
            out["ech_capable"] = True
            out["ech_config"] = ech
    except asyncio.TimeoutError:
        out["error"] = f"DNS query timed out after {timeout}s"
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {e}"
    return out
