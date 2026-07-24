package arc.omega.bridgezero

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Book
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Send
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Divider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp

private val Void = BridgeDesign.Colors.Void
private val Panel = BridgeDesign.Colors.Panel
private val Raised = BridgeDesign.Colors.Raised
private val Signal = BridgeDesign.Colors.Signal
private val Nominal = BridgeDesign.Colors.Nominal
private val Warning = BridgeDesign.Colors.Warning
private val Failure = BridgeDesign.Colors.Failure

class MainActivity : ComponentActivity() {
    private val runtimeStore by viewModels<RuntimeStore>()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent { BridgeZeroTheme { BridgeZeroApp(runtimeStore) } }
    }

    override fun onStart() {
        super.onStart()
        runtimeStore.resumeEvents()
    }

    override fun onStop() {
        runtimeStore.suspendEvents()
        super.onStop()
    }
}

@Composable
fun BridgeZeroApp(viewModel: RuntimeStore) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    LaunchedEffect(Unit) { viewModel.restore() }
    when (val connection = state.connection) {
        ConnectionState.Disconnected, ConnectionState.Connecting -> LoginScreen(state, viewModel)
        is ConnectionState.UpdateRequired -> UpdateRequiredScreen(connection.compatibility, viewModel)
        ConnectionState.Connected, is ConnectionState.Offline -> ConsoleScreen(state, viewModel)
    }
}

@Composable
private fun BridgeZeroTheme(content: @Composable () -> Unit) {
    val colors = androidx.compose.material3.darkColorScheme(
        primary = Signal, secondary = Nominal, background = Void,
        surface = Panel, surfaceVariant = Raised, error = Failure,
    )
    MaterialTheme(colorScheme = colors, typography = androidx.compose.material3.Typography(), content = content)
}

@Composable
private fun LoginScreen(state: OperatorUiState, viewModel: OperatorViewModel) {
    var server by remember(state.server) { mutableStateOf(state.server) }
    var token by remember { mutableStateOf("") }
    Column(
        Modifier.fillMaxSize().background(Void).verticalScroll(rememberScrollState()).padding(BridgeDesign.Spacing.Xl),
        verticalArrangement = Arrangement.spacedBy(BridgeDesign.Spacing.Xl),
    ) {
        Spacer(Modifier.height(32.dp))
        Text("BRIDGE ZERO", style = MaterialTheme.typography.headlineLarge, fontWeight = FontWeight.Bold)
        Text("MOBILE OPERATOR CONSOLE", color = Signal, fontFamily = FontFamily.Monospace)
        InstrumentPanel("CORE RUNTIME LINK") {
            OutlinedTextField(
                value = server, onValueChange = { server = it }, modifier = Modifier.fillMaxWidth(),
                label = { Text("Server Address") }, singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri, imeAction = ImeAction.Next),
            )
            OutlinedTextField(
                value = token, onValueChange = { token = it }, modifier = Modifier.fillMaxWidth(),
                label = { Text("Authentication Token") }, singleLine = true,
                visualTransformation = androidx.compose.ui.text.input.PasswordVisualTransformation(),
                keyboardActions = KeyboardActions(onDone = { if (server.isNotBlank() && token.isNotBlank()) viewModel.connect(server, token) }),
            )
            Button(
                onClick = { viewModel.connect(server, token) },
                enabled = server.isNotBlank() && token.isNotBlank() && state.connection != ConnectionState.Connecting,
                modifier = Modifier.fillMaxWidth(),
            ) {
                if (state.connection == ConnectionState.Connecting) CircularProgressIndicator(Modifier.size(18.dp))
                Text("  CONNECT", fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold)
            }
        }
        if (state.connection is ConnectionState.Offline) Text(state.connection.reason, color = Failure)
        Text("Credentials remain encrypted on this device. Platform TLS validation is enforced.", color = Color.Gray)
    }
}

private enum class Tab { Runtime, Console, Diagnostics, Settings }

