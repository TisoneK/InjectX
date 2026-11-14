package com.injectx.core

import com.injectx.core.crypto.scheme.DarkI1
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.jsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * Decrypt-layer golden parity for DARK (scheme I1). The envelope decode must
 * reproduce the fields the backend surfaces in `raw_data` — `type`, `name`,
 * `transport`, and the `locked` flag — and the locked/unlocked status.
 */
class DarkI1DecryptTest {

    private val json = Json { ignoreUnknownKeys = true; isLenient = true }

    @Serializable private data class Index(val fixtures: List<Row>)
    @Serializable private data class Row(val fixture: String, val source: String, val format: String? = null)

    private fun resource(name: String): String =
        requireNotNull(javaClass.classLoader.getResourceAsStream(name)) { "missing resource: $name" }
            .bufferedReader().readText()

    private fun repoRoot(): File {
        var d: File? = File(System.getProperty("user.dir"))
        while (d != null) {
            if (File(d, "assets/configs").isDirectory) return d
            d = d.parentFile
        }
        error("repo root not found from ${System.getProperty("user.dir")}")
    }

    private fun str(obj: JsonObject, key: String): String? = when (val e = obj[key]) {
        null, JsonNull -> null
        is JsonPrimitive -> e.content
        else -> e.toString()
    }

    @Test
    fun darkEnvelopeMatchesGolden() {
        val index = json.decodeFromString<Index>(resource("index.json"))
        val root = repoRoot()
        val rows = index.fixtures.filter { it.format == "dark" }
        assertTrue("expected dark fixtures present", rows.isNotEmpty())

        for (row in rows) {
            val fixture = json.parseToJsonElement(resource(row.fixture)).jsonObject
            val rawData = fixture["normalized"]!!.jsonObject["raw_data"]!!.jsonObject

            val result = DarkI1.decrypt(File(root, row.source).readBytes())
            assertEquals("status for ${row.source}", DarkI1.Status.PARTIAL, result.status)
            val env = requireNotNull(result.envelope) { "null envelope for ${row.source}" }

            // type / name / locked are verbatim top-level envelope fields the
            // decrypt layer is responsible for. (`transport` in raw_data is
            // parse-engine-derived from nested config — deferred to
            // full-pipeline parity, ADR-11.)
            assertEquals("locked for ${row.source}", str(rawData, "locked")?.toBoolean(), result.locked)
            assertEquals("type for ${row.source}", str(rawData, "type"), str(env, "type"))
            assertEquals("name for ${row.source}", str(rawData, "name"), str(env, "name"))
        }
    }
}
