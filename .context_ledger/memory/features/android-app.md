# Feature Spec — InjectX Android App

> **Status:** **Planned — not started.** No code written yet. This is the
> build plan agreed with the user in Session 34 (2026-11-13, Forge /
> claude-opus-4-8, local macOS).
> **Added:** 2026-11-13 by Forge (Session 34).
> **Decision of record:** see **ADR-10** in `plans/decisions.md` — native
> Kotlin rewrite (NOT Chaquopy/embedded-Python), with **decrypt + SNI
> Host Hunter both in v1**. Those two choices were made by the USER in
> this session; an agent picking this up must honor ADR-10 or supersede it
> with a new ADR, never silently.

---

## 1. Goal

Ship a native **Android** app that delivers InjectX's core value on a
phone: pick a VPN tunnel config file → detect its format → decrypt it →
show the normalized config; plus the **SNI Host Hunter** (discover/probe
bug hosts, ECH check, fronting probe). Monetization is explicitly **out of
scope** for now (the user set that aside in Session 34 after a discussion
of the legal/app-store/payment risks of a "pay-per-decryption" model —
summarized in that session's entry).

## 2. Why this is a rewrite, not a port

The current product is **Electron (desktop UI) + a Python/FastAPI backend**
(`frontend/` + `backend/`). Neither runs on Android. The irreplaceable
asset is **~5,800 lines of Python** crypto/parsing:

- `backend/decrypt/` — 13 scheme implementations (A1–A5 HC, B1/B2 EHI, C1
  NPV, D1 NSH, E1 HAT, F1 TLS, G1 VHD, H1 ZIV, I1 DARK) + `router.py`
  (scheme dispatch + confidence scoring) + `keys.py` (KeyStore, 76+ keys).
- `backend/parser/` — `detector.py` (extension + content sniffing),
  per-format parsers, `parse_engine.py` (745 lines — field map +
  normalization).
- `backend/ir/models.py` — the shared IR (DecryptedPayload, DecryptTrace,
  Format/Scheme enums, etc.) every module depends on.
- `backend/snihunter/` — discovery (crt.sh + seedlists), async TLS/HTTP/DNS
  prober, ECH (RFC 9848 DNS HTTPS-RR), reverse-IP, port check, defensive
  fronting probe (`defensive.py`, governed by ADR-9).

## 3. Architecture decision (ADR-10)

- **Native Kotlin rewrite** of the decrypt/parser core and SNI Hunter.
  (Chaquopy/embedded-Python was offered and **rejected by the user** —
  they want a proper native app, smaller APK, no bundled interpreter.)
- **Monorepo:** new Gradle module **`android/`** at repo root, beside the
  Python. Keeping the Python in-tree is deliberate — it becomes the
  **reference implementation** for the golden-vector test harness (§6).
- **UI:** Jetpack Compose, single-activity, Material 3 dark theme (mirror
  the current Electron dark UI). Min SDK 26 (Android 8) for the modern
  crypto APIs; ~95% device coverage.
- **Crypto libraries:**
  - `javax.crypto` (JDK, built in) — AES-ECB/CBC/GCM, PBKDF2.
  - **Bouncy Castle** — ChaCha20 and **Argon2id** (uniform, one dep).
  - Hand-ported (tiny): XXTEA, the NPV subtraction cipher, HC XOR layers.
  - `android.util.Base64` / `java.util.Base64` (+ the EHI custom-alphabet
    base64 — port carefully, it is non-standard).
- **SNI Hunter networking:** OkHttp (HTTP + crt.sh), **dnsjava** (DNS
  SVCB/HTTPS-RR for ECH), and raw `SSLSocket`/`SSLEngine` for the
  custom-SNI handshake and the fronting probe's mismatched `Host` header.

## 4. Module mapping (Python → Kotlin)

| Python | Kotlin (under `android/.../core|feature`) | Notes |
|---|---|---|
| `ir/models.py` | `core/model/*.kt` | data classes + enums |
| `parser/detector.py` | `core/detect/Detector.kt` | ext + content sniff |
| `decrypt/keys.py` | `core/crypto/KeyStore.kt` | 76+ keys as bundled asset |
| `decrypt/*_decrypt.py` ×13 | `core/crypto/scheme/*.kt` | the bulk of the work |
| `decrypt/router.py` | `core/crypto/SchemeRouter.kt` | dispatch + confidence |
| `parser/*_parser.py`, `parse_engine.py` | `core/parse/*.kt` | → normalized config |
| `snihunter/*` | `feature/sni/*.kt` | Phase 7 |

## 5. Phased plan (each phase a shippable checkpoint)

1. **Scaffold** — Gradle project, Compose skeleton, package layout, and the
   **golden-vector harness** (§6). Depends on nothing; everything depends on it.
2. **Models + detector** — port IR models + format detection; test vs detector's known outputs.
3. **Crypto primitives + KeyStore** — AES/ChaCha20/PBKDF2/Argon2/XXTEA wrappers + key bundle; unit-test with vectors.
4. **Decrypt schemes + router** — port all 13 schemes A1–I1; each asserted against its golden output. Largest phase; likely several sessions.
5. **Parse engine** — per-format parsers → normalized config + audit trace.
6. **UI** — Storage Access Framework file pick → detect → decrypt → show normalized config + audit trail + export.
7. **SNI Hunter** — discovery, TLS/HTTP/DNS probing, ECH, reverse-IP, fronting probe, results UI. Inherits **ADR-6** (loopback/no-scanning caps) and **ADR-9** (defensive probe is single-target, read-only, non-exploitative).
8. **Package** — signing config, release APK.

## 6. Testing strategy — golden-vector parity (non-negotiable)

A hand-rewrite of 13 crypto schemes will drift from the Python subtly. The
harness runs each Python decryptor over the bundled `assets/configs/`
samples, captures the normalized output as fixtures, and the Kotlin tests
assert **byte-identical** results. Build this in Phase 1 before any scheme
is ported. (Relates to open backlog N3/N4 — sample-config test coverage and
CI — which this harness would also feed.)

## 7. Known risks / spots that will need iteration

- **Argon2id** (EHI B2) and the **raw custom-SNI handshake** are the two
  most likely to need iteration against real device/TLS behavior.
- **TLS scheme F1** is already blocked upstream on a rotated key gated
  behind DexProtector (README; Session 16 — needs dynamic Frida). It will
  *port* but stay non-functional until that key exists — same as desktop.
- **EHI custom base64 alphabet** and the **NPV subtraction cipher** are
  easy to get subtly wrong — lean on golden vectors.
- **Dual-use / responsible-use framing** carries over: SNI Hunter on mobile
  is the same research/verification tool, same ToS caveats as the README's
  "Responsible Use" section. ADR-6 + ADR-9 bounds are binding on the port.

## 8. Open questions for whoever starts this

1. Repo home: confirm the `android/` monorepo module (this plan's
   assumption) vs a separate repo. Monorepo recommended (golden vectors).
2. v1 UI scope: is "export normalized config" enough, or is "apply SNI /
   edit a field" wanted on mobile too?
3. Does the tunnel engine (SSH/WS/V2Ray/Hysteria — empty `backend/tunnel/`
   on desktop) ever belong on mobile, or is this strictly a reader?
