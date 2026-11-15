package com.injectx.app

import android.widget.Toast
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.CellTower
import androidx.compose.material.icons.outlined.ChevronRight
import androidx.compose.material.icons.outlined.DeleteOutline
import androidx.compose.material.icons.outlined.Description
import androidx.compose.material.icons.outlined.History
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material.icons.outlined.SignalCellularAlt
import androidx.compose.material.icons.outlined.Wifi
import androidx.compose.material.icons.outlined.WifiOff
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.injectx.app.ui.HexLogo
import com.injectx.app.ui.theme.Accent
import com.injectx.app.ui.theme.BadRed
import com.injectx.app.ui.theme.Cyan
import com.injectx.app.ui.theme.Outline
import com.injectx.app.ui.theme.Surface1
import com.injectx.app.ui.theme.Surface2
import com.injectx.app.ui.theme.TextHi
import com.injectx.app.ui.theme.TextLo
import com.injectx.app.ui.theme.TextMid
import com.injectx.core.history.ActivityEvent
import com.injectx.core.history.ActivityKind

/* ============================== Home tab ============================== */

@Composable
fun HomeScreen(onOpen: (Screen) -> Unit) {
    val ctx = LocalContext.current
    val net = rememberNetworkInfo()
    var refresh by remember { mutableStateOf(0) }
    val activity = remember(refresh) { ActivityStore.recent(ctx) }

    LazyColumn(
        Modifier.fillMaxSize().padding(horizontal = 20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        item { Spacer(Modifier.height(4.dp)); HeroBanner() }

        item {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Text("Tools", style = MaterialTheme.typography.titleMedium, modifier = Modifier.weight(1f))
                Surface(color = Surface2, shape = RoundedCornerShape(20.dp)) {
                    Text("2 tools", style = MaterialTheme.typography.labelMedium.copy(color = Cyan),
                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 5.dp))
                }
            }
        }

        item {
            ToolCard(Icons.Outlined.Description, Cyan, "Decode a config",
                "Detect, decrypt and inspect .ehi, .hc, .ziv, .dark and .tls files.") { onOpen(Screen.Decode) }
        }
        item {
            ToolCard(Icons.Outlined.CellTower, Accent, "SNI Hunter",
                "Discover candidate hosts on your network, then test which ones work on the dataless one.") { onOpen(Screen.Sni) }
        }

        item { NetworkPanel(net) { refresh++; Toast.makeText(ctx, "Network: ${net.label}", Toast.LENGTH_SHORT).show() } }

        item {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Icon(Icons.Outlined.History, null, tint = TextLo, modifier = Modifier.size(18.dp))
                Text("Recent activity", style = MaterialTheme.typography.titleMedium)
            }
        }

        if (activity.isEmpty()) {
            item {
                Surface(color = Surface1, shape = RoundedCornerShape(14.dp), modifier = Modifier.fillMaxWidth()) {
                    Text("Nothing yet. Decode a config or run an SNI test and it shows up here.",
                        style = MaterialTheme.typography.bodySmall, color = TextLo, modifier = Modifier.padding(16.dp))
                }
            }
        } else {
            items(activity) { e -> ActivityRow(e) { onOpen(if (e.kind == ActivityKind.SCAN) Screen.Sni else Screen.Decode) } }
        }

        item {
            Spacer(Modifier.height(4.dp))
            Text("A research tool. Decoding configs you own is yours to do; using a discovered host may breach your ISP's terms.",
                style = MaterialTheme.typography.bodySmall, color = TextLo)
            Spacer(Modifier.height(16.dp))
        }
    }
}

@Composable
private fun HeroBanner() {
    Surface(
        shape = RoundedCornerShape(20.dp),
        color = Surface1,
        border = BorderStroke(1.dp, Accent.copy(alpha = 0.30f)),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Row(
            Modifier
                .background(Brush.linearGradient(listOf(Accent.copy(alpha = 0.10f), Cyan.copy(alpha = 0.04f), Color.Transparent)))
                .padding(20.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text("Your VPN toolkit", style = MaterialTheme.typography.headlineSmall.copy(fontWeight = FontWeight.Bold), color = TextHi)
                Text("Decode, analyze and test VPN tunnel configs — offline, on your device.",
                    style = MaterialTheme.typography.bodyMedium, color = TextMid)
            }
            Spacer(Modifier.size(12.dp))
            HexLogo(Modifier.size(64.dp))
        }
    }
}

@Composable
fun ToolCard(icon: ImageVector, tint: Color, title: String, subtitle: String, onClick: () -> Unit) {
    Surface(
        color = Surface1,
        shape = RoundedCornerShape(16.dp),
        border = BorderStroke(1.dp, Outline),
        modifier = Modifier.fillMaxWidth().clickable { onClick() },
    ) {
        Row(Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(
                Modifier.size(56.dp).background(tint.copy(alpha = 0.14f), RoundedCornerShape(14.dp)),
                contentAlignment = Alignment.Center,
            ) { Icon(icon, null, tint = tint, modifier = Modifier.size(30.dp)) }
            Spacer(Modifier.size(14.dp))
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                Text(title, style = MaterialTheme.typography.titleMedium)
                Text(subtitle, style = MaterialTheme.typography.bodySmall, color = TextMid)
            }
            Spacer(Modifier.size(8.dp))
            Icon(Icons.Outlined.ChevronRight, null, tint = TextLo)
        }
    }
}

