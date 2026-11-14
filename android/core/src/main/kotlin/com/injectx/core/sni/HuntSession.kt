package com.injectx.core.sni

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

/**
 * The persistent SNI-Hunter session (features/android-ui.md §11.7–11).
 *
 * A hunt runs in two phases on two networks:
 *   1. DISCOVER on the real network — crt.sh (or a pasted/imported list)
 *      produces the [candidates].
 *   2. TEST on a dataless network — the user switches SIM/Wi-Fi and probes
 *      which candidates actually work.
 *
 * The whole thing is serialized to `filesDir` by the app so it survives the
 * network switch, an app restart and a dropped connection, and the test can
 * RESUME from where it stopped. Results are 3-state (works / fails / timed
 * out); export is working-only, tagged with the test network's label.
 *
 * This model + its [HuntCodec] are pure and unit-tested; the filesDir I/O is
 * a thin app-side wrapper.
 */

@Serializable
enum class HuntPhase {
    @SerialName("input") INPUT,          // collecting hosts
    @SerialName("discovered") DISCOVERED, // candidates ready; waiting for test network
    @SerialName("testing") TESTING,      // probing on the dataless network
    @SerialName("done") DONE,
}

@Serializable
enum class TestState {
    @SerialName("untested") UNTESTED,
    @SerialName("works") WORKS,
    @SerialName("fails") FAILS,
    @SerialName("timed_out") TIMED_OUT;

    companion object {
        /** Map a live probe result to a 3-state test outcome (§11.11). */
        fun of(r: SniProbeResult): TestState = when {
            r.verdict == Verdict.WORKING -> WORKS
            r.notes.any { it.contains("timeout", ignoreCase = true) || it.contains("timed out", ignoreCase = true) } -> TIMED_OUT
            else -> FAILS
        }
    }
}

@Serializable
data class HostResult(
    val hostname: String,
    val state: TestState = TestState.UNTESTED,
    @SerialName("http_status") val httpStatus: Int? = null,
    @SerialName("target_ip") val targetIp: String? = null,
    val note: String? = null,
    @SerialName("elapsed_ms") val elapsedMs: Double = 0.0,
) {
    companion object {
        fun from(r: SniProbeResult): HostResult = HostResult(
            hostname = r.hostname,
            state = TestState.of(r),
            httpStatus = r.httpStatus,
            targetIp = r.targetIp,
            note = r.notes.firstOrNull(),
            elapsedMs = r.elapsedMs,
        )
    }
}

@Serializable
data class HuntSession(
    val phase: HuntPhase = HuntPhase.INPUT,
    @SerialName("discover_label") val discoverLabel: String? = null,
    @SerialName("test_label") val testLabel: String? = null,
    val candidates: List<String> = emptyList(),
    val results: List<HostResult> = emptyList(),
    @SerialName("updated_at") val updatedAt: Long = 0L,
) {
    /** Hosts not yet tested — the RESUME frontier (§11.10). */
    fun pending(): List<String> {
        val tested = results.mapTo(HashSet()) { it.hostname }
        return candidates.filter { it !in tested }
    }

    fun working(): List<HostResult> = results.filter { it.state == TestState.WORKS }
    fun counts(): Map<TestState, Int> = results.groupingBy { it.state }.eachCount()
    val isComplete: Boolean get() = candidates.isNotEmpty() && pending().isEmpty()
}

/** Pure (de)serialization — the app writes/reads the returned string to filesDir. */
object HuntCodec {
    private val json = Json { ignoreUnknownKeys = true; encodeDefaults = true; prettyPrint = true }

    fun encode(session: HuntSession): String = json.encodeToString(HuntSession.serializer(), session)

    fun decode(text: String): HuntSession? = try {
        json.decodeFromString(HuntSession.serializer(), text)
    } catch (e: Exception) {
        null
    }
}
