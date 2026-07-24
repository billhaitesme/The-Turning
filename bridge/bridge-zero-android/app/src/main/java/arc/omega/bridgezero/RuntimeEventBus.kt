package arc.omega.bridgezero

import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow

sealed interface RuntimeStoreEvent {
    data class Status(val value: RuntimeStatus) : RuntimeStoreEvent
    data class DiagnosticsChanged(val value: Diagnostics) : RuntimeStoreEvent
    data class Telemetry(val value: RuntimeTelemetry) : RuntimeStoreEvent
    data class Session(val id: String?) : RuntimeStoreEvent
    data class Chronicle(val entries: List<ChronicleEntry>) : RuntimeStoreEvent
    data class RuntimeStreaming(val value: RuntimeStreamingSignal) : RuntimeStoreEvent
    data class Stream(val value: StreamEvent) : RuntimeStoreEvent
}

class RuntimeEventBus {
    private val mutableEvents = MutableSharedFlow<RuntimeStoreEvent>(extraBufferCapacity = 64)
    val events: SharedFlow<RuntimeStoreEvent> = mutableEvents.asSharedFlow()

    fun publish(event: RuntimeStoreEvent) {
        mutableEvents.tryEmit(event)
    }
}
