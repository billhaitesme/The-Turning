package arc.omega.bridgezero

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.runInterruptible
import retrofit2.HttpException
import java.time.Instant

class OperatorViewModel(application: Application) : AndroidViewModel(application) {
    val eventBus = RuntimeEventBus()
    private val secureStore = SecureStore(application)
    private val mutableState = MutableStateFlow(
        OperatorUiState(server = secureStore.server(), hasToken = secureStore.token() != null)
    )
    val state: StateFlow<OperatorUiState> = mutableState.asStateFlow()

    private var api: RuntimeApi? = null
    private var eventStream: Job? = null
    private var streaming: Job? = null

    init {
        viewModelScope.launch { eventBus.events.collect(::applyRuntimeEvent) }
    }

    fun restore() {
        val server = secureStore.server()
        val token = secureStore.token()
        if (server.isNotBlank() && !token.isNullOrBlank()) connect(server, token, persist = false)
    }

    fun connect(server: String, token: String, persist: Boolean = true) {
        eventStream?.cancel()
        mutableState.update { it.copy(connection = ConnectionState.Connecting) }
        log("Connection attempt started")
        viewModelScope.launch {
            try {
                val client = RuntimeApi.create(server, token)
                val compatibility = client.compatibility()
                if (!MobileVersion.compatible(compatibility)) {
                    mutableState.update { it.copy(connection = ConnectionState.UpdateRequired(compatibility)) }
                    log("Compatibility gate blocked runtime access")
                    return@launch
                }
                val started = System.nanoTime()
                val status = client.status()
                val telemetry = client.telemetry()
                val diagnostics = client.diagnostics()
                val chronicle = client.chronicle()
                val conversation = try {
                    client.activeConversation()
                } catch (error: HttpException) {
                    if (error.code() == 404) client.createConversation() else throw error
                }
                if (persist) secureStore.save(RuntimeApi.validateServer(server).trimEnd('/'), token)
                api = client
                mutableState.update {
                    it.copy(
                        connection = ConnectionState.Connected,
                        conversation = conversation,
                        latencyMs = (System.nanoTime() - started) / 1_000_000,
                        server = RuntimeApi.validateServer(server).trimEnd('/'),
                        hasToken = true,
                    )
                }
                eventBus.publish(RuntimeStoreEvent.Status(status))
                eventBus.publish(RuntimeStoreEvent.Telemetry(telemetry))
                eventBus.publish(RuntimeStoreEvent.DiagnosticsChanged(diagnostics))
                eventBus.publish(RuntimeStoreEvent.Chronicle(chronicle))
                log("Core Runtime connected")
                resumeEvents()
            } catch (error: Exception) {
                mutableState.update { it.copy(connection = ConnectionState.Offline(safeMessage(error))) }
                log("Connection failed: ${safeMessage(error)}")
            }
        }
    }

    fun refresh() {
        val client = api ?: return
        viewModelScope.launch {
            try {
                val started = System.nanoTime()
                val status = client.status()
                val telemetry = client.telemetry()
                val diagnostics = client.diagnostics()
                mutableState.update {
                    it.copy(
                        connection = ConnectionState.Connected,
                        latencyMs = (System.nanoTime() - started) / 1_000_000,
                    )
                }
                eventBus.publish(RuntimeStoreEvent.Status(status))
                eventBus.publish(RuntimeStoreEvent.Telemetry(telemetry))
                eventBus.publish(RuntimeStoreEvent.DiagnosticsChanged(diagnostics))
            } catch (error: Exception) {
                mutableState.update { it.copy(connection = ConnectionState.Offline(safeMessage(error))) }
                log("Manual runtime refresh unavailable: ${safeMessage(error)}")
            }
        }
    }

