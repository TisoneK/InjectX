package com.injectx.core.sni

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import okhttp3.OkHttpClient
import okhttp3.Request
import java.net.InetAddress
import java.net.InetSocketAddress
import java.security.cert.X509Certificate
import java.time.Duration
import javax.net.ssl.SNIHostName
import javax.net.ssl.SSLSocket
import javax.net.ssl.SSLSocketFactory

/**
 * Live SNI probing + crt.sh discovery — port of the network halves of
 * `backend/snihunter/probe.py` and `sources/crtsh.py`.
 *
 * NOTE: this layer is I/O and cannot be golden-verified offline; it is
 * compile-verified only. The verdict/parse logic it relies on ([SniProbe],
 * [CrtSh]) IS unit-tested. Callers must run it off the main thread. Inherits
 * ADR-6 (single probe per host, concurrency cap) and the research/verification
 * framing — it is not a scanner.
 */
object SniNetwork {

    private val json = Json { ignoreUnknownKeys = true; isLenient = true }

    private fun httpClient(timeoutMs: Int): OkHttpClient = OkHttpClient.Builder()
        .followRedirects(false)
        .followSslRedirects(false)
        .callTimeout(Duration.ofMillis(timeoutMs.toLong()))
        .connectTimeout(Duration.ofMillis(timeoutMs.toLong()))
        .readTimeout(Duration.ofMillis(timeoutMs.toLong()))
        .build()

    /** Probe one hostname end-to-end: forward DNS → TLS (SNI) cert → HTTP GET
     *  → reverse DNS/consistency → verdict. */
    fun probeOne(hostname: String, port: Int = 443, timeoutMs: Int = 5000): SniProbeResult {
        val t0 = System.nanoTime()
        val notes = ArrayList<String>()
        fun elapsed() = (System.nanoTime() - t0) / 1_000_000.0

        // 1) forward DNS
        val forward = try {
            InetAddress.getAllByName(hostname).map { it.hostAddress }.distinct()
        } catch (e: Exception) {
            return SniProbeResult(hostname, port = port, verdict = Verdict.DEAD,
                notes = listOf("DNS resolution failed"), elapsedMs = elapsed())
        }
        if (forward.isEmpty()) return SniProbeResult(hostname, port = port, verdict = Verdict.DEAD,
            notes = listOf("no A/AAAA records"), elapsedMs = elapsed())
        val targetIp = forward.first()

        // 2) TLS handshake with SNI = hostname, capture cert
        var tlsOk = false; var certCn: String? = null; var certSans: List<String> = emptyList()
        try {
            val factory = SSLSocketFactory.getDefault() as SSLSocketFactory
            (factory.createSocket() as SSLSocket).use { sock ->
                sock.connect(InetSocketAddress(hostname, port), timeoutMs)
                sock.soTimeout = timeoutMs
                sock.sslParameters = sock.sslParameters.apply { serverNames = listOf(SNIHostName(hostname)) }
                sock.startHandshake()
                tlsOk = true
                val peer = sock.session.peerCertificates.firstOrNull() as? X509Certificate
                if (peer != null) { certCn = cn(peer); certSans = sans(peer) }
            }
        } catch (e: java.net.SocketTimeoutException) {
            return SniProbeResult(hostname, targetIp = targetIp, port = port, forwardDns = forward,
                verdict = Verdict.DEAD, notes = listOf("TLS handshake timed out"), elapsedMs = elapsed())
        } catch (e: Exception) {
            return SniProbeResult(hostname, targetIp = targetIp, port = port, forwardDns = forward,
                verdict = Verdict.DEAD, notes = listOf("TLS handshake failed: ${e.javaClass.simpleName}"), elapsedMs = elapsed())
        }

        // 3) HTTP GET → status/redirect
        var status: Int? = null; var server: String? = null; var redirect: String? = null
        var verdict: Verdict
        try {
            val req = Request.Builder().url("https://$hostname/")
                .header("User-Agent", "InjectX-SNIHunter").build()
            httpClient(timeoutMs).newCall(req).execute().use { resp ->
                status = resp.code
                server = resp.header("server")
                if (resp.code in 300..399) redirect = resp.header("location")
            }
            verdict = SniProbe.classifyHttp(status, redirect)
            if (verdict == Verdict.BLOCKED) notes.add("redirect looks like an ISP captive portal")
        } catch (e: java.net.SocketTimeoutException) {
            verdict = if (tlsOk) Verdict.REDIRECT else Verdict.DEAD
            notes.add("HTTP probe timed out")
        } catch (e: Exception) {
            verdict = if (tlsOk) Verdict.REDIRECT else Verdict.DEAD
            notes.add("HTTP probe failed: ${e.javaClass.simpleName}")
        }

        // 4) reverse DNS + consistency
        val reverse = try { InetAddress.getByName(targetIp).canonicalHostName.takeIf { it != targetIp } } catch (e: Exception) { null }

        return SniProbeResult(
            hostname = hostname, targetIp = targetIp, port = port, tlsHandshakeOk = tlsOk,
            httpStatus = status, httpRedirect = redirect, serverHeader = server,
            certCn = certCn, certSans = certSans, forwardDns = forward, reverseDns = reverse,
            dnsConsistent = targetIp in forward, verdict = verdict, notes = notes, elapsedMs = elapsed(),
        )
    }

    /** Probe many hostnames (deduped, ADR-6). Sequential — callers wanting
     *  concurrency can parallelize; the cap is [SniProbe.MAX_CONCURRENCY]. */
    fun scan(hostnames: List<String>, timeoutMs: Int = 5000, onResult: (SniProbeResult) -> Unit = {}): List<SniProbeResult> {
        val out = ArrayList<SniProbeResult>()
        for (h in SniProbe.dedupeHostnames(hostnames)) {
            val r = probeOne(h, timeoutMs = timeoutMs)
            out.add(r); onResult(r)
        }
        return out
    }

    /** Discover candidate hostnames for a domain via crt.sh. */
    fun discover(domain: String, timeoutMs: Int = 30000): List<SniCandidate> {
        val d = domain.trim().lowercase().trimStart('*', '.')
        if (d.isEmpty()) return emptyList()
        val url = CrtSh.URL_TEMPLATE.replace("{domain}", d)
        val req = Request.Builder().url(url).header("User-Agent", "InjectX-SNIHunter").build()
        httpClient(timeoutMs).newCall(req).execute().use { resp ->
            if (!resp.isSuccessful) return emptyList()
            val body = resp.body?.string() ?: return emptyList()
            val arr = json.parseToJsonElement(body) as? JsonArray ?: return emptyList()
            return CrtSh.parseCrtshRows(arr.filterIsInstance<JsonObject>())
        }
    }

    private fun cn(cert: X509Certificate): String? =
        Regex("CN=([^,]+)").find(cert.subjectX500Principal.name)?.groupValues?.get(1)

    private fun sans(cert: X509Certificate): List<String> = try {
        cert.subjectAlternativeNames?.mapNotNull { entry ->
            if ((entry[0] as? Int) == 2) entry[1] as? String else null
        } ?: emptyList()
    } catch (e: Exception) { emptyList() }
}