@Composable
private fun ConsoleScreen(state: OperatorUiState, viewModel: OperatorViewModel) {
    var tab by remember { mutableStateOf(Tab.Runtime) }
    Scaffold(
        containerColor = Void,
        bottomBar = {
            NavigationBar {
                listOf(
                    Triple(Tab.Runtime, "Runtime", Icons.Default.Home),
                    Triple(Tab.Console, "Console", Icons.Default.Send),
                    Triple(Tab.Diagnostics, "Diagnostics", Icons.Default.Info),
                    Triple(Tab.Settings, "Settings", Icons.Default.Settings),
                ).forEach { (value, label, icon) ->
                    NavigationBarItem(
                        selected = tab == value, onClick = { tab = value },
                        icon = { Icon(icon, null) }, label = { Text(label) },
                    )
                }
            }
        },
    ) { padding ->
        Box(Modifier.fillMaxSize().padding(padding)) {
            when (tab) {
                Tab.Runtime -> DashboardScreen(state, viewModel)
                Tab.Console -> ConversationScreen(state, viewModel)
                Tab.Diagnostics -> DiagnosticsScreen(state)
                Tab.Settings -> SettingsScreen(state, viewModel)
            }
        }
    }
}

@Composable
private fun DashboardScreen(state: OperatorUiState, viewModel: OperatorViewModel) {
    LazyColumn(
        Modifier.fillMaxSize().background(Void).padding(BridgeDesign.Spacing.Lg),
        verticalArrangement = Arrangement.spacedBy(BridgeDesign.Spacing.Md),
    ) {
        item {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Column { Text("OMEGA-ARC", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold); Text("CORE RUNTIME", color = Signal, fontFamily = FontFamily.Monospace) }
                Spacer(Modifier.weight(1f))
                StatusLamp(if (state.connection == ConnectionState.Connected) Nominal else Failure, if (state.connection == ConnectionState.Connected) "LINKED" else "OFFLINE")
            }
        }
        state.status?.let { status ->
        state.telemetry?.let { telemetry ->
            item {
                InstrumentPanel("OPERATIONS DASHBOARD") {
                    Metric("Streaming", telemetry.streamingState.uppercase(), if (telemetry.streamingState == "streaming") Signal else Color.Gray)
                    Metric("CPU", telemetry.cpuPercent?.let { "%.1f%%".format(it) } ?: "UNAVAILABLE")
                    Metric("RAM", formatMemory(telemetry.ramUsedBytes, telemetry.ramTotalBytes))
                    Metric("Tool Queue", telemetry.toolQueue.toString())
                    Metric("Connected Clients", telemetry.connectedClients.toString())
                    Metric("Active Streams", telemetry.activeStreams.toString())
                    Metric("Current Session", telemetry.currentSession ?: "UNAVAILABLE")
                    Metric("Chronicle Events", telemetry.chronicleEvents.toString())
                }
            }
        }

            item {
                InstrumentPanel("RUNTIME STATUS") {
                    Metric("Status", if (status.online) "ONLINE" else "OFFLINE", if (status.online) Nominal else Failure)
                    Divider()
                    Metric("Current Model", status.currentModel ?: "UNAVAILABLE")
                    Metric("Model Lock", if (status.modelLock) "ENGAGED" else "DISENGAGED", if (status.modelLock) Warning else Color.Gray)
                    Metric("Uptime", formatUptime(status.uptimeSeconds))
                    Metric("Latency", state.latencyMs?.let { "$it ms" } ?: "UNAVAILABLE")
                    Metric("Runtime Version", status.version)
                    Metric("Chronicle Count", status.chronicleCount.toString())
                }
            }
        }
        item {
            InstrumentPanel("CONTINUITY") {
                Metric("Active Session", state.conversation?.id ?: "UNAVAILABLE")
                Metric("Messages", (state.conversation?.messages?.size ?: 0).toString())
                Metric("Mobile Version", MobileVersion.CURRENT)
                OutlinedButton(onClick = viewModel::refresh, modifier = Modifier.fillMaxWidth()) { Text("REFRESH") }
            }
        }
    }
}

@Composable
private fun ConversationScreen(state: OperatorUiState, viewModel: OperatorViewModel) {
    var composer by remember { mutableStateOf("") }
    Column(Modifier.fillMaxSize().background(Void)) {
        LazyColumn(
            modifier = Modifier.weight(1f).padding(BridgeDesign.Spacing.Md),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            items(state.conversation?.messages ?: emptyList(), key = { it.id }) { MessagePlate(it.role, it.content) }
            if (state.streamingText.isNotEmpty() || state.runtimePhase != null) {
                item { MessagePlate(RuntimeMessage.Role.runtime, state.streamingText, state.runtimePhase) }
            }
        }
        Divider()
        Row(Modifier.padding(10.dp), verticalAlignment = Alignment.CenterVertically) {
            OutlinedTextField(
                value = composer, onValueChange = { composer = it }, modifier = Modifier.weight(1f),
                label = { Text("Operator command") }, maxLines = 5,
            )
            IconButton(
                onClick = { viewModel.sendMessage(composer); composer = "" },
                enabled = composer.isNotBlank() && state.connection == ConnectionState.Connected,
            ) { Icon(Icons.Default.Send, "Transmit", tint = Signal) }
        }
    }
}

