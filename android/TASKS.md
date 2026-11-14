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
- [x] Compile `:core` + green `:core:test` on a real JDK (JDK 17 + Gradle 8.9 installed user-level; `GoldenParityTest` passes)
- [x] `gradle wrapper` committed (`./gradlew` runs on a fresh clone)

## Phase 2 — detector
- [x] Port `detector.py` → `core/detect/Detector.kt` (extension + validation, feature vector: entropy/skew/ascii/base64/null/zip, encrypted classifier) — verified via full-pipeline parity (format + is_encrypted + the failed-case feature vector all match)

## Parity methodology (how schemes are verified)
Two levels. **Decrypt-layer parity** (do this first per scheme): assert the
Kotlin decryptor reproduces the Python backend's decrypted field map
(`raw_data._all_fields`) byte-for-byte — this pins the crypto, the risky part.
**Full-pipeline parity** (after detector + parse engine land): assert
`pipeline(source) == fixture.normalized` **excluding `decrypt_trace`**, which
is an implementation-internal audit artifact (exact confidences/attempt order)
and is deliberately not part of the parity contract.

## Phase 3 — crypto primitives + KeyStore
- [x] PBKDF2-HMAC-SHA256 (Bouncy Castle PKCS5S2) + AES-GCM decrypt — `core/crypto/Primitives.kt`
- [x] AES-ECB (javax.crypto) + ChaCha20 8-byte-nonce/seek (Bouncy Castle) — `Primitives.kt`
- [x] AES-CBC (javax.crypto) — `Primitives.kt`
- [x] ChaCha20 + Argon2id + XChaCha20-Poly1305 (Bouncy Castle + hand-rolled HChaCha20) — `Primitives.kt`
- [x] XXTEA, EHI custom base64 alphabet, EHIMSG UTF-16 decode — in `EhiB2.kt`
- [ ] XXTEA, NPV subtraction cipher, HC XOR layers (hand-port)
- [ ] EHI custom base64 alphabet (non-standard — port carefully)
- [ ] `KeyStore.kt` + bundle the 76+ keys from `backend/decrypt/keys.py` as a resource

## Phase 4 — decrypt schemes + router (assert each vs its golden)
- [x] A5 (hc v2.7+: XOR + ChaCha20 + RST AES-ECB + per-field JKL/braille/z3a) — **decrypt-layer parity PASSES** (`HcA5.kt`, `HcA5DecryptTest` vs all 13 hc goldens, new + legacy formats)
- [x] B2 (ehi v2: AES-CBC ×2 + XXTEA + Argon2id + XChaCha20-Poly1305) — **decrypt-layer parity PASSES** (`EhiB2.kt`, `EhiB2DecryptTest` vs all 6 ehi goldens, incl. nested v2rRawJson)
- [x] H1 (ziv: PBKDF2 + AES-128-GCM) — **decrypt-layer parity PASSES** (`ZivH1.kt`, `ZivH1DecryptTest` vs all 6 ziv goldens). Full-pipeline parity pending parse engine.
- [x] I1 (dark: base64 JSON envelope; inner stays locked) — **decrypt-layer parity PASSES** (`DarkI1.kt`, `DarkI1DecryptTest`: type/name/locked/status vs all 4 dark goldens; `transport` is parse-engine-derived, deferred)
- [ ] F1 (tls: AES-256-GCM) — golden ✅ (expected FAILED; port for completeness)
- [ ] A1–A4 (hc legacy), B1 (ehi legacy), C1 (npv), D1 (nsh), E1 (hat), G1 (vhd) — **need samples first (N3)**
- [x] Scheme dispatch in `ParseEngine.parseConfig` (format → decryptor → status/scheme); standalone confidence-scoring router not needed for parity

## Phase 5 — parse engine
- [x] Port `parse_engine.py` → `core/ParseEngine.kt` (detect → dispatch → json_data builders → per-format normalizers → NormalizedConfig; field map, protocol detect, payload parse)
- [x] **Full-pipeline parity PASSES** (`FullPipelineTest`: parseConfig(file) == fixture.normalized for all 31 samples, minus decrypt_trace + machine-specific filepath per ADR-11)

## Phase 6 — UI (`:app`)
- [x] SAF file pick → `ParseEngine.parseConfig` → render key fields + full normalized JSON (`MainActivity.kt`, Compose/Material3 dark)
- [x] Export normalized config (share-sheet JSON)
- [ ] Audit-trace view + per-field niceties (follow-up)

## Phase 7 — SNI Host Hunter
- [ ] Discovery (crt.sh + bundled seedlists), OkHttp
- [ ] TLS/HTTP/DNS prober; ECH via dnsjava (RFC 9848 HTTPS-RR)
- [ ] Reverse-IP, port check
- [ ] Defensive fronting probe (ADR-9: single-target, read-only, non-exploitative)
- [ ] Results UI. Inherits ADR-6 caps.

## Phase 8 — package
- [x] Debug APK builds (`:app:assembleDebug` → app-debug.apk, 13MB) on user-level JDK17 + Android SDK (API 34, build-tools 34.0.0)
- [ ] Release signing config + release APK
- [ ] Runtime verification (needs a device/emulator — not available on this host)
