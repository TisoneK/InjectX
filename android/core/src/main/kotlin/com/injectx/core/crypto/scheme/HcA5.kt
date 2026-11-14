package com.injectx.core.crypto.scheme

import com.injectx.core.crypto.Primitives
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonPrimitive
import java.nio.ByteBuffer
import java.nio.charset.CodingErrorAction
import java.util.Base64

/**
 * HTTP Custom (.hc) v2.7+ decryptor — scheme A5. Port of
 * `backend/decrypt/hc_v27_decrypt.py`.
 *
 * Layers: (1) initial XOR with a fixed hex key; (2) ChaCha20 (8-byte nonce,
 * seek 64) outer envelope → JSON; (3) RST = XOR(range 2..21) → base64 →
 * AES-128-ECB (try 9 keys) on cfg.content; (4) split by [splitConfig] and
 * per-field decrypt (ChaCha20 / JKL-XOR / Braille / z3a). Returns the flat
 * `config` field map (the backend's `_all_fields`).
 */
object HcA5 {

    private val json = Json { ignoreUnknownKeys = true; isLenient = true }

    private val CHACHA_KEYS = listOf(
        "2be4342943c6f91ff58987f41a1aafd179eeb4e053f5cea55b11d6a7db58bd7d",
        "3380aa278b744ba5b529a7f32fa803e48749280dae378345d9b526cf1dbce372",
        "cea9305c95168b162a335b137c61983b8df54e6375da01136547890f14c5fac3",
        "4beeace0e42bae8f29470cf40cf2dfacd5f4e1f751912bf52e803c8c85792193",
        "f8e5f6ebea90558eb32229da24fd0fb7d813091dafe89bb2954fda33b4c60f63",
        "81342f558a6273bac4548d473f54c4ffc7c41747dee81369acab9c787d41ab9c",
        "45635e6fc70486e2fd10d3c2b4780f02d0b4c5f4aa929fc54f86bb8fa4417944",
        "3d632a251c9820f2baf83e15498d27548fc67921cb437f8ce48505989378adea",
    ).map { it.hexToBytes() }

    private val RST_KEYS = listOf(
        "JN1k3YHc2.6_v235", "JN1k3YHc_2.7_v71", "JN1k3YHc2.7.ps69",
        "JN1k3YHc2.7.6950", "Jn1K3yHc2.8.ps08", "Jn1K3yHc2.9.ps6c",
        "Zk:L7>WKaiK*s9>D", "!<f!&WIlM**R.B0X", "b4a5opinx2uloec6",
    ).map { it.toByteArray(Charsets.UTF_8) }

    private val JKL_KEY_OLD = intArrayOf(
        0xd5, 0xd4, 0xd3, 0xd2, 0xd1, 0xd0, 0xcf, 0xce, 0xcd, 0xcc,
        0xbd, 0xbc, 0xbb, 0xba, 0xb9, 0xb8, 0xb7, 0xb6, 0xb5, 0xb4,
    )
    private val JKL_KEY_NEW = intArrayOf(
        8, 9, 10, 11, 12, 13, 14, 15, 17, 17,
        5, 4, 3, 2, 1, 0, 255, 254, 253, 252,
    )

    private val TOKEN_MAP = mapOf(
        0 to "payload", 1 to "proxy_host", 2 to "lock_all_config", 3 to "blocked_by_root",
        4 to "expiry_time", 5 to "note_enabled", 6 to "notes", 7 to "ssh_server",
        8 to "mobile_data_lock", 9 to "unlock_user_pass", 10 to "openvpn_config",
        11 to "openvpn_creds", 12 to "sni", 13 to "unlock_user_pass_2",
        14 to "unknown_14", 15 to "blocked_by_hwid", 16 to "cloud_config",
        17 to "psiphon", 18 to "name", 19 to "block_area",
        20 to "connection_mode", 21 to "blocked_by_password", 22 to "unknown_22",
        23 to "extra_sniffer", 24 to "psiphon_2", 25 to "v2ray_enabled",
        26 to "v2ray_config", 27 to "version", 28 to "slowdns_enabled",
        29 to "slowdns_server", 30 to "slowdns_publickey", 31 to "dns_resolver",
    )

