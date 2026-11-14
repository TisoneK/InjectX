package com.injectx.core.sni

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive

/**
 * Seed-list loader — port of `backend/snihunter/sources/seedlist.py`.
 * Parses USER-supplied .txt / .csv / .json seedlists into deduped
 * [SniCandidate]s. No carrier presets ship with the app (features/
 * android-ui.md §11.1): a universal tool must not name ISPs, and bug-host
 * lists are the user's own to supply, name and save. Plain `.txt` / pasted
 * input now flows through [DomainInput]; this stays for structured csv/json.
 */
object Seedlist {

    private val json = Json { ignoreUnknownKeys = true; isLenient = true }

    private fun mk(hostname: String): SniCandidate =
        SniCandidate(hostname = hostname.trim().lowercase().trimStart('*', '.'), source = "seedlist")

    private fun truthy(v: String?): Boolean =
        v?.trim()?.lowercase() in setOf("1", "true", "yes", "y", "on")

    private fun parseTxt(text: String): List<Pair<String, Boolean>> {
        val out = ArrayList<Pair<String, Boolean>>()
        for (lineRaw in text.lineSequence()) {
            var line = lineRaw.trim()
            if (line.isEmpty() || line.startsWith("#")) continue
            line = line.substringBefore("#").trim()
            if (line.isNotEmpty()) out.add(line to false)
        }
        return out
    }

    private fun parseCsv(text: String): List<Pair<String, Boolean>> {
        val lines = text.lineSequence().filter { it.isNotBlank() }.toList()
        if (lines.isEmpty()) return emptyList()
        val header = lines.first().split(",").map { it.trim().lowercase() }
        val hostIdx = listOf("domain", "hostname", "host").map { header.indexOf(it) }.firstOrNull { it >= 0 }
        val cfIdx = listOf("cloudflare", "cf").map { header.indexOf(it) }.firstOrNull { it >= 0 } ?: -1
        val out = ArrayList<Pair<String, Boolean>>()
        if (hostIdx == null) {
            // Headerless single-column CSV.
            for (row in lines) {
                val cell = row.split(",").firstOrNull()?.trim() ?: continue
                if (cell.isNotEmpty() && !cell.startsWith("#")) out.add(cell to false)
            }
            return out
        }
        for (row in lines.drop(1)) {
            val cells = row.split(",")
            val host = cells.getOrNull(hostIdx)?.trim() ?: continue
            if (host.isEmpty()) continue
            val cf = if (cfIdx >= 0) truthy(cells.getOrNull(cfIdx)) else false
            out.add(host to cf)
        }
        return out
    }

    private fun parseJson(text: String): List<Pair<String, Boolean>> {
        val arr = json.parseToJsonElement(text) as? JsonArray ?: throw IllegalArgumentException("JSON seedlist must be an array")
        val out = ArrayList<Pair<String, Boolean>>()
        for (item in arr) {
            when (item) {
                is JsonPrimitive -> if (item.isString && item.content.isNotBlank()) out.add(item.content.trim() to false)
                is JsonObject -> {
                    val host = (item["domain"] ?: item["hostname"] ?: item["host"]) as? JsonPrimitive
                    val h = host?.content?.trim()
                    if (!h.isNullOrEmpty()) out.add(h to truthy((item["cloudflare"] as? JsonPrimitive)?.content))
                }
                else -> {}
            }
        }
        return out
    }

    fun loadSeedlist(text: String, ext: String, cloudflareOnly: Boolean = false): List<SniCandidate> {
        val pairs = when (ext.lowercase()) {
            ".txt", "txt" -> parseTxt(text)
            ".csv", "csv" -> parseCsv(text)
            ".json", "json" -> parseJson(text)
            else -> throw IllegalArgumentException("Unsupported seedlist extension: $ext")
        }
        val seen = LinkedHashSet<String>()
        val out = ArrayList<SniCandidate>()
        for ((host, cf) in pairs) {
            if (cloudflareOnly && !cf) continue
            val cand = mk(host)
            if (cand.hostname.isEmpty() || !seen.add(cand.hostname)) continue
            out.add(cand)
        }
        return out
    }
}
