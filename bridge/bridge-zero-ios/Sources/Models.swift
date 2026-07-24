import Foundation
import SwiftUI

struct Compatibility: Codable, Equatable {
    let runtimeVersion: String
    let requiredMobileVersion: String
    let apiVersion: String
}

struct RuntimeStatus: Codable, Equatable {
    let online: Bool
    let currentModel: String?
    let modelLock: Bool
    let uptimeSeconds: Int
    let latencyMs: Double
    let version: String
    let chronicleCount: Int
}

struct RuntimeTelemetry: Codable, Equatable {
    let observedAt: String
    let uptimeSeconds: Int
    let cpuPercent: Double?
    let ramUsedBytes: Int64?
    let ramTotalBytes: Int64?
    let latencyMs: Double?
    let toolQueue: Int
    let streamingState: String
    let activeStreams: Int
    let connectedClients: Int
    let currentSession: String?
    let chronicleEvents: Int
    func applying(_ signal: RuntimeStreamingSignal) -> RuntimeTelemetry {
        RuntimeTelemetry(
            observedAt: observedAt,
            uptimeSeconds: uptimeSeconds,
            cpuPercent: cpuPercent,
            ramUsedBytes: ramUsedBytes,
            ramTotalBytes: ramTotalBytes,
            latencyMs: signal.latencyMs ?? latencyMs,
            toolQueue: toolQueue,
            streamingState: signal.state,
            activeStreams: signal.activeStreams,
            connectedClients: connectedClients,
            currentSession: signal.sessionId ?? currentSession,
            chronicleEvents: chronicleEvents
        )
    }
}

struct RuntimeStreamingSignal: Codable, Equatable {
    let state: String
    let sessionId: String?
    let activeStreams: Int
    let latencyMs: Double?
}

struct RuntimeSessionSignal: Codable, Equatable {
    let currentSession: String?
}

struct RuntimeChronicleSignal: Codable, Equatable {
    let entries: [ChronicleEntry]
}

enum DiagnosticLevel: String, Codable {
    case healthy
    case degraded
    case unavailable
    case inactive

    var color: Color {
        switch self {
        case .healthy: BridgeTheme.nominal
        case .degraded: BridgeTheme.warning
        case .unavailable: BridgeTheme.failure
        case .inactive: BridgeTheme.muted
        }
    }
}

struct DiagnosticState: Codable, Equatable {
    let state: DiagnosticLevel
    let detail: String?
}

struct Diagnostics: Codable, Equatable {
    let identity: DiagnosticState
    let evidence: DiagnosticState
    let planning: DiagnosticState
    let deliberation: DiagnosticState
    let toolState: DiagnosticState
    let memory: DiagnosticState
    let chronicle: DiagnosticState
    let connectionHealth: DiagnosticState
    let counts: [String: Int]?

    var ordered: [(String, DiagnosticState)] {
        [
            ("Identity", identity), ("Evidence", evidence), ("Planning", planning),
            ("Deliberation", deliberation), ("Tool State", toolState),
            ("Memory", memory), ("Chronicle", chronicle),
            ("Connection Health", connectionHealth),
        ]
    }
}

struct Conversation: Codable, Equatable {
    let id: String
    let messages: [RuntimeMessage]
}

struct RuntimeMessage: Codable, Equatable, Identifiable {
    enum Role: String, Codable {
        case `operator`
        case runtime
        case system
    }

    let id: String
    let role: Role
    let content: String
    let createdAt: Date
}

struct ChronicleEntry: Codable, Equatable, Identifiable {
    let id: String
    let epoch: String
    let title: String
    let occurredAt: Date
    let items: [String]
}

struct StreamEvent: Equatable {
    enum Kind: Equatable {
        case phase(String)
        case delta(String)
        case end
        case error(String)
        case metadata
    }

    let kind: Kind
}

enum ConsoleConnection: Equatable {
    case disconnected
    case connecting
    case connected
    case offline(String)
    case updateRequired(Compatibility)
}

enum AppTheme: String, CaseIterable, Identifiable {
    case dark
    case system

    var id: String { rawValue }
    var title: String { rawValue.capitalized }
    var colorScheme: ColorScheme? { self == .dark ? .dark : nil }
}

enum MobileVersion {
    static let current = "0.2.0"
    static let apiMajor = "1"

    static func isCompatible(_ compatibility: Compatibility) -> Bool {
        compatibility.apiVersion.split(separator: ".").first.map(String.init) == apiMajor
            && compare(current, compatibility.requiredMobileVersion) != .orderedAscending
    }

    static func compare(_ lhs: String, _ rhs: String) -> ComparisonResult {
        let left = lhs.split(separator: ".").map { Int($0.prefix { $0.isNumber }) ?? 0 }
        let right = rhs.split(separator: ".").map { Int($0.prefix { $0.isNumber }) ?? 0 }
        for index in 0..<max(left.count, right.count) {
            let l = index < left.count ? left[index] : 0
            let r = index < right.count ? right[index] : 0
            if l < r { return .orderedAscending }
            if l > r { return .orderedDescending }
        }
        return .orderedSame
    }
}
