import SwiftUI

/// IX-D (ADR 0015): the operator INITIATES bounded runtime commands. The list is the runtime's
/// command registry, rendered as-is. Approval-gated commands complete in the Approvals tab behind
/// the biometric; forbidden commands are shown so the boundary is visible, never runnable.
struct CommandsView: View {
    @EnvironmentObject private var state: OperatorConsoleState

    var body: some View {
        List {
            if let notice = state.commandNotice {
                Section {
                    HStack(alignment: .top, spacing: BridgeSpacing.sm) {
                        Image(systemName: "bolt.horizontal.circle")
                        Text(notice).font(.footnote.monospaced())
                        Spacer(minLength: 0)
                        Button { state.clearCommandNotice() } label: {
                            Image(systemName: "xmark.circle.fill")
                        }
                        .buttonStyle(.plain)
                        .accessibilityLabel("Dismiss notice")
                    }
                    .foregroundStyle(BridgeTheme.warning)
                    .listRowBackground(BridgeTheme.panel)
                }
            }

            Section {
                ForEach(state.commands) { command in
                    CommandCard(command: command) { state.initiateCommand(command) }
                        .listRowBackground(BridgeTheme.panel)
                }
                if state.commands.isEmpty {
                    Text("No commands available.").foregroundStyle(.secondary)
                        .listRowBackground(BridgeTheme.panel)
                }
            } header: {
                Text("COMMANDS")
                    .font(.caption.monospaced().weight(.semibold))
                    .foregroundStyle(.secondary)
            } footer: {
                if !state.commandExecutionEnabled {
                    Text("Command execution is disabled by runtime policy — requests are recorded but will not run.")
                        .foregroundStyle(BridgeTheme.warning)
                }
            }

            Section {
                ForEach(state.commandHistory.prefix(20)) { entry in
                    CommandHistoryRow(entry: entry)
                        .listRowBackground(BridgeTheme.panel)
                }
                if state.commandHistory.isEmpty {
                    Text("Nothing commanded yet.").foregroundStyle(.secondary)
                        .listRowBackground(BridgeTheme.panel)
                }
            } header: {
                Text("HISTORY")
                    .font(.caption.monospaced().weight(.semibold))
                    .foregroundStyle(.secondary)
            }
        }
        .scrollContentBackground(.hidden)
        .background(BridgeTheme.void)
        .navigationTitle("Commands")
        .navigationBarTitleDisplayMode(.inline)
        .refreshable { await state.loadCommands() }
        .task { await state.loadCommands() }
    }
}

private struct CommandCard: View {
    let command: RuntimeCommand
    let onInitiate: () -> Void

    private var gateColor: Color {
        switch command.gate {
        case "direct": BridgeTheme.nominal
        case "approval": BridgeTheme.warning
        default: BridgeTheme.failure
        }
    }

    private var gateText: String {
        switch command.gate {
        case "direct": "DIRECT — executes now"
        case "approval": "APPROVAL — biometric on this device"
        default: "FORBIDDEN"
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: BridgeSpacing.sm) {
            Text(command.title.uppercased())
                .font(.headline.monospaced())
                .foregroundStyle(BridgeTheme.signal)
            if let description = command.description, !description.isEmpty {
                Text(description).font(.footnote).foregroundStyle(.secondary)
            }
            MetricRow(label: "Risk", value: command.risk.uppercased(), accent: gateColor)
            MetricRow(label: "Gate", value: gateText, accent: gateColor)
            if command.gate == "forbidden" {
                Button {} label: {
                    Text("FORBIDDEN").font(.body.monospaced().weight(.bold)).frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered).disabled(true)
            } else {
                Button(action: onInitiate) {
                    Text(command.gate == "approval" ? "REQUEST" : "RUN")
                        .font(.body.monospaced().weight(.bold)).frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .tint(gateColor)
            }
        }
        .padding(.vertical, 6)
    }
}

private struct CommandHistoryRow: View {
    let entry: CommandEntry

    private var statusColor: Color {
        switch entry.status {
        case "executed": BridgeTheme.nominal
        case "awaiting_approval", "executing": BridgeTheme.warning
        default: BridgeTheme.failure
        }
    }

    private var subtitle: String {
        var parts: [String] = []
        if let channel = entry.channel { parts.append(channel) }
        if let at = entry.requestedAt { parts.append(String(at.prefix(16)).replacingOccurrences(of: "T", with: " ")) }
        return parts.joined(separator: "  ")
    }

    var body: some View {
        HStack(alignment: .center, spacing: BridgeSpacing.md) {
            VStack(alignment: .leading, spacing: 2) {
                Text(entry.name).font(.subheadline.weight(.semibold))
                Text(subtitle).font(.caption2.monospaced()).foregroundStyle(.secondary)
            }
            Spacer(minLength: BridgeSpacing.md)
            Text((entry.status ?? "?").uppercased())
                .font(.caption.monospaced().weight(.bold))
                .foregroundStyle(statusColor)
                .lineLimit(1)
                .fixedSize(horizontal: true, vertical: false)
        }
        .padding(.vertical, 4)
    }
}
