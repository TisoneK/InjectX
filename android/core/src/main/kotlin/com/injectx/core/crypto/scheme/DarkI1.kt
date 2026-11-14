package com.injectx.core.crypto.scheme

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import java.util.Base64

/**
 * DARK Tunnel (.dark) decoder — scheme I1. Port of
 * `backend/decrypt/dark_decrypt.py`.
 *
 * A .dark file is `darktunnel://<base64(JSON)>`. The JSON envelope is
 * plaintext and exposes `type`, `name`, `transport`, and — when the author
 * did not lock it — the server/credentials. The optional
 * `encryptedLockedConfig` field is DRM: a device/server-bound blob with no key
 * in the file, so a locked config is only PARTIAL (type/name recoverable). This
 * decodes the envelope and reports whether the credential body is locked.
 */
object DarkI1 {

    private val PREFIXES = listOf("darktunnel://", "dark://", "dt://")
    private val json = Json { ignoreUnknownKeys = true; isLenient = true }

    enum class Status { SUCCESS, PARTIAL, FAILED }

    data class Result(val status: Status, val envelope: JsonObject?, val locked: Boolean)

    /** Base64 that may be URL-safe and/or unpadded — matches the Python helper. */
    private fun b64Tolerant(s: String): ByteArray {
        var t = s.trim().replace('-', '+').replace('_', '/')
        val pad = (4 - t.length % 4) % 4
        t += "=".repeat(pad)
        return Base64.getDecoder().decode(t)
    }

    fun decrypt(raw: ByteArray): Result {
        val content = raw.toString(Charsets.UTF_8).trim()
        var body = content
        for (p in PREFIXES) {
            if (body.startsWith(p)) { body = body.substring(p.length); break }
        }

        val obj: JsonObject = try {
            json.parseToJsonElement(b64Tolerant(body).toString(Charsets.UTF_8)) as? JsonObject
                ?: return Result(Status.FAILED, null, false)
        } catch (e: Exception) {
            // Fall back to plain JSON (some exports aren't base64-wrapped).
            try {
                json.parseToJsonElement(content) as? JsonObject
                    ?: return Result(Status.FAILED, null, false)
            } catch (e2: Exception) {
                return Result(Status.FAILED, null, false)
            }
        }

        // Python `bool(data.get("encryptedLockedConfig"))`: truthy when present
        // and not null / not an empty string.
        val lockedVal = obj["encryptedLockedConfig"]
        val locked = when (lockedVal) {
            null, JsonNull -> false
            is JsonPrimitive -> if (lockedVal.isString) lockedVal.content.isNotEmpty() else lockedVal.content != "false"
            else -> true
        }
        val status = if (locked) Status.PARTIAL else Status.SUCCESS
        return Result(status, obj, locked)
    }
}
