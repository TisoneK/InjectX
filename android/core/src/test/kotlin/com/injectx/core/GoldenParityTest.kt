package com.injectx.core

import com.injectx.core.model.NormalizedConfig
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Golden-vector parity harness (ADR-10). The fixtures under
 * `android/goldens/fixtures/` are produced by the reference Python backend
 * (`android/goldens/generate_goldens.py`) and wired in as test resources by
 * `core/build.gradle.kts`.
 *
 * TODAY this test proves the Kotlin [NormalizedConfig] model deserializes the
 * real backend output (so the contract matches). The TODO below is the real
 * parity assertion: once the Kotlin pipeline (Detector -> SchemeRouter ->
 * parsers) exists, run it on `fixture.source` and assert its NormalizedConfig
 * equals `fixture.normalized`. Until then this guards the model/contract.
 */
class GoldenParityTest {

    private val json = Json { ignoreUnknownKeys = true; isLenient = true }

    @Serializable
    private data class Index(val count: Int, val errors: Int, val fixtures: List<IndexRow>)

    @Serializable
    private data class IndexRow(
        val fixture: String,
        val source: String,
        val format: String? = null,
        val decryption_status: String? = null,
        val scheme_used: String? = null,
    )

    @Serializable
    private data class Fixture(
        val source: String,
        val normalized: NormalizedConfig? = null,
        val error: String? = null,
    )

    private fun resource(name: String): String =
        requireNotNull(javaClass.classLoader.getResourceAsStream(name)) {
            "missing golden resource: $name (run generate_goldens.py)"
        }.bufferedReader().readText()

    @Test
    fun everyGoldenDeserializesAndMatchesIndex() {
        val index = json.decodeFromString<Index>(resource("index.json"))
        assertTrue("expected fixtures present", index.count > 0)

        var checked = 0
        for (row in index.fixtures) {
            val fixture = json.decodeFromString<Fixture>(resource(row.fixture))
            val n = fixture.normalized ?: continue  // error fixtures carry no config
            assertEquals("format mismatch in ${row.fixture}", row.format, n.format.jsonValue())
            assertEquals(
                "decryption_status mismatch in ${row.fixture}",
                row.decryption_status, n.decryptionStatus.jsonValue(),
            )
            checked++
        }
        assertTrue("at least one config fixture deserialized", checked > 0)
    }
}

/** Serial name of an enum constant (the JSON value the backend emitted). */
private fun Enum<*>.jsonValue(): String {
    val field = javaClass.getField(name)
    val ann = field.getAnnotation(kotlinx.serialization.SerialName::class.java)
    return ann?.value ?: name
}
