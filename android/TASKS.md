# InjectX Android — task checklist (N18)

Phases follow `features/android-app.md` §5. Each decrypt scheme is ported
against its golden fixture (`goldens/fixtures/`). A scheme with **no sample
config** has **no golden** yet — add a sample (backlog N3) before porting, or
port without parity coverage (riskier).

## Golden-vector coverage (what the samples actually exercise)

| Scheme | Format | Samples | Golden coverage |
|--------|--------|--------:|-----------------|
| A5 | hc | 13 | ✅ success |
| B2 | ehi | 6 | ✅ success |
| H1 | ziv | 6 | ✅ success |
| I1 | dark | 4 | ✅ partial (inner blob stays locked) |
| F1 | tls | 2 | ✅ known-FAILED (rotated key, upstream block) |
| A1–A4, B1, C1 (npv), D1 (nsh), E1 (hat), G1 (vhd) | — | 0 | ❌ none — needs samples (N3) |

## Phase 1 — scaffold + goldens
- [x] Gradle project (`:core` JVM lib, `:app` Android)
- [x] Golden-vector generator + 31 fixtures (verified vs Python)
- [x] Shared model `Models.kt` (port of `ir/models.py`)
- [x] Golden parity test harness (contract check)
- [ ] Compile `:core` + green `:core:test` on a real JDK (needs toolchain)
- [ ] `gradle wrapper` committed from a toolchain host

## Phase 2 — detector
- [ ] Port `backend/parser/detector.py` → `core/detect/Detector.kt` (entropy, ascii ratio, zip magic, base64 likelihood, null-byte ratio; extension + content rules)
- [ ] Test vs detector's format verdicts for all 31 samples

## Phase 3 — crypto primitives + KeyStore
- [ ] AES-ECB/CBC/GCM + PBKDF2 wrappers (javax.crypto)
- [ ] ChaCha20 + Argon2id (Bouncy Castle)
- [ ] XXTEA, NPV subtraction cipher, HC XOR layers (hand-port)
- [ ] EHI custom base64 alphabet (non-standard — port carefully)
- [ ] `KeyStore.kt` + bundle the 76+ keys from `backend/decrypt/keys.py` as a resource

## Phase 4 — decrypt schemes + router (assert each vs its golden)
- [ ] A5 (hc v2.7+: XOR + ChaCha20 + RST AES-ECB + per-field) — golden ✅
- [ ] B2 (ehi v2: AES-CBC ×2 + XXTEA + Argon2id + ChaCha20-Poly1305) — golden ✅
- [ ] H1 (ziv: AES-256-GCM + PBKDF2) — golden ✅
- [ ] I1 (dark: base64 JSON envelope; inner stays locked) — golden ✅ partial
- [ ] F1 (tls: AES-256-GCM) — golden ✅ (expected FAILED; port for completeness)
- [ ] A1–A4 (hc legacy), B1 (ehi legacy), C1 (npv), D1 (nsh), E1 (hat), G1 (vhd) — **need samples first (N3)**
- [ ] `SchemeRouter.kt` — dispatch + confidence selection (port `decrypt/router.py`)

## Phase 5 — parse engine
- [ ] Port `parser/parse_engine.py` + per-format parsers → `NormalizedConfig`
- [ ] Full golden parity: pipeline(source) == fixture.normalized for all 31

## Phase 6 — UI (`:app`)
- [ ] SAF file pick → detect → decrypt → render normalized config + audit trace
- [ ] Export normalized config

## Phase 7 — SNI Host Hunter
- [ ] Discovery (crt.sh + bundled seedlists), OkHttp
- [ ] TLS/HTTP/DNS prober; ECH via dnsjava (RFC 9848 HTTPS-RR)
- [ ] Reverse-IP, port check
- [ ] Defensive fronting probe (ADR-9: single-target, read-only, non-exploitative)
- [ ] Results UI. Inherits ADR-6 caps.

## Phase 8 — package
- [ ] Signing config, release APK
