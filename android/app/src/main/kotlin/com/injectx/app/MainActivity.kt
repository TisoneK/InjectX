package com.injectx.app

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.provider.OpenableColumns
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.injectx.app.ui.HexLogo
import com.injectx.app.ui.formatColor
import com.injectx.app.ui.statusColor
import com.injectx.app.ui.theme.InjectXTheme
import com.injectx.app.ui.theme.MonoValue
import com.injectx.core.ParseEngine
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive

private sealed interface UiState {
    data object Idle : UiState
    data class Loading(val name: String) : UiState
    data class Loaded(val name: String, val config: JsonObject, val pretty: String) : UiState
    data class Failed(val name: String, val message: String) : UiState
}

private val SUPPORTED = listOf("ehi", "hc", "ziv", "dark", "tls", "npv", "nsh", "vhd", "hat")

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { InjectXTheme { InjectXApp() } }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun InjectXApp() {
    val prettyJson = remember { Json { prettyPrint = true } }
    var state by remember { mutableStateOf<UiState>(UiState.Idle) }
    val scope = rememberCoroutineScope()
    val ctx = LocalContext.current
    val clipboard = LocalClipboardManager.current
    val snackbar = remember { SnackbarHostState() }

    fun copy(label: String, value: String) {
        clipboard.setText(AnnotatedString(value))
        scope.launch { snackbar.showSnackbar("Copied $label") }
    }

    val picker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri: Uri? ->
        if (uri == null) return@rememberLauncherForActivityResult
        val name = displayName(ctx, uri)
        state = UiState.Loading(name)
        scope.launch {
            state = try {
                val cfg = withContext(Dispatchers.IO) {
                    val bytes = ctx.contentResolver.openInputStream(uri)?.use { it.readBytes() } ?: error("could not read file")
                    ParseEngine.parseConfig(bytes, name)
                }
                UiState.Loaded(name, cfg, prettyJson.encodeToString(JsonObject.serializer(), cfg))
            } catch (e: Exception) {
                UiState.Failed(name, e.message ?: e.toString())
            }
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        HexLogo(Modifier.size(28.dp))
                        Spacer(Modifier.width(10.dp))
                        Text("InjectX", fontFamily = FontFamily.Monospace, letterSpacing = 2.sp)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.background,
                    titleContentColor = MaterialTheme.colorScheme.onBackground,
                ),
            )
        },
        snackbarHost = { SnackbarHost(snackbar) },
        containerColor = MaterialTheme.colorScheme.background,
    ) { pad ->
        Box(Modifier.fillMaxSize().padding(pad)) {
            when (val s = state) {
                is UiState.Idle -> EmptyState { picker.launch(arrayOf("*/*")) }
                is UiState.Loading -> LoadingState(s.name)
                is UiState.Failed -> ErrorState(s.name, s.message) { picker.launch(arrayOf("*/*")) }
                is UiState.Loaded -> ResultView(s, onPickAnother = { picker.launch(arrayOf("*/*")) },
                    onExport = { shareText(ctx, it) }, onCopy = ::copy)
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun EmptyState(onPick: () -> Unit) {
    Column(
        Modifier.fillMaxSize().padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        HexLogo(Modifier.size(132.dp))
        Spacer(Modifier.height(20.dp))
        Text("InjectX", style = MaterialTheme.typography.headlineMedium, fontFamily = FontFamily.Monospace)
        Spacer(Modifier.height(6.dp))
        Text(
            "Detect, decrypt and inspect VPN tunnel configs",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Spacer(Modifier.height(28.dp))
        Button(onClick = onPick, modifier = Modifier.fillMaxWidth()) {
            Text("Open a config file")
        }
        Spacer(Modifier.height(24.dp))
        Text("SUPPORTED", style = MaterialTheme.typography.labelMedium)
        Spacer(Modifier.height(10.dp))
        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            SUPPORTED.forEach { Pill(it.uppercase(), formatColor(it)) }
        }
    }
}

@Composable
private fun LoadingState(name: String) {
    Column(Modifier.fillMaxSize(), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
        CircularProgressIndicator(color = MaterialTheme.colorScheme.primary)
        Spacer(Modifier.height(16.dp))
        Text("Decoding", style = MaterialTheme.typography.titleMedium)
        Text(name, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
            maxLines = 1, overflow = TextOverflow.Ellipsis)
    }
}

@Composable
private fun ErrorState(name: String, message: String, onRetry: () -> Unit) {
    Column(Modifier.fillMaxSize().padding(24.dp), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
        Text("Could not decode", style = MaterialTheme.typography.titleLarge, color = MaterialTheme.colorScheme.error)
        Spacer(Modifier.height(8.dp))
        Text(name, style = MaterialTheme.typography.bodyMedium)
        Spacer(Modifier.height(4.dp))
        Text(message, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Spacer(Modifier.height(24.dp))
        OutlinedButton(onClick = onRetry) { Text("Try another file") }
    }
}

@Composable
private fun ResultView(s: UiState.Loaded, onPickAnother: () -> Unit, onExport: (String) -> Unit, onCopy: (String, String) -> Unit) {
    val n = s.config
    fun f(key: String): String? {
        val e = n[key]
        if (e !is JsonPrimitive) return null
        val c = e.content
        return if (c == "null" || c.isEmpty()) null else c
    }
    val warnings = (n["warnings"] as? JsonArray)?.mapNotNull { (it as? JsonPrimitive)?.content } ?: emptyList()

    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp)) {
        // Header
        Card(Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
            Column(Modifier.padding(16.dp)) {
                Text(s.name, style = MaterialTheme.typography.titleMedium, maxLines = 2, overflow = TextOverflow.Ellipsis)
                Spacer(Modifier.height(12.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    f("format")?.let { Pill(it.uppercase(), formatColor(it)) }
                    f("decryption_status")?.let { Pill(it.replace('_', ' '), statusColor(it)) }
                    f("scheme_used")?.let { Pill(it, MaterialTheme.colorScheme.secondary) }
                }
            }
        }
        Spacer(Modifier.height(12.dp))

        // Connection details
        val rows = listOf(
            "Host" to f("host"), "Port" to f("port"), "Protocol" to f("protocol"),
            "SNI / bug host" to (f("sni") ?: f("bug_host")),
            "SSH server" to f("ssh_server"), "SSH port" to f("ssh_port"),
            "SSH user" to f("ssh_user"), "SSH pass" to f("ssh_pass"),
            "Proxy" to f("proxy_host"), "Proxy port" to f("proxy_port"),
            "DNS" to f("dns"), "Remote DNS" to f("remote_dns"),
        ).filter { it.second != null }
        if (rows.isNotEmpty()) {
            SectionCard("CONNECTION") {
                rows.forEachIndexed { i, (label, value) ->
                    FieldRow(label, value!!) { onCopy(label, value) }
                    if (i < rows.lastIndex) Spacer(Modifier.height(2.dp))
                }
            }
            Spacer(Modifier.height(12.dp))
        }

        if (warnings.isNotEmpty()) {
            SectionCard("WARNINGS", accent = MaterialTheme.colorScheme.error) {
                warnings.forEach {
                    Text("• $it", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Spacer(Modifier.height(6.dp))
                }
            }
            Spacer(Modifier.height(12.dp))
        }

        // Raw JSON (expandable)
        var expanded by remember { mutableStateOf(false) }
        SectionCard("NORMALIZED CONFIG") {
            TextButton(onClick = { expanded = !expanded }, contentPadding = androidx.compose.foundation.layout.PaddingValues(0.dp)) {
                Text(if (expanded) "Hide JSON" else "Show JSON", color = MaterialTheme.colorScheme.primary)
            }
            if (expanded) {
                Spacer(Modifier.height(6.dp))
                Surface(color = MaterialTheme.colorScheme.background, shape = RoundedCornerShape(10.dp), modifier = Modifier.fillMaxWidth()) {
                    Text(s.pretty, style = MonoValue.copy(fontSize = 11.sp), modifier = Modifier.padding(12.dp))
                }
            }
        }
        Spacer(Modifier.height(16.dp))

        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Button(onClick = { onExport(s.pretty) }, modifier = Modifier.weight(1f)) { Text("Export JSON") }
            OutlinedButton(onClick = onPickAnother, modifier = Modifier.weight(1f)) { Text("Open another") }
        }
        Spacer(Modifier.height(24.dp))
    }
}

// ── small reusable pieces ──────────────────────────────────────────────────
@Composable
private fun Pill(text: String, color: Color) {
    Surface(
        color = color.copy(alpha = 0.14f),
        contentColor = color,
        shape = RoundedCornerShape(8.dp),
        border = BorderStroke(1.dp, color.copy(alpha = 0.5f)),
    ) {
        Text(text, style = MaterialTheme.typography.labelMedium.copy(color = color),
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp))
    }
}

@Composable
private fun SectionCard(title: String, accent: Color = MaterialTheme.colorScheme.primary, content: @Composable () -> Unit) {
    Card(Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
        Column(Modifier.padding(16.dp)) {
            Text(title, style = MaterialTheme.typography.labelMedium.copy(color = accent, letterSpacing = 1.5.sp))
            Spacer(Modifier.height(10.dp))
            content()
        }
    }
}

@Composable
private fun FieldRow(label: String, value: String, onCopy: () -> Unit) {
    Row(Modifier.fillMaxWidth().padding(vertical = 6.dp), verticalAlignment = Alignment.CenterVertically) {
        Text(label, style = MaterialTheme.typography.labelMedium, modifier = Modifier.width(120.dp))
        Text(value, style = MonoValue, modifier = Modifier.weight(1f), maxLines = 2, overflow = TextOverflow.Ellipsis)
        TextButton(onClick = onCopy, contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 8.dp)) {
            Text("Copy", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.primary)
        }
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
