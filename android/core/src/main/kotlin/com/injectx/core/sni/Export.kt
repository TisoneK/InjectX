package com.injectx.core.sni

import kotlinx.serialization.json.Json

/**
 * Scan-result exporters — port of `backend/snihunter/export.py`.
 *   txt  — one working host per line (drop straight into a config's `sni`)
 *   csv  — hostname,ip,http_status,verdict,server,redirect
 *   json — the full job
 */
object Export {

    private val prettyJson = Json { prettyPrint = true }

    fun toTxt(job: SniScanJob): String =
        job.results.filter { it.verdict == Verdict.WORKING }.joinToString("") { it.hostname + "\n" }

    fun toCsv(job: SniScanJob): String {
        val sb = StringBuilder()
        sb.append("hostname,ip,http_status,verdict,server,redirect\r\n")
        for (r in job.results) {
            sb.append(csvCell(r.hostname)).append(',')
                .append(csvCell(r.targetIp ?: "")).append(',')
                .append(r.httpStatus?.toString() ?: "").append(',')
                .append(r.verdict.wire).append(',')
                .append(csvCell(r.serverHeader ?: "")).append(',')
                .append(csvCell(r.httpRedirect ?: "")).append("\r\n")
        }
        return sb.toString()
    }

    fun toJson(job: SniScanJob): String = prettyJson.encodeToString(SniScanJob.serializer(), job)

    /**
     * Working-only export for a two-phase hunt (§11.11), tagged with the test
     * network's label so a host that works on one network is never mistaken
     * for working everywhere. One host per line; a `#` header records the
     * network and date for the person reading the file later.
     */
    fun working(session: HuntSession): String {
        val sb = StringBuilder()
        session.testLabel?.takeIf { it.isNotBlank() }?.let { sb.append("# network: ").append(it).append('\n') }
        sb.append("# working SNI hosts (").append(session.working().size).append(")\n")
        for (r in session.working()) sb.append(r.hostname).append('\n')
        return sb.toString()
    }

    fun toJson(session: HuntSession): String = prettyJson.encodeToString(HuntSession.serializer(), session)

    private fun csvCell(v: String): String =
        if (v.any { it == ',' || it == '"' || it == '\n' || it == '\r' }) "\"" + v.replace("\"", "\"\"") + "\"" else v
}
