import Foundation

enum APIClientError: LocalizedError {
    case invalidServer
    case insecureServer
    case unauthorized
    case http(Int)
    case invalidStream
    case runtime(String)

    var errorDescription: String? {
        switch self {
        case .invalidServer: "Enter a valid Core Runtime address."
        case .insecureServer: "HTTPS is required except for local-network development."
        case .unauthorized: "Authentication failed."
        case .http(let code): "Core Runtime returned HTTP \(code)."
        case .invalidStream: "The Core Runtime stream was invalid."
        case .runtime(let message): message
        }
    }
}

struct APIConfiguration: Equatable {
    let baseURL: URL
    let token: String

    init(server: String, token: String) throws {
        let normalized = server.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let url = URL(string: normalized), let scheme = url.scheme?.lowercased(), url.host != nil else {
            throw APIClientError.invalidServer
        }
        guard scheme == "https" || (scheme == "http" && Self.isLocal(url.host)) else {
            throw APIClientError.insecureServer
        }
        self.baseURL = url
        self.token = token
    }

    private static func isLocal(_ host: String?) -> Bool {
        guard let host = host?.lowercased() else { return false }
        return host == "localhost" || host == "127.0.0.1" || host == "::1"
            || host.hasSuffix(".local")
            || host.hasPrefix("10.")
            || host.hasPrefix("192.168.")
            || (host.split(separator: ".").count == 4 && host.hasPrefix("172."))
    }

    func endpoint(_ path: String) -> URL {
        let clean = path.hasPrefix("/") ? String(path.dropFirst()) : path
        return baseURL.appending(path: clean)
    }
}

