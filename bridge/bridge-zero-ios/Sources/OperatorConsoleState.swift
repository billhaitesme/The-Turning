import Combine
import Foundation

@MainActor
final class OperatorConsoleState: ObservableObject {
    let eventBus = RuntimeEventBus()
    @Published private(set) var connection: ConsoleConnection = .disconnected
    @Published private(set) var runtimeStatus: RuntimeStatus?
    @Published private(set) var telemetry: RuntimeTelemetry?
    @Published private(set) var diagnostics: Diagnostics?
    @Published private(set) var conversation: Conversation?
    @Published private(set) var chronicle: [ChronicleEntry] = []
    @Published private(set) var streamingText = ""
    @Published private(set) var runtimePhase: String?
    @Published private(set) var roundTripLatencyMs: Double?
    @Published private(set) var logs: [String] = []
    @Published var composerText = ""
    @Published var theme: AppTheme {
        didSet { defaults.set(theme.rawValue, forKey: Keys.theme) }
    }

    private let credentials: CredentialStoring
    private let defaults: UserDefaults
    private var api: RuntimeAPIClient?
    private var eventStreamTask: Task<Void, Never>?
    private var streamTask: Task<Void, Never>?
    private var eventSubscriptions = Set<AnyCancellable>()

    enum Keys {
        static let server = "bridgeZero.serverURL"
        static let theme = "bridgeZero.theme"
    }

    init(credentials: CredentialStoring = KeychainCredentialStore(), defaults: UserDefaults = .standard) {
        self.credentials = credentials
        self.defaults = defaults
        self.theme = AppTheme(rawValue: defaults.string(forKey: Keys.theme) ?? "dark") ?? .dark
        eventBus.events
            .sink { [weak self] event in
                Task { @MainActor in self?.apply(event) }
            }
            .store(in: &eventSubscriptions)
    }

    var savedServer: String { defaults.string(forKey: Keys.server) ?? "" }
    var hasSavedToken: Bool { credentials.readToken() != nil }
    var isStreaming: Bool { streamTask != nil }
    var isConnected: Bool { if case .connected = connection { true } else { false } }

    func restoreConnectionIfPossible() async {
        guard case .disconnected = connection,
              !savedServer.isEmpty,
              let token = credentials.readToken(), !token.isEmpty else { return }
        await connect(server: savedServer, token: token, persist: false)
    }

    func connect(server: String, token: String, persist: Bool = true) async {
        disconnect(clearCredentials: false)
        connection = .connecting
        appendLog("Connection attempt started")
        do {
            let configuration = try APIConfiguration(server: server, token: token)
            let client = RuntimeAPIClient(configuration: configuration)
            let compatibility = try await client.compatibility()
            guard MobileVersion.isCompatible(compatibility) else {
                api = client
                connection = .updateRequired(compatibility)
                appendLog("Compatibility gate blocked runtime access")
                return
            }
            let start = ContinuousClock.now
            async let status = client.status()
            async let telemetry = client.telemetry()
            async let diagnostics = client.diagnostics()
            async let chronicle = client.chronicle()
            let loadedStatus = try await status
            let loadedTelemetry = try await telemetry
            let loadedDiagnostics = try await diagnostics
            let loadedChronicle = try await chronicle
            let loadedConversation = try await loadActiveConversation(using: client)
            roundTripLatencyMs = milliseconds(since: start)
            eventBus.publish(.status(loadedStatus))
            eventBus.publish(.telemetry(loadedTelemetry))
            eventBus.publish(.diagnostics(loadedDiagnostics))
            eventBus.publish(.chronicle(loadedChronicle))
            conversation = loadedConversation
            api = client
            if persist {
                try credentials.saveToken(token)
                defaults.set(configuration.baseURL.absoluteString, forKey: Keys.server)
            }
            connection = .connected
            appendLog("Core Runtime connected")
            resumeEvents()
        } catch {
            api = nil
            connection = .offline(error.localizedDescription)
            appendLog("Connection failed: \(safeDescription(error))")
        }
    }

    func refresh() async {
        guard let api, isConnected else { return }
        let start = ContinuousClock.now
        do {
            async let status = api.status()
            async let telemetry = api.telemetry()
            async let diagnostics = api.diagnostics()
            let loadedStatus = try await status
            let loadedTelemetry = try await telemetry
            let loadedDiagnostics = try await diagnostics
            eventBus.publish(.status(loadedStatus))
            eventBus.publish(.telemetry(loadedTelemetry))
            eventBus.publish(.diagnostics(loadedDiagnostics))
            roundTripLatencyMs = milliseconds(since: start)
            if case .offline = connection { connection = .connected }
        } catch {
            connection = .offline(error.localizedDescription)
            appendLog("Manual runtime refresh unavailable: \(safeDescription(error))")
        }
    }

