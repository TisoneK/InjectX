package com.injectx.core

import com.injectx.core.sni.CrtSh
import com.injectx.core.sni.DomainInput
import com.injectx.core.sni.Export
import com.injectx.core.sni.HostResult
import com.injectx.core.sni.HuntCodec
import com.injectx.core.sni.HuntPhase
import com.injectx.core.sni.HuntSession
import com.injectx.core.sni.SniProbe
import com.injectx.core.sni.SniProbeResult
import com.injectx.core.sni.SniScanJob
import com.injectx.core.sni.TestState
import com.injectx.core.sni.Verdict
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
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
    fun domainInputCleansEverySeparatorAndNoise() {
        // single, comma, semicolon, space, newline, scheme, path, port, wildcard,
        // inline + whole-line comments, blanks — all in one blob.
        val raw = """
            https://www.example.com/path?q=1
            CDN.Example.com:443 ; a.example.com, b.example.com
            *.wild.example.com   c.example.com
            # a comment line
            d.example.com # inline note
            not a host
            ..broken..
        """.trimIndent()
        val r = DomainInput.parse(raw)
        assertEquals(
            listOf("www.example.com", "cdn.example.com", "a.example.com", "b.example.com",
                "wild.example.com", "c.example.com", "d.example.com"),
            r.valid,
        )
        // "not a host" -> two invalid tokens ("not","a") + "host" is a valid single-label? no (needs a dot) -> 3 skipped; "..broken.." -> skipped
        assertTrue("some tokens are reported skipped", r.skipped.isNotEmpty())
        assertTrue(r.isReady)
    }

    @Test
    fun domainInputDedupesAndCountsDuplicates() {
        val r = DomainInput.parse("a.com\nA.COM\n a.com \nb.com\nb.com")
        assertEquals(listOf("a.com", "b.com"), r.valid)
        assertEquals(3, r.duplicates)
        assertEquals(0, r.skipped.size)
    }

    @Test
    fun domainInputEmptyIsNotReady() {
        val r = DomainInput.parse("\n# only a comment\n   \n")
        assertFalse(r.isReady)
        assertEquals(0, r.valid.size)
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

    @Test
    fun testStateMapsThreeWays() {
        assertEquals(TestState.WORKS, TestState.of(SniProbeResult("a", verdict = Verdict.WORKING)))
        assertEquals(TestState.TIMED_OUT, TestState.of(SniProbeResult("b", verdict = Verdict.DEAD, notes = listOf("TLS handshake timed out"))))
        assertEquals(TestState.FAILS, TestState.of(SniProbeResult("c", verdict = Verdict.DEAD, notes = listOf("DNS resolution failed"))))
        assertEquals(TestState.FAILS, TestState.of(SniProbeResult("d", verdict = Verdict.BLOCKED)))
    }

    @Test
    fun huntSessionResumeAndCounts() {
        val s = HuntSession(
            phase = HuntPhase.TESTING,
            testLabel = "Dataless Airtel",
            candidates = listOf("a.com", "b.com", "c.com", "d.com"),
            results = listOf(
                HostResult("a.com", TestState.WORKS, httpStatus = 200),
                HostResult("b.com", TestState.FAILS),
            ),
        )
        assertEquals(listOf("c.com", "d.com"), s.pending())   // resume frontier
        assertFalse(s.isComplete)
        assertEquals(1, s.working().size)
        assertEquals(1, s.counts()[TestState.WORKS])
    }

    @Test
    fun huntSessionRoundTripsThroughCodec() {
        val s = HuntSession(
            phase = HuntPhase.DISCOVERED,
            discoverLabel = "Work SIM",
            testLabel = null,
            candidates = listOf("x.com", "y.com"),
            results = listOf(HostResult("x.com", TestState.TIMED_OUT, note = "TLS handshake timed out", elapsedMs = 5001.0)),
            updatedAt = 1234L,
        )
        val back = HuntCodec.decode(HuntCodec.encode(s))
        assertEquals(s, back)
        assertNull(HuntCodec.decode("{ not json"))
    }

    @Test
    fun exportWorkingOnlyIsTaggedWithNetwork() {
        val s = HuntSession(
            testLabel = "Dataless Airtel",
            candidates = listOf("a.com", "b.com", "c.com"),
            results = listOf(
                HostResult("a.com", TestState.WORKS),
                HostResult("b.com", TestState.FAILS),
                HostResult("c.com", TestState.WORKS),
            ),
        )
        val txt = Export.working(s)
        assertTrue(txt.startsWith("# network: Dataless Airtel\n"))
        assertTrue(txt.contains("a.com\n"))
        assertTrue(txt.contains("c.com\n"))
        assertFalse(txt.contains("b.com"))
    }
}
