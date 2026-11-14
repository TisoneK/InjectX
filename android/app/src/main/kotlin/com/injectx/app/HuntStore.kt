package com.injectx.app

import android.content.Context
import com.injectx.core.sni.HuntCodec
import com.injectx.core.sni.HuntSession
import java.io.File

/**
 * filesDir persistence for the SNI hunt (features/android-ui.md §11.8).
 *
 * The candidate list + results are written to one small JSON file after every
 * probe, so the hunt survives the network switch, an app restart and a dropped
 * connection — and the test can resume from the saved frontier. Pure encoding
 * lives in [HuntCodec]; this only owns the file.
 */
object HuntStore {
    private const val FILE = "sni_hunt.json"

    private fun file(ctx: Context) = File(ctx.filesDir, FILE)

    fun load(ctx: Context): HuntSession? = runCatching {
        val f = file(ctx)
        if (f.exists()) HuntCodec.decode(f.readText()) else null
    }.getOrNull()

    fun save(ctx: Context, session: HuntSession) {
        runCatching { file(ctx).writeText(HuntCodec.encode(session.copy(updatedAt = System.currentTimeMillis()))) }
    }

    fun clear(ctx: Context) {
        runCatching { file(ctx).delete() }
    }
}
