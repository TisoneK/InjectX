package com.injectx.core.crypto

import org.bouncycastle.crypto.digests.SHA256Digest
import org.bouncycastle.crypto.engines.ChaChaEngine
import org.bouncycastle.crypto.generators.Argon2BytesGenerator
import org.bouncycastle.crypto.generators.PKCS5S2ParametersGenerator
import org.bouncycastle.crypto.modes.ChaCha20Poly1305
import org.bouncycastle.crypto.params.AEADParameters
import org.bouncycastle.crypto.params.Argon2Parameters
import org.bouncycastle.crypto.params.KeyParameter
import org.bouncycastle.crypto.params.ParametersWithIV
import javax.crypto.Cipher
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.IvParameterSpec
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

    /** AES-CBC decrypt, no unpadding (caller unpads). Used by EHI's L1/L2 layers. */
    fun aesCbcDecryptNoPad(key: ByteArray, iv: ByteArray, data: ByteArray): ByteArray {
        val cipher = Cipher.getInstance("AES/CBC/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, SecretKeySpec(key, "AES"), IvParameterSpec(iv))
        return cipher.doFinal(data)
    }

    /**
     * Argon2id, matching argon2-cffi `hash_secret_raw(..., type=Type.ID)` with
     * the default version 1.3 (0x13). [memoryCostKiB] is KiB (argon2-cffi
     * `memory_cost`), [timeCost] is iterations, [parallelism] is lanes.
     */
    fun argon2id(
        secret: ByteArray,
        salt: ByteArray,
        timeCost: Int,
        memoryCostKiB: Int,
        parallelism: Int,
        hashLen: Int = 32,
    ): ByteArray {
        val params = Argon2Parameters.Builder(Argon2Parameters.ARGON2_id)
            .withVersion(Argon2Parameters.ARGON2_VERSION_13)
            .withIterations(timeCost)
            .withMemoryAsKB(memoryCostKiB)
            .withParallelism(parallelism)
            .withSalt(salt)
            .build()
        val gen = Argon2BytesGenerator().apply { init(params) }
        val out = ByteArray(hashLen)
        gen.generateBytes(secret, out)
        return out
    }

    /**
     * XChaCha20-Poly1305 decrypt-and-verify (24-byte nonce), matching
     * PyCryptodome `ChaCha20_Poly1305.new(key, nonce=<24 bytes>)`. Implemented
     * as HChaCha20(key, nonce[0:16]) → subkey, then RFC 8439 ChaCha20-Poly1305
     * with that subkey and nonce = 0x00000000 ‖ nonce[16:24]. BC has no direct
     * XChaCha20Poly1305, so HChaCha20 is done here. [ciphertextWithTag] is
     * ciphertext ‖ 16-byte tag. Throws on auth failure.
     */
    fun xchacha20Poly1305Decrypt(
        key: ByteArray,
        nonce24: ByteArray,
        aad: ByteArray,
        ciphertextWithTag: ByteArray,
    ): ByteArray {
        val subkey = hchacha20(key, nonce24.copyOfRange(0, 16))
        val nonce12 = ByteArray(12)
        System.arraycopy(nonce24, 16, nonce12, 4, 8)
        val aead = ChaCha20Poly1305()
        aead.init(false, AEADParameters(KeyParameter(subkey), 128, nonce12, aad))
        val out = ByteArray(aead.getOutputSize(ciphertextWithTag.size))
        var off = aead.processBytes(ciphertextWithTag, 0, ciphertextWithTag.size, out, 0)
        off += aead.doFinal(out, off)
        return out.copyOfRange(0, off)
    }

    private fun rotl(x: Int, n: Int): Int = (x shl n) or (x ushr (32 - n))

    private fun hchacha20(key: ByteArray, nonce16: ByteArray): ByteArray {
        fun le(b: ByteArray, o: Int): Int =
            (b[o].toInt() and 0xff) or ((b[o + 1].toInt() and 0xff) shl 8) or
                ((b[o + 2].toInt() and 0xff) shl 16) or ((b[o + 3].toInt() and 0xff) shl 24)
        val s = IntArray(16)
        s[0] = 0x61707865; s[1] = 0x3320646e; s[2] = 0x79622d32; s[3] = 0x6b206574
        for (i in 0 until 8) s[4 + i] = le(key, i * 4)
        for (i in 0 until 4) s[12 + i] = le(nonce16, i * 4)
        fun qr(a: Int, b: Int, c: Int, d: Int) {
            s[a] += s[b]; s[d] = rotl(s[d] xor s[a], 16)
            s[c] += s[d]; s[b] = rotl(s[b] xor s[c], 12)
            s[a] += s[b]; s[d] = rotl(s[d] xor s[a], 8)
            s[c] += s[d]; s[b] = rotl(s[b] xor s[c], 7)
        }
        repeat(10) {
            qr(0, 4, 8, 12); qr(1, 5, 9, 13); qr(2, 6, 10, 14); qr(3, 7, 11, 15)
            qr(0, 5, 10, 15); qr(1, 6, 11, 12); qr(2, 7, 8, 13); qr(3, 4, 9, 14)
        }
        val out = ByteArray(32)
        val words = intArrayOf(s[0], s[1], s[2], s[3], s[12], s[13], s[14], s[15])
        for (i in words.indices) {
            out[i * 4] = (words[i] and 0xff).toByte()
            out[i * 4 + 1] = ((words[i] ushr 8) and 0xff).toByte()
            out[i * 4 + 2] = ((words[i] ushr 16) and 0xff).toByte()
            out[i * 4 + 3] = ((words[i] ushr 24) and 0xff).toByte()
        }
        return out
    }
}
