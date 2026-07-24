package arc.omega.bridgezero

import com.google.gson.annotations.SerializedName

data class Compatibility(
    @SerializedName("runtime_version") val runtimeVersion: String,
    @SerializedName("required_mobile_version") val requiredMobileVersion: String,
    @SerializedName("api_version") val apiVersion: String,
)

data class RuntimeStatus(
    val online: Boolean,
    @SerializedName("current_model") val currentModel: String?,
    @SerializedName("model_lock") val modelLock: Boolean,
    @SerializedName("uptime_seconds") val uptimeSeconds: Long,
    @SerializedName("latency_ms") val latencyMs: Double,
    val version: String,
    @SerializedName("chronicle_count") val chronicleCount: Int,
)

data class RuntimeTelemetry(
    @SerializedName("observed_at") val observedAt: String,
    @SerializedName("uptime_seconds") val uptimeSeconds: Long,
    @SerializedName("cpu_percent") val cpuPercent: Double?,
    @SerializedName("ram_used_bytes") val ramUsedBytes: Long?,
    @SerializedName("ram_total_bytes") val ramTotalBytes: Long?,
    @SerializedName("latency_ms") val latencyMs: Double?,
    @SerializedName("tool_queue") val toolQueue: Int,
    @SerializedName("streaming_state") val streamingState: String,
    @SerializedName("active_streams") val activeStreams: Int,
    @SerializedName("connected_clients") val connectedClients: Int,
    @SerializedName("current_session") val currentSession: String?,
    @SerializedName("chronicle_events") val chronicleEvents: Int,
) {
    fun applying(signal: RuntimeStreamingSignal) = copy(
        latencyMs = signal.latencyMs ?: latencyMs,
        streamingState = signal.state,
        activeStreams = signal.activeStreams,
        currentSession = signal.sessionId ?: currentSession,
    )
}

data class RuntimeStreamingSignal(
    val state: String,
    @SerializedName("session_id") val sessionId: String?,
    @SerializedName("active_streams") val activeStreams: Int,
    @SerializedName("latency_ms") val latencyMs: Double?,
)
data class RuntimeSessionSignal(@SerializedName("current_session") val currentSession: String?)
data class RuntimeChronicleSignal(val entries: List<ChronicleEntry>)

enum class DiagnosticLevel { healthy, degraded, unavailable, inactive }

data class DiagnosticState(val state: DiagnosticLevel, val detail: String?)

data class Diagnostics(
    val identity: DiagnosticState,
    val evidence: DiagnosticState,
    val planning: DiagnosticState,
    val deliberation: DiagnosticState,
    @SerializedName("tool_state") val toolState: DiagnosticState,
    val memory: DiagnosticState,
    val chronicle: DiagnosticState,
    @SerializedName("connection_health") val connectionHealth: DiagnosticState,
    val counts: Map<String, Int>?,
) {
    fun ordered() = listOf(
        "Identity" to identity, "Evidence" to evidence, "Planning" to planning,
        "Deliberation" to deliberation, "Tool State" to toolState,
        "Memory" to memory, "Chronicle" to chronicle,
        "Connection Health" to connectionHealth,
    )
}

data class Conversation(val id: String, val messages: List<RuntimeMessage>)

data class RuntimeMessage(
    val id: String,
    val role: Role,
    val content: String,
    @SerializedName("created_at") val createdAt: String,
) {
    enum class Role { operator, runtime, system }
}

data class ChronicleEntry(
    val id: String,
    val epoch: String,
    val title: String,
    @SerializedName("occurred_at") val occurredAt: String,
    val items: List<String>,
)

data class MessageRequest(
    val content: String,
    @SerializedName("client_message_id") val clientMessageId: String,
)

data class ConversationRequest(val title: String = "Bridge Zero Mobile")

sealed interface StreamEvent {
    data class Phase(val name: String) : StreamEvent
    data class Delta(val text: String) : StreamEvent
    data class Error(val message: String) : StreamEvent
    data object End : StreamEvent
    data object Metadata : StreamEvent
}

sealed interface ConnectionState {
    data object Disconnected : ConnectionState
    data object Connecting : ConnectionState
    data object Connected : ConnectionState
    data class Offline(val reason: String) : ConnectionState
    data class UpdateRequired(val compatibility: Compatibility) : ConnectionState
}

object MobileVersion {
    const val CURRENT = "0.2.0"
    const val API_MAJOR = "1"

    fun compatible(value: Compatibility): Boolean =
        value.apiVersion.substringBefore('.') == API_MAJOR && compare(CURRENT, value.requiredMobileVersion) >= 0

    fun compare(left: String, right: String): Int {
        val lhs = left.split('.').map { part -> part.takeWhile { it.isDigit() }.toIntOrNull() ?: 0 }
        val rhs = right.split('.').map { part -> part.takeWhile { it.isDigit() }.toIntOrNull() ?: 0 }
        repeat(maxOf(lhs.size, rhs.size)) { index ->
            val result = (lhs.getOrNull(index) ?: 0).compareTo(rhs.getOrNull(index) ?: 0)
            if (result != 0) return result
        }
        return 0
    }
}

data class OperatorUiState(
    val connection: ConnectionState = ConnectionState.Disconnected,
    val status: RuntimeStatus? = null,
    val telemetry: RuntimeTelemetry? = null,
    val diagnostics: Diagnostics? = null,
    val conversation: Conversation? = null,
    val chronicle: List<ChronicleEntry> = emptyList(),
    val streamingText: String = "",
    val runtimePhase: String? = null,
    val latencyMs: Long? = null,
    val logs: List<String> = emptyList(),
    val server: String = "",
    val hasToken: Boolean = false,
)
