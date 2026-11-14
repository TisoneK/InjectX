package com.injectx.core.crypto.scheme

import com.injectx.core.crypto.Primitives
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.jsonObject
import java.io.ByteArrayInputStream
import java.security.MessageDigest
import java.util.Base64

/**
 * HTTP Injector (.ehi) v2 decryptor — scheme B2. Port of
 * `backend/decrypt/ehi_v2_decrypt.py`.
 *
 * Layers: parse EHI binary header → AES-256-CBC (L1, try 6 IVs) →
 * "a:b:c" → AES-128-CBC (L2, IV=b64(a)) → XXTEA (EOO key) → JSON config.
 * Standard-IV configs then: configData → reverse+custom-b64+hex+XOR → base64
 * → Argon2id key → XChaCha20-Poly1305 → final JSON. Inner string fields are
 * XOR-decoded (or EHIMSG-decoded for configMessage); v2rRawJson /
 * overwriteServerData are parsed as nested JSON. Returns the field map
 * (the backend's `_all_fields`).
 */
object EhiB2 {

    private val json = Json { ignoreUnknownKeys = true; isLenient = true }

    private val L1_KEY = "7e1210f7aab956f7a668bda6e57feddb7f84ad840aef8d27b1b969959be3ab6c".hex()
    private val L2_KEY = "b2bc617c32d8b9eb1943a5ffa8051eea".hex()
    private val EOO_MASTER_KEY = byteArrayOf(
        'n'.code.toByte(), 'u'.code.toByte(), 'l'.code.toByte(), 'l'.code.toByte(),
        '='.code.toByte(), 'V'.code.toByte(), '5'.code.toByte(), 'k'.code.toByte(),
        'U'.code.toByte(), '5'.code.toByte(), '+'.code.toByte(), 'F'.code.toByte(),
        'F'.code.toByte(), 'r'.code.toByte(), 'Y'.code.toByte(), 0,
    )
    private val BYPASS_IVS = listOf(
        "221d572349555f1d112133236b1f4a3f", "5543494c53443e3f4a6a4539384e776a",
        "374c2541575e4d531a3c327b75431e5f",
    ).map { it.hex() }
    private val STANDARD_IVS = listOf(
        "2c5d1147bbad422b3b334d4d235f1a53", "522b01433a5e8b2fc7549e1ad368e541",
        "337a1035aaedf3458ca167e92d74b839",
    ).map { it.hex() }

    private const val STD_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    private const val CUSTOM_ALPHABET = "RkLC2QaVMPYgGJW/A4f7qzDb9e+t6Hr0Zp8OlNyjuxKcTw1o5EIimhBn3UvdSFXs"
    private val TRANSLATE: Map<Char, Char> = CUSTOM_ALPHABET.indices.associate { CUSTOM_ALPHABET[it] to STD_ALPHABET[it] }

    data class Result(val success: Boolean, val fields: JsonObject)

    // ── helpers ──────────────────────────────────────────────────────────

    private fun String.hex(): ByteArray =
        ByteArray(length / 2) { ((this[it * 2].digitToInt(16) shl 4) or this[it * 2 + 1].digitToInt(16)).toByte() }

    private fun hexToBytes(s: String): ByteArray =
        ByteArray(s.length / 2) { ((s[it * 2].digitToInt(16) shl 4) or this.run { s[it * 2 + 1].digitToInt(16) }).toByte() }

    private fun pkcs7Unpad(data: ByteArray): ByteArray {
        val pad = data.last().toInt() and 0xff
        if (pad < 1 || pad > 16 || pad > data.size) throw IllegalArgumentException("pad")
        for (i in data.size - pad until data.size) if ((data[i].toInt() and 0xff) != pad) throw IllegalArgumentException("pad")
        return data.copyOfRange(0, data.size - pad)
    }

    private fun customB64Decode(s: String): ByteArray {
        var clean = s.replace("?", "")
        val rem = clean.length % 4
        if (rem != 0) clean += "=".repeat(4 - rem)
        val translated = buildString { for (c in clean) append(TRANSLATE[c] ?: c) }
        return Base64.getDecoder().decode(translated)
    }

    /** null = decryption judged invalid (Python returns None). */
    private fun decryptXorLayer(ct: String?, key: String): String? {
        if (ct == null || ct.isBlank()) return ct
        return try {
            val hexRaw = customB64Decode(ct.reversed())
            var hexString = String(hexRaw, Charsets.US_ASCII) // strict-ish; non-ascii → '?' but Python would raise
            if (hexString.length % 2 != 0) hexString = "0$hexString"
            val rawBytes = hexToBytes(hexString)
            val keyLen = key.length
            val dec = ArrayList<Byte>(rawBytes.size)
            for (i in rawBytes.indices) {
                val x = (rawBytes[i].toInt() and 0xff) xor (key[i % keyLen].code and 0xff)
                if (x != 0) dec.add(x.toByte())
            }
            val plaintext = utf8Strict(dec.toByteArray())
            if (plaintext.isNotEmpty()) {
                val ctrl = plaintext.count { it.code < 32 && it.code !in intArrayOf(9, 10, 13) }
                if (ctrl.toDouble() / plaintext.length > 0.5) return null
            }
            plaintext
        } catch (e: Exception) { null }
    }

