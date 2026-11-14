package com.injectx.core

import com.injectx.core.crypto.scheme.EhiB2
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * Decrypt-layer golden parity for EHI v2 (scheme B2): the Kotlin decryptor
 * (AES-CBC ×2 → XXTEA → Argon2id → XChaCha20-Poly1305 → inner-field decode)
 * must reproduce the backend's recovered field map (`raw_data._all_fields`),
 * including the nested v2rRawJson / overwriteServerData objects.
 */
class EhiB2DecryptTest {

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

    @Test
    fun ehiDecryptMatchesGoldenFields() {
        val index = json.decodeFromString<Index>(resource("index.json"))
        val root = repoRoot()
        val rows = index.fixtures.filter { it.format == "ehi" }
        assertTrue("expected ehi fixtures present", rows.isNotEmpty())

        for (row in rows) {
            val fixture = json.parseToJsonElement(resource(row.fixture)).jsonObject
            val expected = fixture["normalized"]!!.jsonObject["raw_data"]!!
                .jsonObject["_all_fields"]!!.jsonObject

            val result = EhiB2.decrypt(File(root, row.source).readBytes())
            assertTrue("EHI decrypt failed for ${row.source}", result.success)
            assertEquals("field map mismatch for ${row.source}", expected, result.fields)
        }
    }
}
