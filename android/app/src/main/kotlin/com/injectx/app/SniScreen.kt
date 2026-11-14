package com.injectx.app

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.injectx.app.ui.Pill
import com.injectx.app.ui.SectionCard
import com.injectx.app.ui.SegmentedTabs
import com.injectx.app.ui.theme.MonoValue
import com.injectx.app.ui.verdictColor
import com.injectx.core.sni.Export
import com.injectx.core.sni.Seedlist
import com.injectx.core.sni.SniNetwork
import com.injectx.core.sni.SniProbe
import com.injectx.core.sni.SniProbeResult
import com.injectx.core.sni.SniScanJob
import com.injectx.core.sni.Verdict
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@Composable
fun SniScreen(onExport: (String) -> Unit) {
    val scope = rememberCoroutineScope()
    var mode by remember { mutableIntStateOf(0) } // 0 = seedlist, 1 = domain
    var seedlist by remember { mutableStateOf(Seedlist.BUNDLED.first()) }
    var domain by remember { mutableStateOf("") }
    var scanning by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var total by remember { mutableIntStateOf(0) }
    val results = remember { mutableStateListOf<SniProbeResult>() }

    fun start() {
        error = null
        results.clear()
        scanning = true
        scope.launch {
            try {
                val hosts = withContext(Dispatchers.IO) {
                    if (mode == 0) Seedlist.loadBundled(seedlist).map { it.hostname }
                    else SniNetwork.discover(domain.trim()).map { it.hostname }
                }
                val deduped = SniProbe.dedupeHostnames(hosts)
                total = deduped.size
                if (deduped.isEmpty()) error = "No hosts to probe."
                for (h in deduped) {
                    if (!scanning) break
                    val r = withContext(Dispatchers.IO) { SniNetwork.probeOne(h) }
                    results.add(r)
                }
            } catch (e: Exception) {
                error = e.message ?: e.toString()
            } finally {
                scanning = false
            }
        }
    }

    val working = results.count { it.verdict == Verdict.WORKING }

    LazyColumn(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item {
            SectionCard("DISCOVER", accent = MaterialTheme.colorScheme.secondary) {
                SegmentedTabs(mode, listOf("Seedlist", "Domain"), Modifier.fillMaxWidth()) { if (!scanning) mode = it }
                Spacer(Modifier.height(12.dp))
                if (mode == 0) {
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Seedlist.BUNDLED.forEach { name ->
                            val on = name == seedlist
                            val c = if (on) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant
                            Surface(
                                color = c.copy(alpha = if (on) 0.16f else 0.06f),
                                shape = RoundedCornerShape(8.dp),
                                border = BorderStroke(1.dp, c.copy(alpha = 0.4f)),
                                modifier = Modifier.weight(1f).clickable { if (!scanning) seedlist = name },
                            ) {
                                Text(
                                    name.removeSuffix(".txt"),
                                    style = MaterialTheme.typography.labelMedium.copy(color = c),
                                    textAlign = TextAlign.Center,
                                    modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp),
                                )
                            }
                        }
                    }
                } else {
                    OutlinedTextField(
                        value = domain,
                        onValueChange = { domain = it },
                        singleLine = true,
                        label = { Text("Domain (e.g. cloudflare.com)") },
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
                Spacer(Modifier.height(14.dp))
                if (scanning) {
                    Button(onClick = { scanning = false }, modifier = Modifier.fillMaxWidth()) { Text("Stop") }
                } else {
                    Button(onClick = { start() }, enabled = mode == 0 || domain.isNotBlank(), modifier = Modifier.fillMaxWidth()) {
                        Text("Start scan")
                    }
                }
            }
        }

        if (scanning || results.isNotEmpty() || error != null) {
            item {
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
                    Text(
                        if (total > 0) "$working working · ${results.size}/$total probed" else "Probing…",
                        style = MaterialTheme.typography.labelLarge,
                    )
                    if (scanning) {
                        CircularProgressIndicator(Modifier.height(18.dp), strokeWidth = 2.dp)
                    } else if (working > 0) {
                        OutlinedButton(onClick = {
                            onExport(Export.toTxt(SniScanJob(jobId = "scan", results = results.toList())))
                        }) { Text("Export working") }
                    }
                }
            }
        }

        error?.let { item { Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall) } }

        items(results) { r -> ResultRow(r) }
    }
}

@Composable
private fun ResultRow(r: SniProbeResult) {
    Card(Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
        Row(Modifier.fillMaxWidth().padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(r.hostname, style = MaterialTheme.typography.bodyMedium, maxLines = 1, overflow = TextOverflow.Ellipsis)
                val meta = buildString {
                    r.targetIp?.let { append(it) }
                    r.httpStatus?.let { append("  ·  HTTP $it") }
                    r.serverHeader?.let { append("  ·  $it") }
                }
                if (meta.isNotBlank()) {
                    Text(meta, style = MaterialTheme.typography.labelMedium, fontFamily = FontFamily.Monospace,
                        color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1, overflow = TextOverflow.Ellipsis)
                }
            }
            Spacer(Modifier.width(10.dp))
            Pill(r.verdict.wire, verdictColor(r.verdict.wire))
        }
    }
}