    private fun decodeConfigMessage(ct: String?): String {
        if (ct == null || ct.isBlank()) return ct ?: ""
        return try {
            val padded = ct + "=".repeat((4 - ct.length % 4) % 4)
            val rawBytes = Base64.getDecoder().decode(padded)
            val utf16 = String(rawBytes, Charsets.UTF_8).toByteArray(Charsets.UTF_16BE)
            val n = utf16.size / 2
            val keyChars = "EHIMSG".map { it.code }
            val outBytes = ByteArray(n * 2)
            for (i in 0 until n) {
                val jc = ((utf16[i * 2].toInt() and 0xff) shl 8) or (utf16[i * 2 + 1].toInt() and 0xff)
                val x = jc xor keyChars[i % keyChars.size]
                outBytes[i * 2] = ((x ushr 8) and 0xff).toByte()
                outBytes[i * 2 + 1] = (x and 0xff).toByte()
            }
            String(outBytes, Charsets.UTF_16BE)
        } catch (e: Exception) { ct }
    }

    private fun xxteaDecrypt(dataIn: ByteArray, key: ByteArray): ByteArray {
        if (dataIn.isEmpty()) return ByteArray(0)
        var data = dataIn
        val rem = data.size % 4
        if (rem != 0) data = data + ByteArray(4 - rem)
        val kbuf = key.copyOf(16)
        val k = LongArray(4) { leU32(kbuf, it * 4) }
        val n = data.size / 4
        val v = LongArray(n) { leU32(data, it * 4) }
        val delta = 0x9E3779B9L
        var sum = ((6 + 52 / n) * delta) and 0xFFFFFFFFL
        var y = v[0]
        val mask = 0xFFFFFFFFL
        while (sum != 0L) {
            val e = ((sum ushr 2) and 3).toInt()
            var p = n - 1
            while (p > 0) {
                val z = v[p - 1]
                val mx = ((((z ushr 5) xor (y shl 2)) + ((y ushr 3) xor (z shl 4))) xor
                    ((sum xor y) + (k[(p and 3) xor e] xor z)))
                y = (v[p] - mx) and mask
                v[p] = y
                p--
            }
            val z = v[n - 1]
            val mx = ((((z ushr 5) xor (y shl 2)) + ((y ushr 3) xor (z shl 4))) xor
                ((sum xor y) + (k[(0 and 3) xor e] xor z)))
            y = (v[0] - mx) and mask
            v[0] = y
            sum = (sum - delta) and mask
        }
        val outBytes = ByteArray(n * 4)
        for (i in 0 until n) {
            outBytes[i * 4] = (v[i] and 0xff).toByte()
            outBytes[i * 4 + 1] = ((v[i] ushr 8) and 0xff).toByte()
            outBytes[i * 4 + 2] = ((v[i] ushr 16) and 0xff).toByte()
            outBytes[i * 4 + 3] = ((v[i] ushr 24) and 0xff).toByte()
        }
        val length = v[n - 1]
        return if (length in 1..(n.toLong() * 4)) outBytes.copyOfRange(0, length.toInt())
        else { var end = outBytes.size; while (end > 0 && outBytes[end - 1].toInt() == 0) end--; outBytes.copyOfRange(0, end) }
    }

    private fun leU32(b: ByteArray, o: Int): Long =
        ((b[o].toLong() and 0xff) or ((b[o + 1].toLong() and 0xff) shl 8) or
            ((b[o + 2].toLong() and 0xff) shl 16) or ((b[o + 3].toLong() and 0xff) shl 24)) and 0xFFFFFFFFL

    private fun parseEhiBytes(fileBytes: ByteArray): ByteArray? = try {
        val f = ByteArrayInputStream(fileBytes)
        fun readN(n: Int): ByteArray { val b = ByteArray(n); val r = f.read(b); return if (r < n) b.copyOf(if (r < 0) 0 else r) else b }
        fun rUtf() { val l = readN(2); if (l.size < 2) return; val len = ((l[0].toInt() and 0xff) shl 8) or (l[1].toInt() and 0xff); readN(len) }
        rUtf(); readN(8); rUtf(); readN(8)
        val pl = readN(4)
        if (pl.size < 4) null
        else {
            val pLen = ((pl[0].toLong() and 0xff) shl 24) or ((pl[1].toLong() and 0xff) shl 16) or
                ((pl[2].toLong() and 0xff) shl 8) or (pl[3].toLong() and 0xff)
            readN(8)
            readN(pLen.toInt())
        }
    } catch (e: Exception) { null }

    private fun str(obj: JsonObject, key: String, default: String = ""): String =
        (obj[key] as? JsonPrimitive)?.content ?: default

