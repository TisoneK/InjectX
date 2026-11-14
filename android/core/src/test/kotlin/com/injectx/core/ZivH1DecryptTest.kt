package com.injectx.core

import com.injectx.core.crypto.scheme.ZivH1
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * Decrypt-layer golden parity for ZIV (scheme H1): the Kotlin decryptor must
 * reproduce the Python backend's decrypted `<entry>` map (`raw_data._all_fields`
 * in the fixture) byte-for-byte. This verifies the crypto (PBKDF2 + AES-GCM)
 * and the XML extraction — the hard, error-prone part — independently of the
 * parse-engine normalization (ported later; see android/TASKS.md).
 *
 * Fixtures come from test resources; the source `.ziv` bytes are read from the
 * repo (located by walking up for `assets/configs/`).
 */
class ZivH1DecryptTest {

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
        error("repo root (assets/configs) not found from ${System.getProperty("user.dir")}")
    }

    @Test
    fun zivDecryptMatchesGoldenFields() {
        val index = json.decodeFromString<Index>(resource("index.json"))
        val root = repoRoot()
        val zivRows = index.fixtures.filter { it.format == "ziv" }
        assertTrue("expected ziv fixtures present", zivRows.isNotEmpty())

        for (row in zivRows) {
            val fixture = json.parseToJsonElement(resource(row.fixture)).jsonObject
            val expected = fixture["normalized"]!!.jsonObject["raw_data"]!!
                .jsonObject["_all_fields"]!!.jsonObject
                .mapValues { it.value.jsonPrimitive.content }

            val raw = File(root, row.source).readBytes()
            val result = ZivH1.decrypt(raw)

            assertTrue("ZIV decrypt failed for ${row.source}", result.success)
            assertEquals("decrypted field map mismatch for ${row.source}", expected, result.fields)
        }
    }
}
