package com.injectx.app

import android.content.Context
import android.text.format.DateUtils
import com.injectx.core.history.ActivityEvent
import com.injectx.core.history.ActivityKind
import com.injectx.core.history.ActivityLog
import java.io.File

/**
 * filesDir persistence for the Home screen's recent activity (features/
 * android-ui.md §12). Real data only — a row is appended when the user
 * actually decodes a config or finishes an SNI test.
 */
object ActivityStore {
    private const val FILE = "activity.json"

    private fun file(ctx: Context) = File(ctx.filesDir, FILE)

    fun recent(ctx: Context): List<ActivityEvent> = runCatching {
        val f = file(ctx)
        if (f.exists()) ActivityLog.decode(f.readText()) else emptyList()
    }.getOrDefault(emptyList())

    fun record(ctx: Context, kind: ActivityKind, title: String, subtitle: String) {
        runCatching {
            val updated = ActivityLog.prepend(recent(ctx), ActivityEvent(kind, title, subtitle, System.currentTimeMillis()))
            file(ctx).writeText(ActivityLog.encode(updated))
        }
    }

    fun clear(ctx: Context) {
        runCatching { file(ctx).delete() }
    }

    /** "2 hours ago" — real relative time from the system. */
    fun ago(at: Long): String =
        DateUtils.getRelativeTimeSpanString(at, System.currentTimeMillis(), DateUtils.MINUTE_IN_MILLIS).toString()
}
