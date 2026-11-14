package com.injectx.core

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.jsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * Full-pipeline parity (ADR-11): `ParseEngine.parseConfig(file)` must equal the
 * Python backend's `NormalizedConfig` for every sample, comparing all IR fields
 * EXCEPT `decrypt_trace` (implementation-internal audit, out of contract).
 */
class FullPipelineTest {

    private val json = Json { ignoreUnknownKeys = true; isLenient = true }

    @Serializable private data class Index(val fixtures: List<Row>)
    @Serializable private data class Row(val fixture: String, val source: String, val format: String? = null)

    private fun resource(name: String): String =
        requireNotNull(javaClass.classLoader.getResourceAsStream(name)) { "missing: $name" }
            .bufferedReader().readText()

    private fun repoRoot(): File {
        var d: File? = File(System.getProperty("user.dir"))
        while (d != null) { if (File(d, "assets/configs").isDirectory) return d; d = d.parentFile }
        error("repo root not found")
    }

    // Exclude decrypt_trace (audit, ADR-11) and filepath (absolute vs the
    // generator's repo-relative rewrite — machine-specific, not semantic).
    private fun minusTrace(o: JsonObject): JsonObject =
        JsonObject(o.filterKeys { it != "decrypt_trace" && it != "filepath" })

    @Test
    fun pipelineMatchesGolden() {
        val index = json.decodeFromString<Index>(resource("index.json"))
        val root = repoRoot()
        assertTrue(index.fixtures.isNotEmpty())
        for (row in index.fixtures) {
            val fixture = json.parseToJsonElement(resource(row.fixture)).jsonObject
            val expected = minusTrace(fixture["normalized"]!!.jsonObject)
            val actual = minusTrace(ParseEngine.parseConfig(File(root, row.source)))
            assertEquals("pipeline mismatch for ${row.source}", expected, actual)
        }
    }
}
