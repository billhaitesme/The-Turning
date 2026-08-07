import Combine

enum RuntimeStoreEvent {
    case status(RuntimeStatus)
    case diagnostics(Diagnostics)
    case telemetry(RuntimeTelemetry)
    case session(String?)
    case chronicle([ChronicleEntry])
    case runtimeStreaming(RuntimeStreamingSignal)
    case stream(StreamEvent)
}

final class RuntimeEventBus {
    let events = PassthroughSubject<RuntimeStoreEvent, Never>()

    func publish(_ event: RuntimeStoreEvent) {
        events.send(event)
    }
}
