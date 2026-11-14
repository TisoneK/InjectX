package com.injectx.app

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext

/**
 * Live network indicator for the SNI test step (features/android-ui.md §11.9).
 * The user has to SWITCH to a dataless network before testing; the UI shows
 * what's connected now so the switch is visible, and recomposes on change
 * (which is also how a dropped connection surfaces for resume).
 */
data class NetInfo(val connected: Boolean, val transport: String) {
    val label: String get() = if (connected) transport else "Offline"
}

private fun current(ctx: Context): NetInfo {
    val cm = ctx.getSystemService(ConnectivityManager::class.java) ?: return NetInfo(false, "Offline")
    val caps = cm.activeNetwork?.let { cm.getNetworkCapabilities(it) } ?: return NetInfo(false, "Offline")
    val transport = when {
        caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) -> "Wi-Fi"
        caps.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR) -> "Cellular"
        caps.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET) -> "Ethernet"
        else -> "Connected"
    }
    val online = caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
    return NetInfo(online, transport)
}

@Composable
fun rememberNetworkInfo(): NetInfo {
    val ctx = LocalContext.current
    var info by remember { mutableStateOf(current(ctx)) }
    DisposableEffect(Unit) {
        val cm = ctx.getSystemService(ConnectivityManager::class.java)
        val cb = object : ConnectivityManager.NetworkCallback() {
            override fun onAvailable(network: Network) { info = current(ctx) }
            override fun onLost(network: Network) { info = current(ctx) }
            override fun onCapabilitiesChanged(network: Network, caps: NetworkCapabilities) { info = current(ctx) }
        }
        runCatching { cm?.registerDefaultNetworkCallback(cb) }
        onDispose { runCatching { cm?.unregisterNetworkCallback(cb) } }
    }
    return info
}