@Composable
private fun MessagePlate(role: RuntimeMessage.Role, content: String, phase: String? = null) {
    val color = when (role) { RuntimeMessage.Role.operator -> Signal; RuntimeMessage.Role.runtime -> Nominal; RuntimeMessage.Role.system -> Warning }
    Column(
        Modifier.fillMaxWidth().background(Panel, RoundedCornerShape(10.dp)).border(1.dp, color.copy(alpha = .25f), RoundedCornerShape(10.dp)).padding(14.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Row(Modifier.fillMaxWidth()) {
            Text(if (role == RuntimeMessage.Role.runtime) "CORE RUNTIME" else role.name.uppercase(), color = color, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold)
            Spacer(Modifier.weight(1f)); phase?.let { Text(it.uppercase(), color = Warning, fontFamily = FontFamily.Monospace) }
        }
        if (content.isBlank()) Text("Runtime phase reported; awaiting response data.", color = Color.Gray)
        else MarkdownText(content)
    }
}

@Composable
private fun MarkdownText(content: String) {
    val blocks = content.split("```")
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        blocks.forEachIndexed { index, block ->
            if (index % 2 == 1) {
                Text(block.trim(), fontFamily = FontFamily.Monospace, modifier = Modifier.fillMaxWidth().background(Color.Black.copy(alpha = .35f), RoundedCornerShape(6.dp)).padding(10.dp))
            } else {
                Text(inlineMarkdown(block))
            }
        }
    }
}

private fun inlineMarkdown(value: String) = buildAnnotatedString {
    var index = 0
    while (index < value.length) {
        val bold = value.indexOf("**", index)
        val code = value.indexOf('`', index)
        val next = listOf(bold, code).filter { it >= 0 }.minOrNull()
        if (next == null) { append(value.substring(index)); break }
        append(value.substring(index, next))
        if (next == bold) {
            val end = value.indexOf("**", next + 2)
            if (end < 0) { append(value.substring(next)); break }
            withStyle(SpanStyle(fontWeight = FontWeight.Bold)) { append(value.substring(next + 2, end)) }
            index = end + 2
        } else {
            val end = value.indexOf('`', next + 1)
            if (end < 0) { append(value.substring(next)); break }
            withStyle(SpanStyle(fontFamily = FontFamily.Monospace, background = Raised)) { append(value.substring(next + 1, end)) }
            index = end + 1
        }
    }
}

@Composable
private fun DiagnosticsScreen(state: OperatorUiState) {
    LazyColumn(Modifier.fillMaxSize().background(Void).padding(BridgeDesign.Spacing.Lg), verticalArrangement = Arrangement.spacedBy(9.dp)) {
        val records = state.diagnostics?.ordered() ?: emptyList()
        items(records) { (name, diagnostic) ->
            val color = when (diagnostic.state) { DiagnosticLevel.healthy -> Nominal; DiagnosticLevel.degraded -> Warning; DiagnosticLevel.unavailable -> Failure; DiagnosticLevel.inactive -> Color.Gray }
            Row(Modifier.fillMaxWidth().background(Panel, RoundedCornerShape(10.dp)).padding(14.dp), verticalAlignment = Alignment.Top) {
                Box(Modifier.padding(top = 5.dp).size(9.dp).background(color, RoundedCornerShape(50)))
                Column(Modifier.padding(start = 12.dp).weight(1f)) { Text(name, fontWeight = FontWeight.SemiBold); diagnostic.detail?.let { Text(it, color = Color.Gray) } }
                Text(diagnostic.state.name.uppercase(), color = color, fontFamily = FontFamily.Monospace)
            }
        }
        if (records.isEmpty()) item { Text("No runtime diagnostic response has been received.", color = Color.Gray) }
    }
}

