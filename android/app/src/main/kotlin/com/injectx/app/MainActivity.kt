package com.injectx.app

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.provider.OpenableColumns
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.injectx.core.ParseEngine
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.jsonObject

/** UI state for the single screen. */
private sealed interface UiState {
    data object Idle : UiState
    data object Loading : UiState
    data class Loaded(val name: String, val config: JsonObject, val pretty: String) : UiState
    data class Failed(val name: String, val message: String) : UiState
}

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme(colorScheme = darkColorScheme()) { InjectXScreen() }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun InjectXScreen() {
    val prettyJson = remember { Json { prettyPrint = true } }
    var state by remember { mutableStateOf<UiState>(UiState.Idle) }
    val scope = rememberCoroutineScope()
    val ctx = androidx.compose.ui.platform.LocalContext.current

    val picker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri: Uri? ->
        if (uri == null) return@rememberLauncherForActivityResult
        state = UiState.Loading
        scope.launch {
            val name = displayName(ctx, uri)
            try {
                val result = withContext(Dispatchers.IO) {
                    val bytes = ctx.contentResolver.openInputStream(uri)?.use { it.readBytes() }
                        ?: error("could not read file")
                    ParseEngine.parseConfig(bytes, name)
                }
                state = UiState.Loaded(name, result, prettyJson.encodeToString(JsonObject.serializer(), result))
            } catch (e: Exception) {
                state = UiState.Failed(name, e.message ?: e.toString())
            }
        }
    }

    Scaffold(topBar = { TopAppBar(title = { Text("InjectX") }) }) { pad ->
        Column(
            Modifier.fillMaxSize().padding(pad).padding(16.dp).verticalScroll(rememberScrollState()),
        ) {
            Button(onClick = { picker.launch(arrayOf("*/*")) }, modifier = Modifier.fillMaxWidth()) {
                Text("Pick a config file")
            }
            Spacer(Modifier.height(16.dp))
            when (val s = state) {
                is UiState.Idle -> Text(
                    "Select a VPN tunnel config (.ehi, .hc, .ziv, .dark, .tls …) to detect, decrypt and inspect it.",
                    style = MaterialTheme.typography.bodyMedium,
                )
                is UiState.Loading -> Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                    CircularProgressIndicator(); Spacer(Modifier.height(0.dp)); Text("  Decoding…")
                }
                is UiState.Failed -> Text("Failed on ${s.name}: ${s.message}", color = MaterialTheme.colorScheme.error)
                is UiState.Loaded -> LoadedView(s, prettyJson) { shareText(ctx, it) }
            }
        }
    }
}

@Composable
private fun LoadedView(s: UiState.Loaded, prettyJson: Json, onExport: (String) -> Unit) {
    val n = s.config
    fun f(key: String): String? {
        val e = n[key]
        if (e !is JsonPrimitive) return null
        val c = e.content
        return if (c == "null") null else c
    }

    Text(s.name, style = MaterialTheme.typography.titleMedium)
    Spacer(Modifier.height(8.dp))
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(12.dp)) {
            Field("Format", f("format"))
            Field("Decryption", f("decryption_status"))
            Field("Scheme", f("scheme_used"))
            Field("Protocol", f("protocol"))
            Field("Host", f("host"))
            Field("Port", f("port"))
            Field("SSH server", f("ssh_server"))
            Field("SSH user", f("ssh_user"))
            Field("SNI", f("sni"))
            Field("Proxy", f("proxy_host"))
            Field("DNS", f("dns"))
        }
    }
    Spacer(Modifier.height(12.dp))
    OutlinedButton(onClick = { onExport(s.pretty) }, modifier = Modifier.fillMaxWidth()) {
        Text("Export normalized config (JSON)")
    }
    Spacer(Modifier.height(12.dp))
    Text("Normalized config", style = MaterialTheme.typography.titleSmall)
    Text(s.pretty, fontFamily = FontFamily.Monospace, fontSize = 11.sp)
}

@Composable
private fun Field(label: String, value: String?) {
    if (value.isNullOrEmpty()) return
    Row(Modifier.fillMaxWidth().padding(vertical = 2.dp), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, style = MaterialTheme.typography.labelMedium)
        Text(value, style = MaterialTheme.typography.bodyMedium)
    }
}

private fun displayName(ctx: android.content.Context, uri: Uri): String {
    var name = "config"
    try {
        ctx.contentResolver.query(uri, null, null, null, null)?.use { c ->
            val idx = c.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if (idx >= 0 && c.moveToFirst()) c.getString(idx)?.let { name = it }
        }
    } catch (_: Exception) {}
    return name
}

private fun shareText(ctx: android.content.Context, text: String) {
    val intent = Intent(Intent.ACTION_SEND).apply {
        type = "application/json"
        putExtra(Intent.EXTRA_TEXT, text)
    }
    ctx.startActivity(Intent.createChooser(intent, "Export config"))
}