    private const val BRAILLE =
        "⠁⠃⠉⠙⠑⠋⠛⠓⠊⠚" +
        "⠅⠇⠍⠝⠕⠏⠟⠗⠎⠞" +
        "⠥⠧⠺⠭⠽⠵" +
        "⠼⠁⠼⠃⠼⠉⠼⠙⠼⠑" +
        "⠼⠋⠼⠛⠼⠓⠼⠊⠼⠚"

    private val STATIC_NONCE = ByteArray(8) { 0xdb.toByte() }
    private val RST_XOR_KEY = ByteArray(20) { (it + 2).toByte() }
    private val INITIAL_XOR_KEY = "e382e4b8adc386f09f9293".hexToBytes()

    data class Result(val success: Boolean, val fields: Map<String, Any?>)

    // ── helpers ────────────────────────────────────────────────────────────

    private fun String.hexToBytes(): ByteArray =
        ByteArray(length / 2) { ((this[it * 2].digitToInt(16) shl 4) or this[it * 2 + 1].digitToInt(16)).toByte() }

    private fun bytesToHex(b: ByteArray): String = buildString { for (x in b) append("%02x".format(x.toInt() and 0xff)) }

    private fun cleanHex(raw: String?): String {
        if (raw.isNullOrEmpty()) return ""
        val clean = raw.replace(Regex("[^0-9a-fA-F]"), "")
        return if (clean.length % 2 != 0) "0$clean" else clean
    }

    private fun isHex(s: String?): Boolean =
        s != null && s.length >= 16 && Regex("^[0-9a-fA-F]+$").matches(s)

    private fun isMostlyPrintable(s: String?, strict: Boolean = false): Boolean {
        if (s.isNullOrEmpty()) return false
        if (s.length < 4) return true
        val printable = s.count { it.isPrintablePy() || it in "\t\n\r" }
        return printable.toDouble() / s.length > (if (strict) 0.90 else 0.80)
    }

    // Python str.isprintable(): all chars printable (not "other"/separator except space).
    private fun Char.isPrintablePy(): Boolean {
        if (this == ' ') return true
        if (isISOControl()) return false
        val t = Character.getType(this)
        return t != Character.CONTROL.toInt() && t != Character.FORMAT.toInt() &&
            t != Character.SURROGATE.toInt() && t != Character.PRIVATE_USE.toInt() &&
            t != Character.UNASSIGNED.toInt() && t != Character.LINE_SEPARATOR.toInt() &&
            t != Character.PARAGRAPH_SEPARATOR.toInt() && t != Character.SPACE_SEPARATOR.toInt()
    }

    private fun utf8Lenient(b: ByteArray): String {
        val dec = Charsets.UTF_8.newDecoder()
            .onMalformedInput(CodingErrorAction.IGNORE)
            .onUnmappableCharacter(CodingErrorAction.IGNORE)
        return dec.decode(ByteBuffer.wrap(b)).toString()
    }

    /** Strict UTF-8 decode — throws on malformed input (Python's default
     *  str.decode("utf-8")). Used inside JKL so invalid results fall through
     *  to returning the original token, exactly as the Python suppresses. */
    private fun utf8Strict(b: ByteArray): String =
        Charsets.UTF_8.newDecoder().decode(ByteBuffer.wrap(b)).toString()

    private fun latin1IgnoreEncode(s: String): ByteArray {
        val out = ArrayList<Byte>(s.length)
        for (c in s) if (c.code <= 255) out.add(c.code.toByte())
        return out.toByteArray()
    }

    private fun extractInitialPayload(fileBytes: ByteArray): String? = try {
        val s = utf8Lenient(fileBytes)
        val enc = latin1IgnoreEncode(s)
        val x = ByteArray(enc.size) { (enc[it].toInt() xor INITIAL_XOR_KEY[it % INITIAL_XOR_KEY.size].toInt()).toByte() }
        utf8Lenient(x)
    } catch (e: Exception) { null }

