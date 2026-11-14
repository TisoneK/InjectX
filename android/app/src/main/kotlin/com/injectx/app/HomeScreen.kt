package com.injectx.app

import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.injectx.app.ui.HexLogo
import com.injectx.app.ui.theme.Cyan
import com.injectx.app.ui.theme.NeonGreen
import com.injectx.app.ui.theme.Surface2
import com.injectx.app.ui.theme.TextHi
import com.injectx.app.ui.theme.TextLo

@Composable
fun HomeScreen(onOpen: (Screen) -> Unit) {
    val pulse = rememberInfiniteTransition(label = "pulse")
    val scale by pulse.animateFloat(
        initialValue = 1f, targetValue = 1.05f,
        animationSpec = infiniteRepeatable(tween(1800), RepeatMode.Reverse), label = "scale",
    )

    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Spacer(Modifier.height(16.dp))
        HexLogo(Modifier.size(112.dp).scale(scale))
        Spacer(Modifier.height(18.dp))
        Text("INJECTX", fontFamily = FontFamily.Monospace, color = TextHi, fontSize = 26.sp, letterSpacing = 6.sp)
        Spacer(Modifier.height(6.dp))
        Text("VPN tunnel config toolkit", style = MaterialTheme.typography.bodyMedium, color = TextLo)
        Spacer(Modifier.height(14.dp))
        StatusLine()
        Spacer(Modifier.height(28.dp))

        ToolModule(
            accent = NeonGreen,
            title = "Decode a config",
            desc = "Detect, decrypt and inspect .ehi / .hc / .ziv / .dark / .tls files.",
            onClick = { onOpen(Screen.Decode) },
        )
        Spacer(Modifier.height(14.dp))
        ToolModule(
            accent = Cyan,
            title = "SNI Hunter",
            desc = "Discover and probe bug hosts, then export the working ones.",
            onClick = { onOpen(Screen.Sni) },
        )

        Spacer(Modifier.height(28.dp))
        Text(
            "Research tool. Decoding configs you own is yours to do; using discovered hosts may breach your ISP's terms.",
            style = MaterialTheme.typography.labelSmall, color = TextLo,
            modifier = Modifier.padding(horizontal = 8.dp),
        )
        Spacer(Modifier.height(16.dp))
    }
}

@Composable
private fun StatusLine() {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Box(Modifier.size(7.dp).clip(CircleShape).background(NeonGreen))
        Text(
            "core ready · schemes A5·B2·H1·I1 · sni armed",
            fontFamily = FontFamily.Monospace, fontSize = 11.sp, color = TextLo, letterSpacing = 0.5.sp,
        )
    }
}

@Composable
private fun ToolModule(accent: Color, title: String, desc: String, onClick: () -> Unit) {
    Card(
        Modifier.fillMaxWidth().clickable { onClick() },
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(1.dp, accent.copy(alpha = 0.35f)),
    ) {
        Row(Modifier.fillMaxWidth().height(96.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.width(4.dp).fillMaxSize().background(accent))
            Column(Modifier.weight(1f).padding(horizontal = 16.dp, vertical = 14.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Box(Modifier.size(8.dp).clip(CircleShape).background(accent))
                    Text(title, style = MaterialTheme.typography.titleMedium, color = TextHi)
                }
                Spacer(Modifier.height(6.dp))
                Text(desc, style = MaterialTheme.typography.bodySmall, color = TextLo)
            }
            Text("›", color = accent, fontSize = 26.sp, modifier = Modifier.padding(end = 18.dp))
        }
    }
}
