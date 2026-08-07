import SwiftUI

struct ApprovalsView: View {
    @EnvironmentObject private var state: OperatorConsoleState

    var body: some View {
        List {
            ForEach(state.approvals) { approval in
                VStack(alignment: .leading, spacing: 8) {
                    Text(approval.toolName ?? "Runtime action")
                        .font(.headline.monospaced())
                        .foregroundStyle(BridgeTheme.signal)
                    Text("Requested by \(approval.requestedBy ?? "runtime")")
                        .font(.caption).foregroundStyle(.secondary)
                    if let expires = approval.expiresAt {
                        Label("Expires \(expires)", systemImage: "clock")
                            .font(.caption2.monospaced()).foregroundStyle(BridgeTheme.warning)
                    }
                    HStack(spacing: 12) {
                        Button {
                            state.approve(approval)
                        } label: {
                            Label("Approve", systemImage: "faceid").frame(maxWidth: .infinity)
                        }
                        .buttonStyle(.borderedProminent).tint(BridgeTheme.nominal)

                        Button(role: .destructive) {
                            state.deny(approval)
                        } label: {
                            Label("Deny", systemImage: "xmark").frame(maxWidth: .infinity)
                        }
                        .buttonStyle(.bordered)
                    }
                    .padding(.top, 4)
                }
                .padding(.vertical, 6)
                .listRowBackground(BridgeTheme.panel)
            }
        }
        .scrollContentBackground(.hidden)
        .background(BridgeTheme.void)
        .overlay {
            if state.approvals.isEmpty {
                ContentUnavailableView("No Pending Approvals", systemImage: "checkmark.shield")
            }
        }
        .navigationTitle("Approvals")
        .navigationBarTitleDisplayMode(.inline)
        .refreshable { await state.loadApprovals() }
        .task { await state.loadApprovals() }
    }
}
