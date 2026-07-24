import SwiftUI

struct DashboardView: View {
    @EnvironmentObject private var state: OperatorConsoleState

    var body: some View {
        ScrollView {
            VStack(spacing: 14) {
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("OMEGA-ARC").font(.title.bold()).tracking(1.5)
                        Text("CORE RUNTIME").font(.caption.monospaced()).foregroundStyle(BridgeTheme.signal)
                    }
                    Spacer()
                    connectionLamp
                }

                if let telemetry = state.telemetry {
                    InstrumentPanel(title: "Operations Dashboard") {
                        HStack {
                            StatusBadge(
                                label: telemetry.streamingState,
                                color: telemetry.streamingState == "streaming" ? BridgeTheme.signal : BridgeTheme.muted
                            )
                            Spacer()
                            Text("IX-B").font(.caption.monospaced()).foregroundStyle(BridgeTheme.signal)
                        }
                        MetricRow(label: "CPU", value: percent(telemetry.cpuPercent))
                        MetricRow(label: "RAM", value: memory(telemetry.ramUsedBytes, telemetry.ramTotalBytes))
                        MetricRow(label: "Tool Queue", value: String(telemetry.toolQueue))
                        MetricRow(label: "Connected Clients", value: String(telemetry.connectedClients))
                        MetricRow(label: "Active Streams", value: String(telemetry.activeStreams))
                        MetricRow(label: "Current Session", value: telemetry.currentSession ?? "UNAVAILABLE")
                        MetricRow(label: "Chronicle Events", value: String(telemetry.chronicleEvents))
                    }
                } else {
                    InstrumentPanel(title: "Operations Dashboard") {
                        Text("Measured telemetry unavailable.").foregroundStyle(.secondary)
                    }
                }

                if let status = state.runtimeStatus {
                    InstrumentPanel(title: "Runtime Status") {
                        MetricRow(label: "Status", value: status.online ? "ONLINE" : "OFFLINE", accent: status.online ? BridgeTheme.nominal : BridgeTheme.failure)
                        Divider()
                        MetricRow(label: "Current Model", value: status.currentModel ?? "UNAVAILABLE")
                        MetricRow(label: "Model Lock", value: status.modelLock ? "ENGAGED" : "DISENGAGED", accent: status.modelLock ? BridgeTheme.warning : BridgeTheme.muted)
                        MetricRow(label: "Uptime", value: formatUptime(status.uptimeSeconds))
                        MetricRow(label: "Latency", value: latency)
                        MetricRow(label: "Runtime Version", value: status.version)
                        MetricRow(label: "Chronicle Count", value: String(status.chronicleCount))
                    }
                } else {
                    InstrumentPanel(title: "Runtime Status") { ProgressView("Awaiting runtime state") }
                }

                InstrumentPanel(title: "Continuity") {
                    MetricRow(label: "Active Session", value: state.conversation?.id ?? "UNAVAILABLE")
                    MetricRow(label: "Messages", value: String(state.conversation?.messages.count ?? 0))
                    MetricRow(label: "Mobile Version", value: MobileVersion.current)
                }
            }
            .padding(16)
        }
        .background(BridgeTheme.void)
        .navigationTitle("Operator Console")
        .navigationBarTitleDisplayMode(.inline)
        .refreshable { await state.refresh() }
    }

    @ViewBuilder private var connectionLamp: some View {
        switch state.connection {
        case .connected: StatusLamp(color: BridgeTheme.nominal, label: "Linked")
        case .offline: StatusLamp(color: BridgeTheme.failure, label: "Offline")
        default: StatusLamp(color: BridgeTheme.warning, label: "Standby")
        }
    }

    private var latency: String {
        guard let value = state.roundTripLatencyMs else { return "UNAVAILABLE" }
        return String(format: "%.0f ms", value)
    }

    private func percent(_ value: Double?) -> String {
        value.map { String(format: "%.1f%%", $0) } ?? "UNAVAILABLE"
    }

    private func memory(_ used: Int64?, _ total: Int64?) -> String {
        guard let used, let total, total > 0 else { return "UNAVAILABLE" }
        let formatter = ByteCountFormatter()
        formatter.countStyle = .memory
        return "\(formatter.string(fromByteCount: used)) / \(formatter.string(fromByteCount: total))"
    }

    private func formatUptime(_ seconds: Int) -> String {
        let days = seconds / 86_400
        let hours = (seconds % 86_400) / 3_600
        let minutes = (seconds % 3_600) / 60
        if days > 0 { return "\(days)d \(hours)h" }
        if hours > 0 { return "\(hours)h \(minutes)m" }
        return "\(minutes)m"
    }
}
