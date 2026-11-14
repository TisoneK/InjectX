package com.injectx.core.sni

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/** Port of `backend/snihunter/models.py` (the subset the Kotlin side needs). */

@Serializable
enum class Verdict {
    @SerialName("working") WORKING,
    @SerialName("redirect") REDIRECT,
    @SerialName("blocked") BLOCKED,
    @SerialName("dead") DEAD,
    @SerialName("unknown") UNKNOWN;

    val wire: String get() = when (this) {
        WORKING -> "working"; REDIRECT -> "redirect"; BLOCKED -> "blocked"; DEAD -> "dead"; UNKNOWN -> "unknown"
    }
}

@Serializable
enum class FrontingVerdict {
    @SerialName("bypassable") BYPASSABLE,
    @SerialName("enforced") ENFORCED,
    @SerialName("indeterminate") INDETERMINATE,
    @SerialName("error") ERROR,
}

@Serializable
data class SniCandidate(
    val hostname: String,
    val source: String, // crt.sh | seedlist | certstream | manual
    @SerialName("issuer_ca_id") val issuerCaId: Int? = null,
    @SerialName("not_before") val notBefore: String? = null,
    @SerialName("not_after") val notAfter: String? = null,
)

@Serializable
data class SniProbeResult(
    val hostname: String,
    @SerialName("target_ip") val targetIp: String? = null,
    val port: Int = 443,
    @SerialName("tls_handshake_ok") val tlsHandshakeOk: Boolean = false,
    @SerialName("http_status") val httpStatus: Int? = null,
    @SerialName("http_redirect") val httpRedirect: String? = null,
    @SerialName("server_header") val serverHeader: String? = null,
    @SerialName("cert_cn") val certCn: String? = null,
    @SerialName("cert_sans") val certSans: List<String> = emptyList(),
    @SerialName("forward_dns") val forwardDns: List<String> = emptyList(),
    @SerialName("reverse_dns") val reverseDns: String? = null,
    @SerialName("dns_consistent") val dnsConsistent: Boolean? = null,
    val verdict: Verdict = Verdict.UNKNOWN,
    val notes: List<String> = emptyList(),
    @SerialName("elapsed_ms") val elapsedMs: Double = 0.0,
)

@Serializable
data class SniScanJob(
    @SerialName("job_id") val jobId: String,
    val status: String = "queued",
    @SerialName("seed_domain") val seedDomain: String? = null,
    val candidates: List<SniCandidate> = emptyList(),
    val total: Int = 0,
    val done: Int = 0,
    val found: Int = 0,
    val results: List<SniProbeResult> = emptyList(),
    val error: String? = null,
)
