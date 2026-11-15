package com.injectx.core.history

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

/**
 * Recent-activity log for the Home screen (features/android-ui.md §12).
 *
 * The home screen shows REAL activity, never decorative placeholders: a row is
 * written only when the user actually decodes a config or finishes an SNI test.
 * This model + codec are pure and unit-tested; the app persists the encoded
 * string to filesDir and renders the newest few.
 */

@Serializable
enum class ActivityKind {
    @SerialName("decode") DECODE,
    @SerialName("scan") SCAN,
}

@Serializable
data class ActivityEvent(
    val kind: ActivityKind,
    val title: String,
    val subtitle: String = "",
    val at: Long = 0L,
)

object ActivityLog {
    const val CAP = 30
    private val json = Json { ignoreUnknownKeys = true; encodeDefaults = true }

    fun encode(events: List<ActivityEvent>): String =
        json.encodeToString(kotlinx.serialization.builtins.ListSerializer(ActivityEvent.serializer()), events)

    fun decode(text: String): List<ActivityEvent> = try {
        json.decodeFromString(kotlinx.serialization.builtins.ListSerializer(ActivityEvent.serializer()), text)
    } catch (e: Exception) {
        emptyList()
    }

    /** Prepend the newest event and keep at most [CAP] (newest first). */
    fun prepend(existing: List<ActivityEvent>, event: ActivityEvent): List<ActivityEvent> =
        (listOf(event) + existing).take(CAP)
}
