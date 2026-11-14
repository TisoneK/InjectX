package com.injectx.app

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
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
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.injectx.app.ui.HexLogo
import com.injectx.app.ui.theme.Divider
import com.injectx.app.ui.theme.TextLo
import com.injectx.app.ui.theme.TextMid

@Composable
fun HomeScreen(onOpen: (Screen) -> Unit) {
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 20.dp)) {
        Spacer(Modifier.height(20.dp))
        Text("VPN tunnel config toolkit", style = MaterialTheme.typography.titleMedium, color = TextMid)

        Spacer(Modifier.height(28.dp))
        Text("Tools", style = MaterialTheme.typography.labelMedium, color = TextLo)
        Spacer(Modifier.height(4.dp))

        ToolRow(
            title = "Decode a config",
            subtitle = "Detect, decrypt and inspect .ehi, .hc, .ziv, .dark and .tls files.",
            onClick = { onOpen(Screen.Decode) },
        )
        HorizontalDivider(color = Divider)
        ToolRow(
            title = "SNI Hunter",
            subtitle = "Discover and probe bug hosts, then export the ones that work.",
            onClick = { onOpen(Screen.Sni) },
        )
        HorizontalDivider(color = Divider)

        Spacer(Modifier.height(28.dp))
        Text(
            "A research tool. Decoding configs you own is yours to do; using a discovered host may breach your ISP's terms.",
            style = MaterialTheme.typography.bodySmall, color = TextLo,
        )
        Spacer(Modifier.height(20.dp))
    }
}

@Composable
private fun ToolRow(title: String, subtitle: String, onClick: () -> Unit) {
    Row(
        Modifier.fillMaxWidth().clickable { onClick() }.padding(vertical = 18.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
            Text(title, style = MaterialTheme.typography.titleMedium)
            Text(subtitle, style = MaterialTheme.typography.bodySmall, color = TextMid)
        }
        Text("›", style = MaterialTheme.typography.titleLarge, color = TextLo)
    }
}
