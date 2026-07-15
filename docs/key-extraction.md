# Extracting decryption keys ourselves

InjectX's config decryptors need the symmetric key each source app uses
to seal its config exports. Those keys are **baked into the app**. The
public decryptor projects (HCDecryptor, X-Tools) work by extracting the
key from an app build once and publishing it — and they go stale the
moment the app authors rotate it. That is exactly why TLS Tunnel and
ZIVPN don't decode today: the keys InjectX inherited from those projects
were rotated in newer builds.

The durable fix is to extract the **current** key ourselves and load it
without touching code. This document is the procedure.

> **Scope / authorization.** This is reverse-engineering config-file
> formats for a config-analysis tool. Only do it against apps and
> configs you are authorized to analyze (your own devices, security
> research, CTF). Nothing here attacks a network or a third party — it
> recovers the static key an app uses to encode its own export files.

## The key fact first

There is **no keyless shortcut**. TLS Tunnel and ZIVPN use AES-GCM
(AES-256 and AES-128 respectively) — unbroken ciphers. Without the key,
the plaintext is unrecoverable, and brute-forcing a random app key is
infeasible (a dictionary sweep over known ZIVPN passwords was already
tried and failed — see `.context/memory/reviews/2026-07-15-review-5.md`).
So the entire game is: **get the key out of the app.**

## Method 1 — static extraction (try this first)

1. Get the current APK (e.g. from the vendor, APKMirror, or a device via
   `adb pull`). Confirm the version.
2. Decompile:
   ```bash
   jadx -d out/ target.apk          # Java/Kotlin sources
   # or: apktool d target.apk        # smali + resources
   ```
3. Search for the crypto call sites and the key material:
   ```bash
   grep -rniE "SecretKeySpec|AES/GCM|PBKDF2|GCMParameterSpec|IvParameterSpec" out/
   grep -rniE "getBytes|Base64.decode" out/ | grep -i key
   ```
   - For **TLS Tunnel (F1)** you're looking for a 32-byte AES-256 key
     (often a base64 string constant fed to `SecretKeySpec`).
   - For **ZIVPN (H1)** you're looking for the PBKDF2 **password**
     constant and its parameters (iteration count, key length) —
     InjectX currently assumes the KMKZ defaults (SHA-256, 1000
     iterations, 16-byte key); verify these match the current build.
   - For **HA Tunnel (E1)** you're looking for a 16-byte AES-128-ECB key.
4. If strings are obfuscated/encrypted (common in newer builds), static
   grep fails — go to Method 2.

## Method 2 — dynamic extraction with Frida (beats obfuscation)

Run the app and capture the key at the moment it's used, after any
in-app decryption of the constant.

1. Rooted device or emulator + `frida-server` running on it.
2. Hook the JCE crypto entry points and dump the key/IV:
   ```javascript
   // frida -U -f <package> -l dump_key.js
   Java.perform(function () {
     const KeySpec = Java.use("javax.crypto.spec.SecretKeySpec");
     KeySpec.$init.overload("[B", "java.lang.String").implementation =
       function (keyBytes, algo) {
         console.log("[key] " + algo + " " +
           Java.use("android.util.Base64").encodeToString(keyBytes, 2));
         return this.$init(keyBytes, algo);
       };
     const Cipher = Java.use("javax.crypto.Cipher");
     Cipher.doFinal.overload("[B").implementation = function (data) {
       console.log("[cipher] " + this.getAlgorithm());
       return this.doFinal(data);
     };
   });
   ```
3. Trigger an "import/export config" in the app; read the key off the
   Frida console.

## Loading an extracted key into InjectX (no code change)

The runtime keyfile is wired through `get_router()` →
`KeyStore._load_keyfile()`. Write a JSON file whose top-level keys are
the KeyStore categories, then point `INJECTX_KEYFILE` at it:

```json
{
  "tls": ["<new-base64-32-byte-key>"],
  "aot": ["<new-base64-16-byte-key>"]
}
```

```bash
INJECTX_KEYFILE=/path/to/keys.json python backend/main.py
```

Supplied keys are **merged over** the built-in defaults (the old keys
stay, so older configs still decode). Categories: `tls` (TLS Tunnel),
`aot` (HA Tunnel), `evozi` (HTTP Injector legacy), `ePro` (HTTP Custom
legacy), `slipk`, `sip`, `npv2`, `vhd`.

### Known gap

ZIVPN passwords (`H1`), and the HC v2.7 / EHI v2 constants, are still
hardcoded inside their decryptor modules (`decrypt/ziv_decrypt.py`
`_ZIV_PASSWORDS`, `decrypt/hc_v27_decrypt.py`, `decrypt/ehi_v2_decrypt.py`)
rather than in `KeyStore`. Until those are routed through `KeyStore`
(backlog N12), a rotated **ZIVPN** password can't be supplied via the
keyfile — it needs a one-line edit to `_ZIV_PASSWORDS`. TLS and HAT are
fully keyfile-driven today.
