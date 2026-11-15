package com.injectx.app

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
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
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.injectx.app.ui.Pill
import com.injectx.app.ui.theme.Accent
import com.injectx.app.ui.theme.BadRed
import com.injectx.app.ui.theme.Outline
import com.injectx.app.ui.theme.Surface1
import com.injectx.app.ui.theme.Surface2
import com.injectx.app.ui.theme.TextLo
import com.injectx.app.ui.theme.TextMid
import com.injectx.app.ui.theme.WarnAmber
import com.injectx.core.sni.DomainInput
import com.injectx.core.sni.Export
import com.injectx.core.sni.HostResult
import com.injectx.core.sni.HuntPhase
import com.injectx.core.sni.HuntSession
import com.injectx.core.sni.SniNetwork
import com.injectx.core.sni.TestState
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@Composable
fun SniScreen(onExport: (String) -> Unit, onScanComplete: (Int, String?) -> Unit = { _, _ -> }) {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    val net = rememberNetworkInfo()

    var session by remember { mutableStateOf(HuntStore.load(ctx) ?: HuntSession()) }
    fun persist(s: HuntSession) { session = s; HuntStore.save(ctx, s) }

    when (session.phase) {
        HuntPhase.INPUT -> InputPhase(
            net = net,
            onDiscover = { seeds, onProgress, done ->
                scope.launch {
                    val found = LinkedHashSet<String>()
                    for (d in seeds) {
                        val hosts = withContext(Dispatchers.IO) {
                            runCatching { SniNetwork.discover(d).map { it.hostname } }.getOrDefault(emptyList())
                        }
                        found.addAll(hosts); onProgress(d, found.size)
                    }
                    done(found.toList())
                }
            },
            onContinue = { candidates -> persist(session.copy(phase = HuntPhase.DISCOVERED, candidates = candidates)) },
        )

        HuntPhase.DISCOVERED -> HandoffPhase(
            session = session, net = net,
            onBack = { persist(session.copy(phase = HuntPhase.INPUT)) },
            onStart = { label -> persist(session.copy(phase = HuntPhase.TESTING, testLabel = label.ifBlank { null })) },
        )

        HuntPhase.TESTING, HuntPhase.DONE -> TestPhase(
            session = session, net = net,
            onProbe = { onEach ->
                scope.launch {
                    for (h in session.pending()) {
                        if (!onEach()) break
                        val r = withContext(Dispatchers.IO) { SniNetwork.probeOne(h) }
                        persist(session.copy(results = session.results + HostResult.from(r)))
                    }
                    if (session.pending().isEmpty()) {
                        val done = session.copy(phase = HuntPhase.DONE)
                        persist(done)
                        onScanComplete(done.working().size, done.testLabel)
                    }
                }
            },
            onExport = { onExport(Export.working(session)) },
            onReset = { HuntStore.clear(ctx); session = HuntSession() },
            onEditHosts = { persist(session.copy(phase = HuntPhase.INPUT)) },
        )
    }
}

/* ------------------------------- Step 1: input + discover ------------------------------- */

