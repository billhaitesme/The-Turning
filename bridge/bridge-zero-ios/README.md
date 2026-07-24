# Bridge Zero Mobile for iOS

Native SwiftUI operator console for the OMEGA-ARC Core Runtime.

**Release:** Epoch IX / Version 0.2.0 · **Milestone:** IX-B

## Build

1. Install Xcode 16 and XcodeGen.
2. Run `xcodegen generate` in this directory.
3. Open `BridgeZeroMobile.xcodeproj` and select a signing team.
4. Run on an iOS 17+ simulator or device.

The project has no third-party runtime dependencies. Credentials are stored in Keychain. URLSession performs normal platform certificate validation. Local-network access is enabled, but arbitrary cleartext HTTP is not globally allowed.

## Behavior

The application connects only after compatibility, status, diagnostics, and session checks succeed. It polls live status every 2.5 seconds and consumes the Core Runtime SSE stream without simulated typing. A completed stream triggers an authoritative history reload.

Run unit and UI tests with Xcode. Tests cover semantic version comparison, SSE parsing, compatibility gating, secure endpoint policy, offline state, and the login surface.
