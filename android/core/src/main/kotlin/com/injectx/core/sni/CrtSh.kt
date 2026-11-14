package com.injectx.core.sni

import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.intOrNull

/**
 * crt.sh discovery parsing — port of `backend/snihunter/sources/crtsh.py`.
 * The network GET lives in [SniNetwork]; [parseCrtshRows] is pure so it can be
 * unit-tested against fixture JSON rows.
 */
object CrtSh {

    const val URL_TEMPLATE = "https://crt.sh/?q=%25.{domain}&output=json"

    private val HOSTNAME_RE = Regex("^(?=.{1,253}$)([a-z0-9_-]{1,63}\\.)+[a-z]{2,63}$")

    /** Normalise one CT name into a bare probeable hostname, or null. */
    fun clean(nameIn: String): String? {
        var name = nameIn.trim().lowercase()
        if (name.isEmpty()) return null
        if (name.startsWith("*.")) name = name.substring(2)
        if ("@" in name || " " in name) return null
        if (!HOSTNAME_RE.matches(name)) return null
        return name
    }

    fun parseCrtshRows(rows: List<JsonObject>): List<SniCandidate> {
        val seen = LinkedHashSet<String>()
        val out = ArrayList<SniCandidate>()
        for (row in rows) {
            val names = ((row["name_value"] as? JsonPrimitive)?.content ?: "").split("\n").toMutableList()
            (row["common_name"] as? JsonPrimitive)?.contentOrNull?.let { names.add(it) }
            for (raw in names) {
                val host = clean(raw) ?: continue
                if (!seen.add(host)) continue
                out.add(
                    SniCandidate(
                        hostname = host,
                        source = "crt.sh",
                        issuerCaId = (row["issuer_ca_id"] as? JsonPrimitive)?.intOrNull,
                        notBefore = (row["not_before"] as? JsonPrimitive)?.contentOrNull,
                        notAfter = (row["not_after"] as? JsonPrimitive)?.contentOrNull,
                    ),
                )
            }
        }
        return out
    }
}