@Composable
private fun SettingsScreen(state: OperatorUiState, viewModel: OperatorViewModel) {
    var showChronicle by remember { mutableStateOf(false) }
    var showLogs by remember { mutableStateOf(false) }
    LazyColumn(Modifier.fillMaxSize().background(Void).padding(BridgeDesign.Spacing.Lg), verticalArrangement = Arrangement.spacedBy(BridgeDesign.Spacing.Md)) {
        item { InstrumentPanel("CONNECTION") { Metric("Server", state.server); Metric("Authentication", if (state.hasToken) "ENCRYPTED" else "NOT STORED") } }
        item { InstrumentPanel("MODEL INFORMATION") { Metric("Model", state.status?.currentModel ?: "UNAVAILABLE"); Metric("Model Lock", if (state.status?.modelLock == true) "ENGAGED" else "UNAVAILABLE"); Metric("Runtime", state.status?.version ?: "UNAVAILABLE"); Metric("Mobile", MobileVersion.CURRENT) } }
        item {
            InstrumentPanel("ARCHIVE") {
                OutlinedButton(onClick = { showChronicle = !showChronicle }, modifier = Modifier.fillMaxWidth()) { Icon(Icons.Default.Book, null); Text("  CHRONICLE") }
                if (showChronicle) state.chronicle.forEach { entry -> Column(Modifier.padding(vertical = 6.dp)) { Text(entry.epoch, color = Signal, fontFamily = FontFamily.Monospace); Text(entry.title, fontWeight = FontWeight.Bold); entry.items.forEach { Text("— $it") } } }
                OutlinedButton(onClick = { showLogs = !showLogs }, modifier = Modifier.fillMaxWidth()) { Text("CONNECTION LOGS") }
                if (showLogs) state.logs.forEach { Text(it, fontFamily = FontFamily.Monospace, style = MaterialTheme.typography.bodySmall) }
            }
        }
        item { InstrumentPanel("NOTIFICATIONS") { Text("Runtime push notifications become available in Epoch IX-C.", color = Color.Gray) } }
        item { Button(onClick = { viewModel.disconnect() }, modifier = Modifier.fillMaxWidth()) { Text("DISCONNECT") } }
    }
}

@Composable
private fun UpdateRequiredScreen(compatibility: Compatibility, viewModel: OperatorViewModel) {
    Column(Modifier.fillMaxSize().background(Void).padding(BridgeDesign.Spacing.Xl), verticalArrangement = Arrangement.Center, horizontalAlignment = Alignment.CenterHorizontally) {
        Text("UPDATE REQUIRED", style = MaterialTheme.typography.headlineMedium, color = Warning, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(20.dp))
        InstrumentPanel("COMPATIBILITY") { Metric("Installed Mobile", MobileVersion.CURRENT); Metric("Required Mobile", compatibility.requiredMobileVersion); Metric("Runtime", compatibility.runtimeVersion); Metric("API", compatibility.apiVersion) }
        Spacer(Modifier.height(20.dp)); OutlinedButton(onClick = { viewModel.disconnect(false) }) { Text("DISCONNECT") }
    }
}

@Composable
private fun InstrumentPanel(title: String, content: @Composable ColumnScope.() -> Unit) {
    Column(
        Modifier.fillMaxWidth().background(Panel, RoundedCornerShape(BridgeDesign.Radius.Card)).border(1.dp, BridgeDesign.Colors.Separator, RoundedCornerShape(BridgeDesign.Radius.Card)).padding(BridgeDesign.Spacing.Lg),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) { Text(title, color = Signal, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold); content() }
}

@Composable
private fun Metric(label: String, value: String, color: Color = Color.White) {
    Row(Modifier.fillMaxWidth()) { Text(label, color = Color.Gray); Spacer(Modifier.weight(1f)); Text(value, color = color, fontFamily = FontFamily.Monospace) }
}

@Composable
private fun StatusLamp(color: Color, label: String) {
    Row(verticalAlignment = Alignment.CenterVertically) { Box(Modifier.size(8.dp).background(color, RoundedCornerShape(50))); Text("  $label", fontFamily = FontFamily.Monospace) }
}

private fun formatUptime(seconds: Long): String {
    val days = seconds / 86_400; val hours = seconds % 86_400 / 3_600; val minutes = seconds % 3_600 / 60
    return if (days > 0) "${days}d ${hours}h" else if (hours > 0) "${hours}h ${minutes}m" else "${minutes}m"
}

private fun formatMemory(used: Long?, total: Long?): String {
    if (used == null || total == null || total <= 0) return "UNAVAILABLE"
    val gib = 1024.0 * 1024.0 * 1024.0
    return "%.1f / %.1f GiB".format(used / gib, total / gib)
}