actor RuntimeAPIClient {
    private let configuration: APIConfiguration
    private let session: URLSession
    private let decoder: JSONDecoder
    private let encoder = JSONEncoder()
    private let clientID = UUID().uuidString

    init(configuration: APIConfiguration, session: URLSession = .shared) {
        self.configuration = configuration
        self.session = session
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601
        self.decoder = decoder
    }

    func compatibility() async throws -> Compatibility {
        try await get("api/mobile/v1/compatibility")
    }

    func status() async throws -> RuntimeStatus {
        try await get("api/mobile/v1/status")
    }

    func telemetry() async throws -> RuntimeTelemetry {
        try await get("api/mobile/v1/telemetry")
    }

    func diagnostics() async throws -> Diagnostics {
        try await get("api/mobile/v1/diagnostics")
    }

    func activeConversation() async throws -> Conversation {
        try await get("api/mobile/v1/conversations/active")
    }

    func conversation(id: String) async throws -> Conversation {
        try await get("api/mobile/v1/conversations/\(id)")
    }

    func createConversation() async throws -> Conversation {
        try await send("api/mobile/v1/conversations", body: ["title": "Bridge Zero Mobile"])
    }

    func chronicle() async throws -> [ChronicleEntry] {
        try await get("api/mobile/v1/chronicle")
    }
    func runtimeEvents() -> AsyncThrowingStream<RuntimeStoreEvent, Error> {
        AsyncThrowingStream { continuation in
            let task = Task {
                do {
                    var eventRequest = self.request("api/mobile/v1/events")
                    eventRequest.timeoutInterval = 90
                    eventRequest.setValue("text/event-stream", forHTTPHeaderField: "Accept")
                    let (bytes, response) = try await self.session.bytes(for: eventRequest)
                    try Self.validate(response)
                    var parser = RuntimeOperationsSSEParser()
                    for try await line in bytes.lines {
                        if let event = try parser.consume(line: line) {
                            continuation.yield(event)
                        }
                    }
                    continuation.finish(throwing: APIClientError.invalidStream)
                } catch is CancellationError {
                    continuation.finish()
                } catch {
                    continuation.finish(throwing: error)
                }
            }
            continuation.onTermination = { _ in task.cancel() }
        }
    }


    func streamMessage(conversationID: String, content: String) -> AsyncThrowingStream<StreamEvent, Error> {
        AsyncThrowingStream { continuation in
            let task = Task {
                do {
                    var request = self.request(
                        "api/mobile/v1/conversations/\(conversationID)/messages",
                        method: "POST"
                    )
                    request.httpBody = try self.encoder.encode([
                        "content": content,
                        "client_message_id": UUID().uuidString,
                    ])
                    let (bytes, response) = try await self.session.bytes(for: request)
                    try Self.validate(response)
                    var parser = SSEParser()
                    for try await line in bytes.lines {
                        if let event = parser.consume(line: line) {
                            continuation.yield(event)
                            if event.kind == .end { break }
                        }
                    }
                    continuation.finish()
                } catch is CancellationError {
                    continuation.finish()
                } catch {
                    continuation.finish(throwing: error)
                }
            }
            continuation.onTermination = { _ in task.cancel() }
        }
    }

    private func get<T: Decodable>(_ path: String) async throws -> T {
        let (data, response) = try await session.data(for: request(path))
        try Self.validate(response)
        return try decoder.decode(T.self, from: data)
    }

    private func send<T: Decodable, Body: Encodable>(_ path: String, body: Body) async throws -> T {
        var request = request(path, method: "POST")
        request.httpBody = try encoder.encode(body)
        let (data, response) = try await session.data(for: request)
        try Self.validate(response)
        return try decoder.decode(T.self, from: data)
    }

    private func request(_ path: String, method: String = "GET") -> URLRequest {
        var request = URLRequest(url: configuration.endpoint(path))
        request.httpMethod = method
        request.timeoutInterval = 30
        request.setValue("Bearer \(configuration.token)", forHTTPHeaderField: "Authorization")
        request.setValue(clientID, forHTTPHeaderField: "X-Bridge-Client-ID")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if method != "GET" {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        return request
    }

    private static func validate(_ response: URLResponse) throws {
        guard let http = response as? HTTPURLResponse else { throw APIClientError.invalidStream }
        if http.statusCode == 401 { throw APIClientError.unauthorized }
        guard (200..<300).contains(http.statusCode) else { throw APIClientError.http(http.statusCode) }
    }
}

struct SSEParser {
    private var dataLines: [String] = []

    mutating func consume(line: String) -> StreamEvent? {
        if line.isEmpty {
            defer { dataLines.removeAll(keepingCapacity: true) }
            guard !dataLines.isEmpty,
                  let data = dataLines.joined(separator: "\n").data(using: .utf8),
                  let payload = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                  let type = payload["type"] as? String else { return nil }
            switch type {
            case "phase": return .init(kind: .phase(payload["name"] as? String ?? "runtime"))
            case "delta": return .init(kind: .delta(payload["text"] as? String ?? ""))
            case "end": return .init(kind: .end)
            case "error": return .init(kind: .error(payload["error"] as? String ?? "Runtime stream error"))
            default: return .init(kind: .metadata)
            }
        }
        if line.hasPrefix("data:") {
            dataLines.append(String(line.dropFirst(5)).trimmingCharacters(in: .whitespaces))
        }
        return nil
    }
}

struct RuntimeOperationsSSEParser {
    private var dataLines: [String] = []
    private let decoder: JSONDecoder

    init() {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601
        self.decoder = decoder
    }

    mutating func consume(line: String) throws -> RuntimeStoreEvent? {
        if line.isEmpty {
            defer { dataLines.removeAll(keepingCapacity: true) }
            guard !dataLines.isEmpty,
                  let data = dataLines.joined(separator: "\n").data(using: .utf8),
                  let envelope = try JSONSerialization.jsonObject(with: data) as? [String: Any],
                  let type = envelope["type"] as? String,
                  let payload = envelope["payload"],
                  JSONSerialization.isValidJSONObject(payload) else { return nil }
            let payloadData = try JSONSerialization.data(withJSONObject: payload)
            switch type {
            case "status":
                return .status(try decoder.decode(RuntimeStatus.self, from: payloadData))
            case "diagnostics":
                return .diagnostics(try decoder.decode(Diagnostics.self, from: payloadData))
            case "telemetry":
                return .telemetry(try decoder.decode(RuntimeTelemetry.self, from: payloadData))
            case "session":
                return .session(try decoder.decode(RuntimeSessionSignal.self, from: payloadData).currentSession)
            case "chronicle":
                return .chronicle(try decoder.decode(RuntimeChronicleSignal.self, from: payloadData).entries)
            case "streaming":
                return .runtimeStreaming(try decoder.decode(RuntimeStreamingSignal.self, from: payloadData))
            default:
                return nil
            }
        }
        if line.hasPrefix("data:") {
            dataLines.append(String(line.dropFirst(5)).trimmingCharacters(in: .whitespaces))
        }
        return nil
    }
}