    private fun abcDecrypt(rawInput: String?, key: ByteArray, nonce: ByteArray = STATIC_NONCE): String {
        if (rawInput.isNullOrEmpty()) return ""
        return try {
            val data = cleanHex(rawInput).hexToBytes()
            if (data.size > 16) {
                utf8Lenient(Primitives.chacha20(key, nonce, data.copyOfRange(0, data.size - 16), seek = 64))
            } else ""
        } catch (e: Exception) { "" }
    }

    private fun pkcs7Unpad(data: ByteArray): ByteArray {
        if (data.isEmpty()) throw IllegalArgumentException("empty")
        val pad = data.last().toInt() and 0xff
        if (pad < 1 || pad > 16 || pad > data.size) throw IllegalArgumentException("bad pad")
        for (i in data.size - pad until data.size) if ((data[i].toInt() and 0xff) != pad) throw IllegalArgumentException("bad pad")
        return data.copyOfRange(0, data.size - pad)
    }

    private fun rstDecrypt(encrypted: String): String? {
        return try {
            val src = encrypted.toByteArray(Charsets.UTF_8)
            val b64 = ByteArray(src.size) { (src[it].toInt() xor RST_XOR_KEY[it % 20].toInt()).toByte() }
            val aesCt = Base64.getDecoder().decode(b64)
            for (key in RST_KEYS) {
                try {
                    val dec = pkcs7Unpad(Primitives.aesEcbDecryptNoPad(key, aesCt))
                    val s = utf8Lenient(dec)
                    if (s.contains("[splitConfig]")) return s
                } catch (e: Exception) { /* next key */ }
            }
            null
        } catch (e: Exception) { null }
    }

    private fun jklDecrypt(input: String?, isNew: Boolean): String {
        if (input.isNullOrEmpty()) return input ?: ""
        val key = if (isNew) JKL_KEY_NEW else JKL_KEY_OLD
        return try {
            val pad = input.length % 4
            val padded = if (pad != 0) input + "=".repeat(4 - pad) else input
            val data = Base64.getDecoder().decode(padded)
            val out = ByteArray(data.size)
            for (i in data.indices) {
                val d = data[i].toInt() and 0xff
                val k = key[i % 20]
                out[i] = ((((d xor 0xff) and 0xca) or (d and 0x35)) xor (((k xor 0xff) and 0xca) or (k and 0x35))).toByte()
            }
            val inner = utf8Strict(out)
            utf8Strict(Base64.getDecoder().decode(inner))
        } catch (e: Exception) { input }
    }

    private fun decryptBraille(ct: String): String = try {
        val bytes = ArrayList<Byte>()
        var i = 0
        while (i < ct.length - 1) {
            val v = (BRAILLE.indexOf(ct[i]) * 16 + BRAILLE.indexOf(ct[i + 1])) and 255
            bytes.add(v.toByte()); i += 2
        }
        String(bytes.toByteArray(), Charsets.UTF_8)
    } catch (e: Exception) { ct }

    private fun extractZ3a(data: String?, iv: Int): String {
        if (data.isNullOrEmpty()) return ""
        val out = ArrayList<Byte>()
        for (m in Regex("(-?\\d+)\\.(-?\\d+)").findAll(data)) {
            try {
                val v1 = m.groupValues[1].toLong() - iv
                val v2 = m.groupValues[2].toLong() - iv
                if (v2 < 0 || v2 > 62) continue // Python `1 << negative` raises → suppressed
                val divisor = 1L shl v2.toInt()
                // Python uses floor division and non-negative modulo.
                if (divisor != 0L) out.add(Math.floorMod(Math.floorDiv(v1, divisor), 256L).toByte())
            } catch (e: Exception) { }
        }
        return utf8Lenient(out.toByteArray())
    }

