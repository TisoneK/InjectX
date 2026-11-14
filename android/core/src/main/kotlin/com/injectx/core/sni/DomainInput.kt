package com.injectx.core.sni

/**
 * The ONE flexible host input for SNI Hunter (features/android-ui.md §11.3–6).
 *
 * Accepts, in a single text field or an imported `.txt`:
 *   - a single domain
 *   - several separated by `;` / `,` / spaces / tabs / newlines
 *   - a rockyou-style list, one host per line (possibly huge)
 *
 * Cleanup per token (§11.4): trim, lowercase, strip `http(s)://`, any path,
 * any `:port`, a leading `*.`, and leading/trailing dots; blank lines and
 * `#` comments are ignored. Invalid tokens are reported (not silently
 * dropped) so the UI can show "N valid, M skipped" and list the skips.
 * Duplicates collapse (order-preserving) and are counted separately — a
 * huge list repeating hosts isn't "skipped", it's deduped.
 *
 * Pure and unit-tested; no Android, no I/O.
 */
object DomainInput {

    /** A line/token that could not be used, with a human reason for the UI. */
    data class Skipped(val raw: String, val reason: String)

    data class Result(
        val valid: List<String>,   // cleaned, deduped, in first-seen order
        val skipped: List<Skipped>,
        val duplicates: Int,
    ) {
        val isReady: Boolean get() = valid.isNotEmpty()
        /** "212 valid · 3 skipped" style summary for the live count. */
        fun summary(): String = buildString {
            append(valid.size).append(if (valid.size == 1) " valid" else " valid")
            if (skipped.isNotEmpty()) append(" · ").append(skipped.size).append(" skipped")
            if (duplicates > 0) append(" · ").append(duplicates).append(" duplicate").append(if (duplicates == 1) "" else "s")
        }
    }

    // Split a line into tokens on ; , and any whitespace.
    private val SEP = Regex("[;,\\s]+")

    // Permissive hostname (allows punycode TLDs via a-z0-9- in the last label).
    private val HOSTNAME_RE = Regex("^(?=.{1,253}$)([a-z0-9_-]{1,63}\\.)+[a-z0-9-]{2,63}$")

    /** Clean one raw token to a bare probeable hostname, or null if unusable. */
    fun clean(raw: String): String? {
        var s = raw.trim().lowercase()
        if (s.isEmpty()) return null
        // scheme
        s = s.removePrefix("https://").removePrefix("http://").removePrefix("//")
        // path / query / fragment — cut at the first delimiter
        s = s.substringBefore('/').substringBefore('?').substringBefore('#')
        // port
        s = s.substringBefore(':')
        // wildcard + stray dots
        if (s.startsWith("*.")) s = s.substring(2)
        s = s.trim('.')
        if (s.isEmpty()) return null
        return if (HOSTNAME_RE.matches(s)) s else null
    }

    fun parse(text: String): Result {
        val valid = LinkedHashSet<String>()
        val skipped = ArrayList<Skipped>()
        var duplicates = 0

        for (lineRaw in text.lineSequence()) {
            val line = lineRaw.trim()
            if (line.isEmpty() || line.startsWith("#")) continue       // §11.4 ignore blanks + comments
            val body = line.substringBefore('#').trim()                 // inline comment
            if (body.isEmpty()) continue
            for (token in body.split(SEP)) {
                if (token.isBlank()) continue
                val host = clean(token)
                when {
                    host == null -> skipped.add(Skipped(token, "not a valid hostname"))
                    !valid.add(host) -> duplicates++
                }
            }
        }
        return Result(valid.toList(), skipped, duplicates)
    }
}
