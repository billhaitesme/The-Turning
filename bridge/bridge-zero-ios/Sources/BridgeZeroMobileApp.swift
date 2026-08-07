import SwiftUI

@main
struct BridgeZeroMobileApp: App {
    @Environment(\.scenePhase) private var scenePhase
    @StateObject private var state = RuntimeStore()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(state)
                .preferredColorScheme(state.theme.colorScheme)
                .tint(BridgeTheme.signal)
                .task {
                    if ProcessInfo.processInfo.arguments.contains("-ui-testing") {
                        state.disconnect(clearCredentials: true)
                    } else {
                        await state.restoreConnectionIfPossible()
                    }
                }
                .onChange(of: scenePhase) { _, phase in
                    switch phase {
                    case .active:
                        state.resumeEvents()
                    case .inactive, .background:
                        state.suspendEvents()
                    @unknown default:
                        state.suspendEvents()
                    }
                }
        }
    }
}
