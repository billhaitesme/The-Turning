import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var state: OperatorConsoleState

    var body: some View {
        List {
            Section("Connection") {
                LabeledContent("Server", value: state.savedServer)
                LabeledContent("Authentication", value: state.hasSavedToken ? "Keychain secured" : "Not stored")
            }
            Section("Appearance") {
                Picker("Theme", selection: $state.theme) {
                    ForEach(AppTheme.allCases) { Text($0.title).tag($0) }
                }
            }
            Section("Runtime") {
                LabeledContent("Model", value: state.runtimeStatus?.currentModel ?? "Unavailable")
                LabeledContent("Model Lock", value: state.runtimeStatus?.modelLock == true ? "Engaged" : "Unavailable")
                LabeledContent("Runtime Version", value: state.runtimeStatus?.version ?? "Unavailable")
                LabeledContent("Mobile Version", value: MobileVersion.current)
                NavigationLink("Chronicle") { ChronicleView() }
                NavigationLink("Logs") { LogsView() }
            }
            Section("Notifications") {
                Text("Runtime push notifications become available in Epoch IX-C.")
                    .font(.footnote).foregroundStyle(.secondary)
            }
            Section {
                Button("Disconnect", role: .destructive) { state.disconnect(clearCredentials: true) }
            }
        }
        .scrollContentBackground(.hidden)
        .background(BridgeTheme.void)
        .navigationTitle("Settings")
        .navigationBarTitleDisplayMode(.inline)
    }
}

struct ChronicleView: View {
    @EnvironmentObject private var state: OperatorConsoleState

    var body: some View {
        ScrollView {
            LazyVStack(spacing: 14) {
                ForEach(state.chronicle) { entry in
                    InstrumentPanel(title: "Chronicle") {
                        Text(entry.epoch).font(.title3.monospaced().weight(.bold))
                        Text(entry.title).foregroundStyle(BridgeTheme.signal)
                        Divider()
                        ForEach(entry.items, id: \.self) { Label($0, systemImage: "minus") }
                    }
                }
                if state.chronicle.isEmpty {
                    ContentUnavailableView("No Chronicle Entries", systemImage: "book.closed")
                }
            }.padding(16)
        }
        .background(BridgeTheme.void)
        .navigationTitle("Chronicle")
    }
}

struct LogsView: View {
    @EnvironmentObject private var state: OperatorConsoleState

    var body: some View {
        List(state.logs, id: \.self) { line in
            Text(line).font(.caption.monospaced()).textSelection(.enabled)
        }
        .overlay {
            if state.logs.isEmpty { ContentUnavailableView("No Connection Logs", systemImage: "doc.text") }
        }
        .navigationTitle("Logs")
    }
}
