import SwiftUI

struct DiagnosticsView: View {
    @EnvironmentObject private var state: OperatorConsoleState

    var body: some View {
        ScrollView {
            VStack(spacing: 10) {
                if let diagnostics = state.diagnostics {
                    ForEach(Array(diagnostics.ordered.enumerated()), id: \.offset) { _, record in
                        let (name, diagnostic) = record
                        HStack(alignment: .top, spacing: 12) {
                            Circle().fill(diagnostic.state.color).frame(width: 9, height: 9).padding(.top, 5)
                            VStack(alignment: .leading, spacing: 3) {
                                Text(name).font(.body.weight(.semibold))
                                if let detail = diagnostic.detail {
                                    Text(detail).font(.footnote).foregroundStyle(.secondary)
                                }
                            }
                            Spacer()
                            Text(diagnostic.state.rawValue.uppercased())
                                .font(.caption2.monospaced().weight(.bold))
                                .foregroundStyle(diagnostic.state.color)
                        }
                        .padding(14)
                        .background(BridgeTheme.panel, in: RoundedRectangle(cornerRadius: 10))
                    }
                } else {
                    ContentUnavailableView("Diagnostics Unavailable", systemImage: "scope", description: Text("No runtime diagnostic response has been received."))
                }
            }.padding(16)
        }
        .background(BridgeTheme.void)
        .navigationTitle("Diagnostics")
        .navigationBarTitleDisplayMode(.inline)
        .refreshable { await state.refresh() }
    }
}
