package com.injectx.core

import com.injectx.core.crypto.scheme.HcA5
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.jsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * Decrypt-layer golden parity for HC v2.7+ (scheme A5): the Kotlin decryptor
 * must reproduce the backend's recovered field map (`raw_data._all_fields`).
 * Values are compared as strings (nested-JSON fields by their canonical text).
 */
class HcA5DecryptTest {

    private val json = Json { ignoreUnknownKeys = true; isLenient = true }

    @Serializable private data class Index(val fixtures: List<Row>)
    @Serializable private data class Row(val fixture: String, val source: String, val format: String? = null)

    private fun resource(name: String): String =
        requireNotNull(javaClass.classLoader.getResourceAsStream(name)) { "missing resource: $name" }
            .bufferedReader().readText()

    private fun repoRoot(): File {
        var d: File? = File(System.getProperty("user.dir"))
        while (d != null) { if (File(d, "assets/configs").isDirectory) return d; d = d.parentFile }
        error("repo root not found from ${System.getProperty("user.dir")}")
    }

    private fun stringify(e: JsonElement): String =
        if (e is JsonPrimitive && e.isString) e.content else e.toString()

    private fun stringifyAny(v: Any?): String = when (v) {
        is String -> v
        is JsonElement -> stringify(v)
        else -> v.toString()
    }

    @Test
    fun hcDecryptMatchesGoldenFields() {
        val index = json.decodeFromString<Index>(resource("index.json"))
        val root = repoRoot()
        val rows = index.fixtures.filter { it.format == "hc" }
        assertTrue("expected hc fixtures present", rows.isNotEmpty())

        for (row in rows) {
            val fixture = json.parseToJsonElement(resource(row.fixture)).jsonObject
            val expected = fixture["normalized"]!!.jsonObject["raw_data"]!!
                .jsonObject["_all_fields"]!!.jsonObject
                .mapValues { stringify(it.value) }

            val result = HcA5.decrypt(File(root, row.source).readBytes())
            assertTrue("HC decrypt failed for ${row.source}", result.success)
            val actual = result.fields.mapValues { stringifyAny(it.value) }
            assertEquals("field map mismatch for ${row.source}", expected, actual)
        }
    }
}