    fun sendMessage(content: String) {
        val client = api ?: return
        val conversation = mutableState.value.conversation ?: return
        if (streaming != null || content.isBlank()) return
        val local = RuntimeMessage(
            id = java.util.UUID.randomUUID().toString(),
            role = RuntimeMessage.Role.operator,
            content = content.trim(),
            createdAt = Instant.now().toString(),
        )
        mutableState.update {
            it.copy(
                conversation = conversation.copy(messages = conversation.messages + local),
                streamingText = "",
                runtimePhase = null,
            )
        }
        streaming = viewModelScope.launch {
            try {
                runInterruptible(Dispatchers.IO) {
                    client.streamMessage(conversation.id, content.trim()) { event ->
                        eventBus.publish(RuntimeStoreEvent.Stream(event))
                        when (event) {
                            is StreamEvent.Phase -> mutableState.update { it.copy(runtimePhase = event.name) }
                            is StreamEvent.Delta -> mutableState.update {
                                it.copy(streamingText = it.streamingText + event.text)
                            }
                            is StreamEvent.Error -> throw RuntimeException(event.message)
                            StreamEvent.End, StreamEvent.Metadata -> Unit
                        }
                    }
                }
                val refreshed = client.conversation(conversation.id)
                mutableState.update {
                    it.copy(
                        conversation = refreshed,
                        streamingText = "",
                        runtimePhase = null,
                    )
                }
            } catch (error: Exception) {
                log("Runtime stream failed: ${safeMessage(error)}")
                mutableState.update { it.copy(connection = ConnectionState.Offline(safeMessage(error))) }
            } finally {
                streaming = null
            }
        }
    }

    fun disconnect(clearCredentials: Boolean = true) {
        eventStream?.cancel()
        streaming?.cancel()
        eventStream = null
        streaming = null
        api = null
        if (clearCredentials) secureStore.clear()
        mutableState.value = OperatorUiState()
    }

    fun resumeEvents() {
        val client = api ?: return
        if (eventStream != null) return
        eventStream = viewModelScope.launch {
            while (true) {
                try {
                    runInterruptible(Dispatchers.IO) { client.streamRuntimeEvents(eventBus::publish) }
                } catch (error: CancellationException) {
                    return@launch
                } catch (error: Exception) {
                    mutableState.update { it.copy(connection = ConnectionState.Offline(safeMessage(error))) }
                    log("Runtime event stream unavailable: ${safeMessage(error)}; retrying")
                    delay(3_000)
                }
            }
        }
    }

    fun suspendEvents() {
        eventStream?.cancel()
        eventStream = null
    }

    private fun applyRuntimeEvent(event: RuntimeStoreEvent) {
        when (event) {
            is RuntimeStoreEvent.Status -> mutableState.update { it.copy(status = event.value) }
            is RuntimeStoreEvent.DiagnosticsChanged -> mutableState.update { it.copy(diagnostics = event.value) }
            is RuntimeStoreEvent.Telemetry -> mutableState.update {
                it.copy(telemetry = event.value, connection = ConnectionState.Connected)
            }
            is RuntimeStoreEvent.Chronicle -> mutableState.update { it.copy(chronicle = event.entries) }
            is RuntimeStoreEvent.RuntimeStreaming -> mutableState.update {
                it.copy(telemetry = it.telemetry?.applying(event.value))
            }
            is RuntimeStoreEvent.Session -> {
                val client = api
                if (event.id != null && event.id != mutableState.value.conversation?.id && client != null) {
                    viewModelScope.launch {
                        runCatching { client.conversation(event.id) }
                            .onSuccess { conversation -> mutableState.update { it.copy(conversation = conversation) } }
                    }
                }
            }
            is RuntimeStoreEvent.Stream -> Unit
        }
    }
    private fun log(message: String) {
        mutableState.update {
            it.copy(logs = (listOf("${Instant.now()}  $message") + it.logs).take(100))
        }
    }

    private fun safeMessage(error: Exception): String = when (error) {
        is HttpException -> if (error.code() == 401) "Authentication failed." else "Core Runtime returned HTTP ${error.code()}."
        is IllegalArgumentException -> error.message ?: "Invalid connection settings."
        else -> "Core Runtime is unavailable."
    }
}

/** Epoch IX-B name for the single lifecycle-aware runtime-state authority. */
typealias RuntimeStore = OperatorViewModel
