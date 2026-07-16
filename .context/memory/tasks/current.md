# Current Task (overwrite each session)

Holds exactly one task — the one being worked on right now.

- **Session:** idle — no task in progress.
- **Last session:** 2026-07-15 Session 16 (Claude Fable 5, local macOS) — **blocked (no code change).** Tried to extract the TLS Tunnel `.tls` AES-GCM key from the v8.0.6 APK (com.tlsvpn.tlstunnel) with the ZIVPN method. **Blocked by DexProtector** (`libdexprotector.so`) — a commercial packer that encrypts the app's own strings/classes at runtime. Every AES/GCM reference in the dex was an unprotected ad SDK (Digital Turbine `Lhm`, Conscrypt `Lo30`, Tink, Mintegral); a 148k-string × 5-derivation brute force found no key. TLS's F1 algorithm is still correct — only the runtime-only key is missing. **Next:** dynamic Frida on a rooted device/emulator (needs the user's device — not runnable on the dev machine). Documented the packer caveat in `docs/key-extraction.md`. Decryption scoreboard: HC ✅, EHI ✅, DARK ✅ (envelope), ZIVPN ✅; TLS blocked (DexProtector → Frida); HAT/NPV/NSH/VHD need samples; LNK unknown. See `reviews/2026-07-15-review-9.md`.