    private fun generateMasterKey(config: JsonObject): ByteArray {
        val parts = listOf(
            str(config, "configAesKey"),
            str(config, "configIdentifier"),
            str(config, "configSalt"),
            str(config, "configTimestamp", "0"),
            str(config, "configExpiryTimestamp", "0"),
            str(config, "lockModes"),
            str(config, "lockModesHash"),
            str(config, "configHwid"),
            str(config, "configLockMobileOperatorId"),
        )
        val payload = parts.filter { it.isNotEmpty() }.joinToString("")
        return MessageDigest.getInstance("SHA-256").digest(payload.toByteArray(Charsets.UTF_8))
    }

    private fun decodeInnerFields(parsed: JsonObject, salt: String): LinkedHashMap<String, JsonElement> {
        val out = LinkedHashMap<String, JsonElement>()
        val vital = setOf("overwriteServerData")
        for ((k, v) in parsed) {
            if (v is JsonPrimitive && v.isString && v.content.isNotBlank()) {
                val decoded = if (k == "configMessage") decodeConfigMessage(v.content) else decryptXorLayer(v.content, salt)
                when {
                    decoded != null -> out[k] = JsonPrimitive(decoded)
                    k in vital -> out[k] = v
                }
            } else out[k] = v
        }
        return out
    }

    fun decrypt(raw: ByteArray): Result {
        val payload = parseEhiBytes(raw) ?: return Result(false, JsonObject(emptyMap()))
        var config: JsonObject? = null
        var matchedIv: ByteArray? = null
        for (iv in BYPASS_IVS + STANDARD_IVS) {
            try {
                val l1 = utf8Strict(pkcs7Unpad(Primitives.aesCbcDecryptNoPad(L1_KEY, iv, payload)))
                val parts = l1.split(":")
                if (parts.size < 3) continue
                val garbage = pkcs7Unpad(
                    Primitives.aesCbcDecryptNoPad(L2_KEY, Base64.getDecoder().decode(parts[0]), Base64.getDecoder().decode(parts[2]))
                )
                val finalRaw = xxteaDecrypt(garbage, EOO_MASTER_KEY)
                val brace = finalRaw.indexOf('{'.code.toByte())
                if (brace != -1) {
                    config = json.parseToJsonElement(utf8Lenient(finalRaw.copyOfRange(brace, finalRaw.size))) as? JsonObject ?: continue
                    matchedIv = iv
                    break
                }
            } catch (e: Exception) { /* try next IV */ }
        }
        val cfg = config ?: return Result(false, JsonObject(emptyMap()))
        val targetSalt = str(cfg, "configSalt", "EVZJNI")

        val parsedFinal: JsonObject = if (matchedIv in BYPASS_IVS) {
            cfg
        } else {
            val targetData = (cfg["configData"] as? JsonPrimitive)?.content
                ?: return Result(false, JsonObject(emptyMap()))
            val aaa = decryptXorLayer(targetData, targetSalt) ?: return Result(false, JsonObject(emptyMap()))
            val rawPayload = try { Base64.getDecoder().decode(aaa) } catch (e: Exception) { return Result(false, JsonObject(emptyMap())) }
            if (rawPayload.size <= 50) return Result(false, JsonObject(emptyMap()))
            try {
                val argonKey = Primitives.argon2id(
                    secret = generateMasterKey(cfg),
                    salt = rawPayload.copyOfRange(0x0A, 0x1A),
                    timeCost = leU32(rawPayload, 1).toInt(),
                    memoryCostKiB = leU32(rawPayload, 5).toInt(),
                    parallelism = rawPayload[9].toInt() and 0xff,
                    hashLen = 32,
                )
                val plain = Primitives.xchacha20Poly1305Decrypt(
                    key = argonKey,
                    nonce24 = rawPayload.copyOfRange(0x1A, 0x32),
                    aad = rawPayload.copyOfRange(0, 0x1A),
                    ciphertextWithTag = rawPayload.copyOfRange(0x32, rawPayload.size),
                )
                json.parseToJsonElement(utf8Lenient(plain)) as? JsonObject ?: return Result(false, JsonObject(emptyMap()))
            } catch (e: Exception) { return Result(false, JsonObject(emptyMap())) }
        }

        val cleaned = decodeInnerFields(parsedFinal, targetSalt)

        // Parse nested JSON string fields into objects.
        for (field in listOf("v2rRawJson", "overwriteServerData")) {
            val el = cleaned[field]
            if (el is JsonPrimitive && el.isString) {
                val s = el.content
                val start = s.indexOf('{'); val end = s.lastIndexOf('}')
                if (start != -1 && end != -1) {
                    try { cleaned[field] = json.parseToJsonElement(s.substring(start, end + 1)) } catch (e: Exception) {}
                }
            }
        }

        return Result(true, buildJsonObject { for ((k, v) in cleaned) /* preserve */ this.put(k, v) })
    }

    private fun utf8Strict(b: ByteArray): String =
        Charsets.UTF_8.newDecoder().decode(java.nio.ByteBuffer.wrap(b)).toString()

    private fun utf8Lenient(b: ByteArray): String =
        Charsets.UTF_8.newDecoder()
            .onMalformedInput(java.nio.charset.CodingErrorAction.IGNORE)
            .onUnmappableCharacter(java.nio.charset.CodingErrorAction.IGNORE)
            .decode(java.nio.ByteBuffer.wrap(b)).toString()
}
