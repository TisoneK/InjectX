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

    private fun csvCell(v: String): String =
        if (v.any { it == ',' || it == '"' || it == '\n' || it == '\r' }) "\"" + v.replace("\"", "\"\"") + "\"" else v
}