@Composable
private fun InputPhase(
    net: NetInfo,
    onDiscover: (seeds: List<String>, onProgress: (String, Int) -> Unit, done: (List<String>) -> Unit) -> Unit,
    onContinue: (List<String>) -> Unit,
) {
    var typed by remember { mutableStateOf("") }
    var imported by remember { mutableStateOf<DomainInput.Result?>(null) }
    var importedName by remember { mutableStateOf<String?>(null) }
    val discovered = remember { mutableStateOf<List<String>>(emptyList()) }
    var discovering by remember { mutableStateOf(false) }
    var discoverNote by remember { mutableStateOf<String?>(null) }
    var showSkipped by remember { mutableStateOf(false) }

    val ctx = LocalContext.current
    val picker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri: Uri? ->
        if (uri == null) return@rememberLauncherForActivityResult
        val text = runCatching { ctx.contentResolver.openInputStream(uri)?.use { it.readBytes().decodeToString() } }.getOrNull()
        if (text != null) {
            imported = DomainInput.parse(text)
            importedName = uri.lastPathSegment?.substringAfterLast('/')?.substringAfterLast(':') ?: "imported.txt"
        }
    }

    val typedParse = remember(typed) { DomainInput.parse(typed) }
    val combined = remember(typed, imported, discovered.value) {
        LinkedHashSet<String>().apply {
            addAll(typedParse.valid)
            imported?.let { addAll(it.valid) }
            addAll(discovered.value)
        }.toList()
    }
    val skippedAll = typedParse.skipped + (imported?.skipped ?: emptyList())

    LazyColumn(Modifier.fillMaxSize().padding(horizontal = 20.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        item {
            Spacer(Modifier.height(16.dp))
            StepHeader(1, "Discover", "Enter or import the hosts to test. Do this on your normal network.")
        }

        item {
            OutlinedTextField(
                value = typed,
                onValueChange = { typed = it },
                label = { Text("Domains or hosts") },
                placeholder = { Text("one per line, or separated by ; , or spaces\ne.g. cloudflare.com; m.youtube.com") },
                modifier = Modifier.fillMaxWidth().height(150.dp),
            )
        }

        item {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                OutlinedButton(onClick = { picker.launch(arrayOf("text/plain", "text/*", "*/*")) }) { Text("Import .txt") }
                importedName?.let { name ->
                    Text(
                        "$name — ${imported?.valid?.size ?: 0} valid",
                        style = MaterialTheme.typography.labelMedium, color = TextMid,
                        maxLines = 1, overflow = TextOverflow.Ellipsis,
                    )
                }
            }
        }

        // Live count (§11.5) + skipped viewer (§11.6 reason).
        item {
            val typedSkip = skippedAll.size
            Column {
                Text(
                    "${combined.size} valid" + if (typedSkip > 0) " · $typedSkip skipped" else "",
                    style = MaterialTheme.typography.labelLarge,
                    color = if (combined.isEmpty()) TextLo else Accent,
                )
                if (combined.isEmpty()) {
                    Text("Enter at least one valid host to continue.", style = MaterialTheme.typography.bodySmall, color = TextLo)
                }
                if (typedSkip > 0) {
                    TextButton(onClick = { showSkipped = !showSkipped }, contentPadding = androidx.compose.foundation.layout.PaddingValues(0.dp)) {
                        Text(if (showSkipped) "Hide skipped" else "View skipped", style = MaterialTheme.typography.labelMedium)
                    }
                    if (showSkipped) {
                        Surface(color = Surface2, shape = RoundedCornerShape(8.dp), modifier = Modifier.fillMaxWidth()) {
                            Column(Modifier.padding(10.dp)) {
                                skippedAll.take(20).forEach {
                                    Text("${it.raw}  —  ${it.reason}", style = MaterialTheme.typography.labelMedium,
                                        fontFamily = FontFamily.Monospace, color = TextMid, maxLines = 1, overflow = TextOverflow.Ellipsis)
                                }
                                if (skippedAll.size > 20) Text("+${skippedAll.size - 20} more", style = MaterialTheme.typography.labelMedium, color = TextLo)
                            }
                        }
                    }
                }
            }
        }

        // Optional: expand the candidate set with crt.sh subdomains (needs a real network).
        item {
            Column {
                OutlinedButton(
                    onClick = {
                        discovering = true; discoverNote = "Searching crt.sh…"
                        onDiscover(combined, { d, n -> discoverNote = "crt.sh: $n found ($d)" }) { found ->
                            discovered.value = found; discovering = false
                            discoverNote = "Added ${found.size} from crt.sh"
                        }
                    },
                    enabled = combined.isNotEmpty() && net.connected && !discovering,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    if (discovering) { CircularProgressIndicator(Modifier.size(16.dp), strokeWidth = 2.dp); Spacer(Modifier.width(10.dp)) }
                    Text("Find more via crt.sh (optional)")
                }
                val note = discoverNote ?: if (!net.connected) "Offline — connect to search crt.sh." else null
                note?.let { Text(it, style = MaterialTheme.typography.bodySmall, color = TextLo, modifier = Modifier.padding(top = 4.dp)) }
            }
        }

        item {
            Button(
                onClick = { onContinue(combined) },
                enabled = combined.isNotEmpty(),
                modifier = Modifier.fillMaxWidth(),
            ) { Text(if (combined.isEmpty()) "Save candidates" else "Save ${combined.size} candidates → Test") }
            Spacer(Modifier.height(20.dp))
        }
    }
}

/* ------------------------------- Step handoff ------------------------------- */

@Composable
private fun HandoffPhase(session: HuntSession, net: NetInfo, onBack: () -> Unit, onStart: (String) -> Unit) {
    var label by remember { mutableStateOf(session.testLabel ?: "") }

    Column(Modifier.fillMaxSize().padding(horizontal = 20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        Spacer(Modifier.height(16.dp))
        StepHeader(2, "Test", "Candidates saved. Switch to your dataless network, then run the test.")

        Surface(color = Surface1, shape = RoundedCornerShape(16.dp), border = BorderStroke(1.dp, Outline), modifier = Modifier.fillMaxWidth()) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text("${session.candidates.size} candidates", style = MaterialTheme.typography.titleMedium, color = Accent)
                Text("A host that works on one network isn't assumed to work on another — name the network so the results are tagged with it.",
                    style = MaterialTheme.typography.bodySmall, color = TextMid)
            }
        }

        NetworkChip(net)

        OutlinedTextField(
            value = label,
            onValueChange = { label = it },
            singleLine = true,
            label = { Text("Network label") },
            placeholder = { Text("e.g. Dataless Airtel") },
            modifier = Modifier.fillMaxWidth(),
        )

        Button(onClick = { onStart(label) }, modifier = Modifier.fillMaxWidth()) {
            Text(if (session.results.isEmpty()) "Start test on this network" else "Continue test")
        }
        TextButton(onClick = onBack, modifier = Modifier.fillMaxWidth()) { Text("Edit hosts") }
    }
}