@Composable
private fun NetworkPanel(net: NetInfo, onCheck: () -> Unit) {
    val color = if (net.connected) Accent else BadRed
    val icon = when {
        !net.connected -> Icons.Outlined.WifiOff
        net.transport == "Cellular" -> Icons.Outlined.SignalCellularAlt
        else -> Icons.Outlined.Wifi
    }
    Surface(
        color = Surface1, shape = RoundedCornerShape(16.dp),
        border = BorderStroke(1.dp, color.copy(alpha = 0.35f)), modifier = Modifier.fillMaxWidth(),
    ) {
        Row(Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(icon, null, tint = color, modifier = Modifier.size(28.dp))
            Spacer(Modifier.size(14.dp))
            Column(Modifier.weight(1f)) {
                Text("Network status", style = MaterialTheme.typography.labelMedium, color = TextLo)
                Text(if (net.connected) "Connected · ${net.transport}" else "Offline",
                    style = MaterialTheme.typography.titleMedium, color = color)
            }
            OutlinedButton(onClick = onCheck, contentPadding = PaddingValues(horizontal = 14.dp, vertical = 8.dp)) {
                Icon(Icons.Outlined.Refresh, null, modifier = Modifier.size(16.dp))
                Spacer(Modifier.size(6.dp))
                Text("Check")
            }
        }
    }
}

@Composable
private fun ActivityRow(e: ActivityEvent, onClick: () -> Unit) {
    val icon = if (e.kind == ActivityKind.SCAN) Icons.Outlined.CellTower else Icons.Outlined.Description
    val tint = if (e.kind == ActivityKind.SCAN) Accent else Cyan
    Surface(color = Surface1, shape = RoundedCornerShape(12.dp),
        modifier = Modifier.fillMaxWidth().clickable { onClick() }) {
        Row(Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(38.dp).background(tint.copy(alpha = 0.14f), RoundedCornerShape(10.dp)), contentAlignment = Alignment.Center) {
                Icon(icon, null, tint = tint, modifier = Modifier.size(20.dp))
            }
            Spacer(Modifier.size(12.dp))
            Column(Modifier.weight(1f)) {
                Text(e.title, style = MaterialTheme.typography.bodyMedium, maxLines = 1, overflow = TextOverflow.Ellipsis)
                val sub = buildString {
                    if (e.subtitle.isNotBlank()) append(e.subtitle).append("  ·  ")
                    append(ActivityStore.ago(e.at))
                }
                Text(sub, style = MaterialTheme.typography.labelMedium, color = TextLo, maxLines = 1, overflow = TextOverflow.Ellipsis)
            }
            Icon(Icons.Outlined.ChevronRight, null, tint = TextLo)
        }
    }
}

/* ============================== Tools tab ============================== */

@Composable
fun ToolsScreen(onOpen: (Screen) -> Unit) {
    LazyColumn(Modifier.fillMaxSize().padding(horizontal = 20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        item { Spacer(Modifier.height(4.dp)); Text("Tools", style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold)) }
        item {
            ToolCard(Icons.Outlined.Description, Cyan, "Decode a config",
                "Detect, decrypt and inspect .ehi, .hc, .ziv, .dark and .tls files.") { onOpen(Screen.Decode) }
        }
        item {
            ToolCard(Icons.Outlined.CellTower, Accent, "SNI Hunter",
                "Discover candidate hosts on your network, then test which ones work on the dataless one.") { onOpen(Screen.Sni) }
        }
    }
}

/* ============================== Settings tab ============================== */

@Composable
fun SettingsScreen() {
    val ctx = LocalContext.current
    val version = remember {
        runCatching { ctx.packageManager.getPackageInfo(ctx.packageName, 0).versionName }.getOrNull() ?: "0.1.0"
    }

    LazyColumn(Modifier.fillMaxSize().padding(horizontal = 20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        item { Spacer(Modifier.height(4.dp)); Text("Settings", style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold)) }

        item {
            Surface(color = Surface1, shape = RoundedCornerShape(16.dp), border = BorderStroke(1.dp, Outline), modifier = Modifier.fillMaxWidth()) {
                Row(Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
                    HexLogo(Modifier.size(44.dp))
                    Spacer(Modifier.size(14.dp))
                    Column(Modifier.weight(1f)) {
                        Text("InjectX", style = MaterialTheme.typography.titleMedium)
                        Text("v$version · offline VPN tunnel config toolkit", style = MaterialTheme.typography.bodySmall, color = TextMid)
                    }
                }
            }
        }

        item { Text("Data", style = MaterialTheme.typography.labelMedium, color = TextLo) }
        item {
            SettingRow(Icons.Outlined.DeleteOutline, "Clear recent activity", "Remove the home-screen history.") {
                ActivityStore.clear(ctx); Toast.makeText(ctx, "Recent activity cleared", Toast.LENGTH_SHORT).show()
            }
        }
        item {
            SettingRow(Icons.Outlined.DeleteOutline, "Clear saved SNI hunt", "Discard the saved candidate list and test results.") {
                HuntStore.clear(ctx); Toast.makeText(ctx, "Saved hunt cleared", Toast.LENGTH_SHORT).show()
            }
        }

        item {
            Spacer(Modifier.height(4.dp))
            Text("A research tool for configs and networks you are authorised to test. Using a discovered host may breach your ISP's terms — that's on you.",
                style = MaterialTheme.typography.bodySmall, color = TextLo)
        }
    }
}

@Composable
private fun SettingRow(icon: ImageVector, title: String, subtitle: String, onClick: () -> Unit) {
    Surface(color = Surface1, shape = RoundedCornerShape(12.dp), modifier = Modifier.fillMaxWidth().clickable { onClick() }) {
        Row(Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(icon, null, tint = TextMid, modifier = Modifier.size(22.dp))
            Spacer(Modifier.size(14.dp))
            Column(Modifier.weight(1f)) {
                Text(title, style = MaterialTheme.typography.bodyMedium)
                Text(subtitle, style = MaterialTheme.typography.labelMedium, color = TextLo)
            }
        }
    }
}