    private fun processCredentials(rawValIn: String, isSsh: Boolean): String {
        var rawVal = rawValIn
        if (rawVal.isEmpty()) return rawVal
        if (isSsh && rawVal.isNotEmpty() && BRAILLE.indexOf(rawVal[0]) >= 0) rawVal = decryptBraille(rawVal)
        val pattern = if (isSsh) Regex("^([\\w.\\-]+):([\\d\\-]+)@(.+):(.+)$") else Regex("^([^:]+):(.+)$")
        val match = pattern.find(rawVal) ?: return rawVal
        val g = match.groupValues
        val uEnc = g[g.size - 2]; val pEnc = g[g.size - 1]
        val uDec = extractZ3a(uEnc, Regex("(-?\\d+)\\.(-?\\d+)").findAll(uEnc).count())
        val pDec = extractZ3a(pEnc, Regex("(-?\\d+)\\.(-?\\d+)").findAll(pEnc).count())
        val finalUser = uDec.ifEmpty { uEnc }
        val finalPass = pDec.ifEmpty { pEnc }
        return if (isSsh) "${g[1]}:${g[2]}@$finalUser:$finalPass" else "$finalUser:$finalPass"
    }

    private fun decryptField(token: String, nonce: ByteArray): String {
        if (token.isEmpty() || token in setOf("true", "false", "lifeTime", "[splitPsiphon][splitPsiphon]") || token.startsWith("<")) return token
        val candidates = LinkedHashSet<List<Byte>>()
        val cleanH = cleanHex(token)
        if (isHex(cleanH) && cleanH.length >= 32) try { candidates.add(cleanH.hexToBytes().toList()) } catch (e: Exception) {}
        if (token.length > 16) {
            try { candidates.add(latin1IgnoreEncodeStrict(token).toList()) } catch (e: Exception) {}
            try { candidates.add(token.toByteArray(Charsets.UTF_8).toList()) } catch (e: Exception) {}
        }
        for (cand in candidates) {
            val arr = cand.toByteArray()
            if (arr.size <= 16) continue
            val ciphertext = arr.copyOfRange(0, arr.size - 16)
            for (key in CHACHA_KEYS) {
                try {
                    val decStr = utf8Lenient(Primitives.chacha20(key, nonce, ciphertext, seek = 64))
                    for (isNew in listOf(true, false)) {
                        val out = jklDecrypt(decStr, isNew)
                        if (out.isNotEmpty() && out != decStr && isMostlyPrintable(out)) return out
                    }
                    if ((isMostlyPrintable(decStr, strict = true) &&
                            listOf("HTTP", "@", ":", "{").any { decStr.contains(it) }) ||
                        (decStr.isNotEmpty() && decStr.all { it.isLetterOrDigit() })
                    ) return decStr
                } catch (e: Exception) {}
            }
        }
        for (isNew in listOf(true, false)) {
            val out = jklDecrypt(token, isNew)
            if (out != token && isMostlyPrintable(out)) return out
        }
        return token
    }

    // Python token.encode("latin-1") WITHOUT errors=ignore raises on >255; mirror that.
    private fun latin1IgnoreEncodeStrict(s: String): ByteArray {
        val out = ByteArray(s.length)
        for (i in s.indices) { val c = s[i].code; if (c > 255) throw IllegalArgumentException("latin-1"); out[i] = c.toByte() }
        return out
    }

