package com.injectx.core.crypto

import org.bouncycastle.crypto.digests.SHA256Digest
import org.bouncycastle.crypto.engines.ChaChaEngine
import org.bouncycastle.crypto.generators.PKCS5S2ParametersGenerator
import org.bouncycastle.crypto.params.KeyParameter
import org.bouncycastle.crypto.params.ParametersWithIV
import javax.crypto.Cipher
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.SecretKeySpec

/**
 * Low-level crypto primitives shared by the decrypt schemes. Chosen to be
 * byte-for-byte compatible with the Python backend (`backend/decrypt/`):
 * where the JDK's own API risks a mismatch (notably PBKDF2's char[]-vs-bytes
 * password handling), we use Bouncy Castle, which takes password bytes
 * directly — the same generator the target apps use.
 */
object Primitives {

    /**
     * PBKDF2-HMAC-SHA256. Matches PyCryptodome `PBKDF2(pw, salt,
     * hmac_hash_module=SHA256)` with its defaults (count=1000, dkLen=16 bytes)
     * and the ZIVPN app's BouncyCastle PKCS5S2 generator. Password is passed
     * as raw bytes (no char[] encoding ambiguity).
     */
    fun pbkdf2HmacSha256(
        password: ByteArray,
        salt: ByteArray,
        iterations: Int = 1000,
        dkLenBytes: Int = 16,
    ): ByteArray {
        val gen = PKCS5S2ParametersGenerator(SHA256Digest())
        gen.init(password, salt, iterations)
        return (gen.generateDerivedParameters(dkLenBytes * 8) as KeyParameter).key
    }

    /**
     * AES/GCM decrypt-and-verify. [ciphertextWithTag] is the ciphertext with
     * its 16-byte GCM tag appended — the same bytes PyCryptodome splits via
     * `decrypt_and_verify(ct[:-16], ct[-16:])`. The JDK verifies the tag and
     * throws (AEADBadTagException) if it fails, mirroring the Python behaviour.
     * Key length selects AES-128/192/256 (ZIV H1 uses a 16-byte key → AES-128).
     */
    fun aesGcmDecrypt(key: ByteArray, nonce: ByteArray, ciphertextWithTag: ByteArray): ByteArray {
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, SecretKeySpec(key, "AES"), GCMParameterSpec(128, nonce))
        return cipher.doFinal(ciphertextWithTag)
    }

    /** AES-128/256-ECB, no padding (caller strips PKCS7). Used by HC's RST layer. */
    fun aesEcbDecryptNoPad(key: ByteArray, data: ByteArray): ByteArray {
        val cipher = Cipher.getInstance("AES/ECB/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, SecretKeySpec(key, "AES"))
        return cipher.doFinal(data)
    }

    /**
     * Original (Bernstein) ChaCha20 with an 8-byte nonce and a 64-bit counter —
     * matching PyCryptodome `ChaCha20.new(key, nonce=<8 bytes>)`. [seek] skips
     * that many keystream bytes first (PyCryptodome `cipher.seek(n)`); HC A5
     * uses seek(64). ChaCha20 is a stream cipher, so decrypt == XOR keystream.
     */
    fun chacha20(key: ByteArray, nonce: ByteArray, data: ByteArray, seek: Int = 0): ByteArray {
        val engine = ChaChaEngine() // default 20 rounds
        engine.init(false, ParametersWithIV(KeyParameter(key), nonce))
        if (seek > 0) {
            val skip = ByteArray(seek)
            engine.processBytes(skip, 0, seek, ByteArray(seek), 0)
        }
        val out = ByteArray(data.size)
        engine.processBytes(data, 0, data.size, out, 0)
        return out
    }
}