/* ------------------------------- Step 2: testing ------------------------------- */

@Composable
private fun TestPhase(
    session: HuntSession,
    net: NetInfo,
    onProbe: (onEach: () -> Boolean) -> Unit,
    onExport: () -> Unit,
    onReset: () -> Unit,
    onEditHosts: () -> Unit,
) {
    var scanning by remember { mutableStateOf(false) }
    val counts = session.counts()
    val works = counts[TestState.WORKS] ?: 0
    val tested = session.results.size
    val total = session.candidates.size
    val pending = total - tested

    LazyColumn(Modifier.fillMaxSize().padding(horizontal = 20.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        item {
            Spacer(Modifier.height(16.dp))
            StepHeader(2, "Test", session.testLabel?.let { "Testing on “$it”." } ?: "Testing candidates.")
        }
        item { NetworkChip(net) }

        item {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
                Text("$works working · $tested/$total tested", style = MaterialTheme.typography.labelLarge)
                if (scanning) CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp)
            }
        }

        item {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                if (scanning) {
                    Button(onClick = { scanning = false }, modifier = Modifier.weight(1f)) { Text("Pause") }
                } else if (pending > 0) {
                    Button(
                        onClick = { scanning = true; onProbe { scanning } },
                        enabled = net.connected,
                        modifier = Modifier.weight(1f),
                    ) { Text(if (tested == 0) "Start test" else "Resume ($pending left)") }
                }
                if (works > 0 && !scanning) {
                    OutlinedButton(onClick = onExport, modifier = Modifier.weight(1f)) { Text("Export working") }
                }
            }
        }

        if (!net.connected && pending > 0 && !scanning) {
            item { Text("Offline — connect to your test network to run the probes.", style = MaterialTheme.typography.bodySmall, color = WarnAmber) }
        }

        if (session.phase == HuntPhase.DONE && !scanning) {
            item {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    TextButton(onClick = onEditHosts, modifier = Modifier.weight(1f)) { Text("Edit hosts") }
                    TextButton(onClick = onReset, modifier = Modifier.weight(1f)) { Text("New hunt") }
                }
            }
        }

        items(session.results) { r -> ResultRow(r) }
    }
}

/* ------------------------------- shared bits ------------------------------- */

@Composable
private fun StepHeader(n: Int, title: String, subtitle: String) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Surface(color = Accent, shape = CircleShape) {
                Text("$n", style = MaterialTheme.typography.labelMedium, color = Color.Black,
                    modifier = Modifier.padding(horizontal = 9.dp, vertical = 3.dp))
            }
            Text(title, style = MaterialTheme.typography.titleMedium)
        }
        Text(subtitle, style = MaterialTheme.typography.bodySmall, color = TextMid)
    }
}

@Composable
private fun NetworkChip(net: NetInfo) {
    val c = if (net.connected) Accent else BadRed
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Box(Modifier.size(8.dp).clip(CircleShape).background(c))
        Text("Network: ${net.label}", style = MaterialTheme.typography.labelMedium, color = TextMid)
    }
}

@Composable
private fun ResultRow(r: HostResult) {
    val color = when (r.state) {
        TestState.WORKS -> Accent
        TestState.FAILS -> BadRed
        TestState.TIMED_OUT -> WarnAmber
        TestState.UNTESTED -> TextLo
    }
    val label = when (r.state) {
        TestState.WORKS -> "works"; TestState.FAILS -> "fails"
        TestState.TIMED_OUT -> "timed out"; TestState.UNTESTED -> "—"
    }
    Surface(color = Surface1, shape = RoundedCornerShape(12.dp), border = BorderStroke(1.dp, Outline), modifier = Modifier.fillMaxWidth()) {
        Row(Modifier.fillMaxWidth().padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(r.hostname, style = MaterialTheme.typography.bodyMedium, maxLines = 1, overflow = TextOverflow.Ellipsis)
                val meta = buildString {
                    r.targetIp?.let { append(it) }
                    r.httpStatus?.let { if (isNotEmpty()) append("  ·  "); append("HTTP $it") }
                }
                if (meta.isNotBlank()) {
                    Text(meta, style = MaterialTheme.typography.labelMedium, fontFamily = FontFamily.Monospace,
                        color = TextLo, maxLines = 1, overflow = TextOverflow.Ellipsis)
                }
            }
            Spacer(Modifier.width(10.dp))
            Pill(label, color)
        }
    }
}
