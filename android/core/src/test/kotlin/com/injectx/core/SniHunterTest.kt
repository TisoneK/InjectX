package com.injectx.core

import com.injectx.core.sni.CrtSh
import com.injectx.core.sni.Export
import com.injectx.core.sni.Seedlist
import com.injectx.core.sni.SniProbe
import com.injectx.core.sni.SniProbeResult
import com.injectx.core.sni.SniScanJob
import com.injectx.core.sni.Verdict
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** Parity tests for the SNI Hunter pure logic (port of backend/snihunter). */
class SniHunterTest {

    @Test
    fun classifyHttpMatchesPython() {
        assertEquals(Verdict.WORKING, SniProbe.classifyHttp(200))
        assertEquals(Verdict.WORKING, SniProbe.classifyHttp(404))
        assertEquals(Verdict.BLOCKED, SniProbe.classifyHttp(302, "http://portal.isp/topup"))
        assertEquals(Verdict.REDIRECT, SniProbe.classifyHttp(302, "http://example.com"))
        assertEquals(Verdict.DEAD, SniProbe.classifyHttp(500))
        assertEquals(Verdict.DEAD, SniProbe.classifyHttp(null))
    }

    @Test
    fun captivePortalDetection() {
        assertTrue(SniProbe.looksLikeCaptivePortal("https://selfcare.safaricom.co.ke/recharge"))
        assertTrue(SniProbe.looksLikeCaptivePortal("http://x/no-balance"))
        assertEquals(false, SniProbe.looksLikeCaptivePortal("https://www.google.com"))
        assertEquals(false, SniProbe.looksLikeCaptivePortal(null))
    }

    @Test
    fun dedupePreservesOrderAndNormalizes() {
        assertEquals(
            listOf("a.com", "b.com"),
            SniProbe.dedupeHostnames(listOf("A.com", " a.com ", "b.com", "B.COM", "")),
        )
    }

    @Test
    fun bundledSeedlistsMatchPythonCounts() {
        val airtel = Seedlist.loadBundled("airtel-ke.txt")
        assertEquals(13, airtel.size)
        assertEquals("free.facebook.com", airtel.first().hostname)
        assertEquals("ajax.googleapis.com", airtel.last().hostname)

        val saf = Seedlist.loadBundled("safaricom-ke.txt")
        assertEquals(19, saf.size)
        assertEquals("free.facebook.com", saf.first().hostname)
        assertEquals("fonts.gstatic.com", saf.last().hostname)

        val telkom = Seedlist.loadBundled("telkom-ke.txt")
        assertEquals(10, telkom.size)
        assertEquals("www.telkom.co.ke", telkom.first().hostname)
        assertEquals("fonts.gstatic.com", telkom.last().hostname)

        // all normalized: lowercase, no leading wildcard/dot
        assertTrue(saf.all { it.hostname == it.hostname.lowercase() && !it.hostname.startsWith("*") && !it.hostname.startsWith(".") })
    }

    @Test
    fun crtshParsingDedupesAndCleans() {
        val row = buildJsonObject {
            put("name_value", "*.example.com\nwww.example.com\nbad name\nuser@example.com")
            put("common_name", "example.com")
            put("issuer_ca_id", 123)
            put("not_before", "2026-01-01")
            put("not_after", "2026-12-31")
        }
        val cands = CrtSh.parseCrtshRows(listOf(row))
        assertEquals(listOf("example.com", "www.example.com"), cands.map { it.hostname })
        assertEquals(123, cands.first().issuerCaId)
        assertEquals("crt.sh", cands.first().source)
    }

    @Test
    fun exportTxtAndCsv() {
        val job = SniScanJob(
            jobId = "j1",
            results = listOf(
                SniProbeResult(hostname = "a.com", verdict = Verdict.WORKING, httpStatus = 200, targetIp = "1.2.3.4"),
                SniProbeResult(hostname = "b.com", verdict = Verdict.DEAD),
                SniProbeResult(hostname = "c.com", verdict = Verdict.WORKING, httpStatus = 403),
            ),
        )
        assertEquals("a.com\nc.com\n", Export.toTxt(job))
        val csv = Export.toCsv(job)
        assertTrue(csv.startsWith("hostname,ip,http_status,verdict,server,redirect\r\n"))
        assertTrue(csv.contains("a.com,1.2.3.4,200,working,,"))
        assertTrue(csv.contains("b.com,,,dead,,"))
    }
}
