import SwiftUI

struct RootView: View {
    @EnvironmentObject private var state: OperatorConsoleState

    var body: some View {
        Group {
            switch state.connection {
            case .connected, .offline:
                ConsoleTabView()
            case .updateRequired(let compatibility):
                UpdateRequiredView(compatibility: compatibility)
            case .disconnected, .connecting:
                LoginView()
            }
        }
        .background(BridgeTheme.void.ignoresSafeArea())
    }
}

struct LoginView: View {
    @EnvironmentObject private var state: OperatorConsoleState
    @State private var server = ""
    @State private var token = ""

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 28) {
                    VStack(alignment: .leading, spacing: 6) {
                        Text("BRIDGE ZERO")
                            .font(.system(size: 34, weight: .bold, design: .rounded))
                            .tracking(2)
                        Text("MOBILE OPERATOR CONSOLE")
                            .font(.caption.monospaced().weight(.semibold))
                            .foregroundStyle(BridgeTheme.signal)
                    }

                    InstrumentPanel(title: "Core Runtime Link") {
                        TextField("https://runtime.example", text: $server)
                            .textInputAutocapitalization(.never)
                            .keyboardType(.URL)
                            .textContentType(.URL)
                            .padding(BridgeSpacing.md).background(BridgeTheme.raised, in: RoundedRectangle(cornerRadius: BridgeRadius.control))
                            .accessibilityLabel("Server Address")
                        SecureField("Authentication Token", text: $token)
                            .textContentType(.password)
                            .padding(BridgeSpacing.md).background(BridgeTheme.raised, in: RoundedRectangle(cornerRadius: BridgeRadius.control))
                        Button {
                            Task { await state.connect(server: server, token: token) }
                        } label: {
                            HStack {
                                Spacer()
                                if case .connecting = state.connection { ProgressView().padding(.trailing, 4) }
                                Text("CONNECT").font(.body.monospaced().weight(.bold))
                                Spacer()
                            }.padding(.vertical, BridgeSpacing.md)
                        }
                        .buttonStyle(.borderedProminent)
                        .disabled(server.isEmpty || token.isEmpty || state.connection == .connecting)
                    }

                    if case .offline(let reason) = state.connection {
                        Label(reason, systemImage: "exclamationmark.triangle")
                            .font(.footnote).foregroundStyle(BridgeTheme.failure)
                    }
                    Text("Credentials remain on this device. TLS certificate validation is enforced by iOS.")
                        .font(.footnote).foregroundStyle(.secondary)
                }
                .padding(BridgeSpacing.xl)
            }
            .background(BridgeTheme.void)
            .onAppear {
                server = state.savedServer
                if state.hasSavedToken { token = "" }
            }
        }
    }
}

struct ConsoleTabView: View {
    var body: some View {
        TabView {
            NavigationStack { DashboardView() }
                .tabItem { Label("Runtime", systemImage: "waveform.path.ecg") }
            NavigationStack { ConversationView() }
                .tabItem { Label("Console", systemImage: "terminal") }
            NavigationStack { DiagnosticsView() }
                .tabItem { Label("Diagnostics", systemImage: "scope") }
            NavigationStack { SettingsView() }
                .tabItem { Label("Settings", systemImage: "slider.horizontal.3") }
        }
    }
}

struct UpdateRequiredView: View {
    @EnvironmentObject private var state: OperatorConsoleState
    let compatibility: Compatibility

    var body: some View {
        VStack(spacing: 18) {
            Image(systemName: "arrow.down.app.fill")
                .font(.system(size: 44)).foregroundStyle(BridgeTheme.warning)
            Text("UPDATE REQUIRED").font(.title2.monospaced().weight(.bold))
            Text("This operator console cannot safely use the connected Core Runtime.")
                .multilineTextAlignment(.center).foregroundStyle(.secondary)
            InstrumentPanel(title: "Compatibility") {
                MetricRow(label: "Installed Mobile", value: MobileVersion.current)
                MetricRow(label: "Required Mobile", value: compatibility.requiredMobileVersion)
                MetricRow(label: "Runtime", value: compatibility.runtimeVersion)
                MetricRow(label: "API", value: compatibility.apiVersion)
            }.frame(maxWidth: 420)
            Button("DISCONNECT") { state.disconnect(clearCredentials: false) }
                .buttonStyle(.bordered)
        }
        .padding(BridgeSpacing.xl)
    }
}
