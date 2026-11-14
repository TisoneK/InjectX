package com.injectx.core.crypto.scheme

import com.injectx.core.crypto.Primitives
import java.util.Base64

/**
 * ZIVPN (.ziv) decryptor — scheme H1. Faithful port of
 * `backend/decrypt/ziv_decrypt.py`.
 *
 * File format: `base64(salt) . base64(nonce) . base64(ciphertext‖tag)`.
 * Key = PBKDF2-HMAC-SHA256(password, salt, 1000 iters, 16 bytes); payload is
 * AES-128-GCM. The password is a hardcoded app constant tried from a known
 * list (current ZIVPN Tunnel v2.1.5 uses the concatenated "SecurePart1..5").
 * On success the plaintext is XML with `<entry key="k">v</entry>` pairs, which
 * this returns as a flat ordered map (the backend's `_all_fields`).
 */
object ZivH1 {

    private val PASSWORDS = listOf(
        "SecurePart1SecurePart2SecurePart3SecurePart4SecurePart5",
        "fubvx788b46v",
        "fubvx788B4mev",
        "zivpn",
        "ZIVPN",
        "com.zi.zivpn",
        "zi.zivpn",
    )

    private val ENTRY = Regex("""<entry key="([^"]*)">([^<]*)</entry>""")

    /** [success] false means every known password failed the GCM auth check. */
    data class Result(val success: Boolean, val keyLabel: String?, val fields: Map<String, String>)

    fun decrypt(raw: ByteArray): Result {
        val content = raw.toString(Charsets.UTF_8).trim()
        val parts = content.split(".")
        if (parts.size != 3) return Result(false, null, emptyMap())

        val dec = Base64.getDecoder()
        val salt: ByteArray
        val nonce: ByteArray
        val ctMac: ByteArray
        try {
            salt = dec.decode(parts[0])
            nonce = dec.decode(parts[1])
            ctMac = dec.decode(parts[2])
        } catch (e: IllegalArgumentException) {
            return Result(false, null, emptyMap())
        }

        for (pw in PASSWORDS) {
            try {
                val key = Primitives.pbkdf2HmacSha256(pw.toByteArray(Charsets.UTF_8), salt)
                val plain = Primitives.aesGcmDecrypt(key, nonce, ctMac)
                val text = String(plain, Charsets.UTF_8)
                val fields = LinkedHashMap<String, String>()
                for (m in ENTRY.findAll(text)) {
                    fields[m.groupValues[1]] = m.groupValues[2]
                }
                return Result(true, "ziv:$pw", fields)
            } catch (e: Exception) {
                // Wrong password → GCM tag mismatch; try the next one.
            }
        }
        return Result(false, null, emptyMap())
    }
}
