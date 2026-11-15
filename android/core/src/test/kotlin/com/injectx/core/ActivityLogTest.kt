package com.injectx.core

import com.injectx.core.history.ActivityEvent
import com.injectx.core.history.ActivityKind
import com.injectx.core.history.ActivityLog
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ActivityLogTest {

    @Test
    fun prependKeepsNewestFirstAndCaps() {
        var log = emptyList<ActivityEvent>()
        for (i in 1..ActivityLog.CAP + 5) {
            log = ActivityLog.prepend(log, ActivityEvent(ActivityKind.DECODE, "config $i", at = i.toLong()))
        }
        assertEquals(ActivityLog.CAP, log.size)
        assertEquals("config ${ActivityLog.CAP + 5}", log.first().title) // newest first
    }

    @Test
    fun roundTripsThroughCodec() {
        val events = listOf(
            ActivityEvent(ActivityKind.DECODE, "Config decoded", "profile.ehi · EHI", 1000L),
            ActivityEvent(ActivityKind.SCAN, "SNI test completed", "4 working · Dataless Airtel", 2000L),
        )
        assertEquals(events, ActivityLog.decode(ActivityLog.encode(events)))
    }

    @Test
    fun decodeOfGarbageIsEmpty() {
        assertTrue(ActivityLog.decode("{not json").isEmpty())
        assertTrue(ActivityLog.decode("").isEmpty())
    }
}
