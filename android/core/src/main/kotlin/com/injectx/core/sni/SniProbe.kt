package com.injectx.core.sni

/**
 * Pure SNI-prober logic — port of the I/O-free parts of
 * `backend/snihunter/probe.py` (the live TLS/HTTP/DNS probing lives in
 * [SniNetwork]). `classifyHttp` and `looksLikeCaptivePortal` are pure so the
 * verdict heuristic is unit-tested directly.
 */
object SniProbe {

    /** ADR-6: hard ceiling on concurrent probes. */
    const val MAX_CONCURRENCY = 200

    private val DEFAULT_INDICATORS = listOf(
        "captive", "portal", "no-balance", "nobalance", "topup", "top-up",
        "data.bundles", "databundles", "internetsuppressed", "suppressed",
        "outofbundle", "out-of-bundle", "selfcare", "recharge", "unsubscribed",
    )

    /** Captive-portal indicators, loaded from the bundled resource (a user can
     *  extend it), falling back to the built-in list. */
    val portalIndicators: List<String> by lazy { loadIndicators() }

    private fun loadIndicators(): List<String> {
        val text = javaClass.classLoader?.getResourceAsStream("sni/portal_indicators.txt")
            ?.bufferedReader()?.use { it.readText() } ?: return DEFAULT_INDICATORS
        val out = text.lineSequence()
            .map { it.substringBefore("#").trim().lowercase() }
            .filter { it.isNotEmpty() }
            .toList()
        return out.ifEmpty { DEFAULT_INDICATORS }
    }

    fun looksLikeCaptivePortal(url: String?, indicators: List<String> = portalIndicators): Boolean {
        if (url.isNullOrEmpty()) return false
        val low = url.lowercase()
        return indicators.any { it in low }
    }

    /**
     * Pure verdict classifier from an HTTP response (port of `classify_http`):
     * 2xx → working, 4xx → working, 3xx→portal → blocked, 3xx→else → redirect,
     * 5xx / null → dead.
     */
    fun classifyHttp(
        status: Int?,
        redirectLocation: String? = null,
        indicators: List<String> = portalIndicators,
    ): Verdict {
        if (status == null) return Verdict.DEAD
        return when {
            status in 200..299 -> Verdict.WORKING
            status in 300..399 -> if (looksLikeCaptivePortal(redirectLocation, indicators)) Verdict.BLOCKED else Verdict.REDIRECT
            status in 400..499 -> Verdict.WORKING
            else -> Verdict.DEAD
        }
    }

    /** ADR-6: probe each unique hostname at most once per job (order-preserving). */
    fun dedupeHostnames(hostnames: List<String>): List<String> {
        val seen = LinkedHashSet<String>()
        for (h in hostnames) {
            val t = h.trim().lowercase()
            if (t.isNotEmpty()) seen.add(t)
        }
        return seen.toList()
    }

    fun clampConcurrency(n: Int): Int = maxOf(1, minOf(n, MAX_CONCURRENCY))
}