    func sendMessage() {
        let content = composerText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !content.isEmpty, let api, let conversation, streamTask == nil, isConnected else { return }
        composerText = ""
        streamingText = ""
        runtimePhase = nil
        let local = RuntimeMessage(
            id: UUID().uuidString,
            role: .operator,
            content: content,
            createdAt: Date()
        )
        self.conversation = Conversation(id: conversation.id, messages: conversation.messages + [local])
        streamTask = Task { [weak self] in
            guard let self else { return }
            defer {
                self.streamTask = nil
                self.runtimePhase = nil
            }
            do {
                for try await event in await api.streamMessage(conversationID: conversation.id, content: content) {
                    self.eventBus.publish(.stream(event))
                    switch event.kind {
                    case .phase(let phase): self.runtimePhase = phase
                    case .delta(let text): self.streamingText += text
                    case .end:
                        self.conversation = try await api.conversation(id: conversation.id)
                        self.streamingText = ""
                    case .error(let message): throw APIClientError.runtime(message)
                    case .metadata: break
                    }
                }
                if !self.streamingText.isEmpty {
                    self.conversation = try await api.conversation(id: conversation.id)
                    self.streamingText = ""
                }
            } catch is CancellationError {
                self.appendLog("Runtime stream cancelled")
            } catch {
                self.appendLog("Runtime stream failed: \(self.safeDescription(error))")
                self.connection = .offline(error.localizedDescription)
            }
        }
    }

    func disconnect(clearCredentials: Bool) {
        eventStreamTask?.cancel()
        streamTask?.cancel()
        eventStreamTask = nil
        streamTask = nil
        api = nil
        runtimePhase = nil
        streamingText = ""
        if clearCredentials {
            try? credentials.deleteToken()
            defaults.removeObject(forKey: Keys.server)
        }
        connection = .disconnected
    }

    func resumeEvents() {
        guard api != nil, eventStreamTask == nil else { return }
        eventStreamTask = Task { [weak self] in
            guard let self else { return }
            while !Task.isCancelled {
                guard let api = self.api else { return }
                do {
                    for try await event in await api.runtimeEvents() {
                        guard !Task.isCancelled else { return }
                        self.eventBus.publish(event)
                        if case .offline = self.connection { self.connection = .connected }
                    }
                } catch is CancellationError {
                    return
                } catch {
                    self.connection = .offline(error.localizedDescription)
                    self.appendLog("Runtime event stream unavailable: \(self.safeDescription(error)); retrying")
                    do {
                        try await Task.sleep(for: .seconds(3))
                    } catch {
                        return
                    }
                }
            }
        }
    }

    func suspendEvents() {
        eventStreamTask?.cancel()
        eventStreamTask = nil
    }

    private func apply(_ event: RuntimeStoreEvent) {
        switch event {
        case .status(let value):
            runtimeStatus = value
        case .telemetry(let value):
            telemetry = value
        case .diagnostics(let value):
            diagnostics = value
        case .chronicle(let entries):
            chronicle = entries
        case .session(let sessionID):
            guard let sessionID, sessionID != conversation?.id, let api else { return }
            Task { [weak self] in
                guard let self else { return }
                do {
                    self.conversation = try await api.conversation(id: sessionID)
                } catch {
                    self.appendLog("Session synchronization failed: \(self.safeDescription(error))")
                }
            }
        case .runtimeStreaming(let signal):
            if let current = telemetry {
                telemetry = current.applying(signal)
            }
        case .stream:
            break
        }
    }

    private func loadActiveConversation(using client: RuntimeAPIClient) async throws -> Conversation {
        do { return try await client.activeConversation() }
        catch APIClientError.http(404) { return try await client.createConversation() }
    }

    private func appendLog(_ message: String) {
        let formatter = ISO8601DateFormatter()
        logs.insert("\(formatter.string(from: Date()))  \(message)", at: 0)
        logs = Array(logs.prefix(100))
    }

    private func safeDescription(_ error: Error) -> String {
        // Error types never retain or print request headers or bearer credentials.
        (error as? LocalizedError)?.errorDescription ?? "Unknown runtime error"
    }

    private func milliseconds(since instant: ContinuousClock.Instant) -> Double {
        let duration = instant.duration(to: .now)
        return Double(duration.components.seconds) * 1_000
            + Double(duration.components.attoseconds) / 1_000_000_000_000_000
    }
}

/// Epoch IX-B name for the single observable runtime-state authority.
typealias RuntimeStore = OperatorConsoleState