    fun decrypt(raw: ByteArray): Result {
        val hexPayload = extractInitialPayload(raw) ?: return Result(false, emptyMap())
        val outer = abcDecrypt(hexPayload, CHACHA_KEYS[5])
        if (outer.isEmpty() || !outer.startsWith("{")) return Result(false, emptyMap())
        val jsonObj = try { json.parseToJsonElement(outer) as? JsonObject ?: return Result(false, emptyMap()) }
            catch (e: Exception) { return Result(false, emptyMap()) }

        val cfgObj = jsonObj["cfg"] as? JsonObject
        val isNewFormat = cfgObj != null && cfgObj.containsKey("content")

        val metaValues = LinkedHashMap<String, String>()
        val protections = LinkedHashMap<String, String>()
        val targetCipher: String?
        val splitDelim: String?

        if (isNewFormat) {
            for ((k, name) in mapOf("b" to "hwid", "f" to "area")) {
                val v = (jsonObj[k]?.strOrNull() ?: cfgObj!![k]?.strOrNull() ?: "")
                if (v.isNotEmpty()) { metaValues[name] = v; protections[name] = v }
            }
            targetCipher = cfgObj!!["content"]?.strOrNull()
            splitDelim = "[splitConfig]"
        } else {
            val objA = jsonObj["a"] as? JsonObject
            for ((k, name) in mapOf("bb" to "hwid", "e" to "password", "fe" to "area", "ed" to "provider")) {
                val v = if (k == "e") jsonObj[k]?.strOrNull() else objA?.get(k)?.strOrNull()
                if (!v.isNullOrEmpty()) {
                    val decV = abcDecrypt(v, CHACHA_KEYS[7])
                    if (decV.isNotEmpty()) { metaValues[name] = decV; protections[name] = decV }
                }
            }
            targetCipher = jsonObj["xy"]?.strOrNull() ?: objA?.get("xy")?.strOrNull()
            splitDelim = jsonObj["uv"]?.strOrNull() ?: objA?.get("uv")?.strOrNull() ?: "[splitConfig]"
        }

        if (targetCipher.isNullOrEmpty() || splitDelim.isNullOrEmpty()) return Result(false, emptyMap())

        fun toHex(s: String?): String = if (!s.isNullOrEmpty()) bytesToHex(s.toByteArray(Charsets.UTF_8)) else ""
        val h = metaValues["hwid"]; val p = metaValues["password"]; val pr = metaValues["provider"]; val a = metaValues["area"]
        val derivedHex = if (!h.isNullOrEmpty() && p.isNullOrEmpty() && pr.isNullOrEmpty() && a.isNullOrEmpty())
            toHex(h) + toHex(h) else toHex(p) + toHex(h) + toHex(pr) + toHex(a)
        val dynamicNonce = STATIC_NONCE.copyOf()
        if (derivedHex.isNotEmpty()) try {
            val db = derivedHex.hexToBytes(); for (i in 0 until minOf(8, db.size)) dynamicNonce[i] = db[i]
        } catch (e: Exception) {}

        var xyDec: String? = null
        if (isNewFormat) {
            xyDec = rstDecrypt(targetCipher)
            if (xyDec == null) for (key in CHACHA_KEYS) {
                val temp = abcDecrypt(targetCipher, key)
                if (temp.contains(splitDelim)) { xyDec = temp; break }
            }
        } else {
            xyDec = abcDecrypt(targetCipher, CHACHA_KEYS[1])
        }
        if (xyDec.isNullOrEmpty()) return Result(false, emptyMap())

        val configData = LinkedHashMap<String, Any?>()
        val tokens = xyDec.split(splitDelim)
        for ((i, token) in tokens.withIndex()) {
            if (i == 22 || i == 24) continue
            val label = TOKEN_MAP[i] ?: "field_$i"
            var finalOut: Any? = token
            try {
                if (isNewFormat) {
                    finalOut = decryptField(token, dynamicNonce)
                } else {
                    var fo = token
                    if (isHex(token)) fo = abcDecrypt(token, CHACHA_KEYS[7], dynamicNonce)
                    finalOut = jklDecrypt(fo, false)
                }
                if (i == 7) finalOut = processCredentials(finalOut as String, true)
                else if (i == 11) finalOut = processCredentials(finalOut as String, false)

                if (finalOut is String && finalOut.isNotEmpty()) {
                    var s = finalOut.replace("88a05e8772eac3e5703e0cd26c6e6f23de72fb09f7ee5a43283d1681f19d", "")
                    finalOut = s
                    if (s.startsWith("{") || s.startsWith("[")) {
                        try { finalOut = json.parseToJsonElement(s) } catch (e: Exception) {}
                    }
                    if (!(finalOut is String && isHex(finalOut))) configData[label] = finalOut
                }
            } catch (e: Exception) {}
        }
        return Result(true, configData)
    }

    private fun kotlinx.serialization.json.JsonElement.strOrNull(): String? =
        (this as? JsonPrimitive)?.let { if (it.isString) it.content else it.contentOrNull } ?: this.jsonPrimitive.contentOrNull
}
